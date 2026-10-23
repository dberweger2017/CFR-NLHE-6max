//! Prepared two-player river games. No blueprint, hidden deal or live adapter.
//!
//! The chance law is w0(h0) w1(h1) / Z on disjoint holdings. Sorted rank
//! prefixes and per-card sums replace dense holding-by-holding leaf products.
use hu20_buckets::evaluate;
use rayon::prelude::*;
use serde_json::{json, Value};
use std::{collections::HashSet, time::Instant};

#[derive(Clone, Debug)]
pub struct Holding {
    pub cards: [u8; 2],
    pub weight: f64,
}
#[derive(Clone, Copy, Debug)]
pub struct Terminal {
    pub base: f64,
    pub win0: f64,
    pub tie0: f64,
}
#[derive(Clone, Debug)]
pub enum Node {
    Decision { actor: usize, children: Vec<usize> },
    Leaf(Terminal),
}
#[derive(Clone)]
struct Hand {
    cards: [u8; 2],
    mask: u64,
    weight: f64,
    rank: u32,
}

mod correlated;

pub struct Game {
    board_mask: u64,
    folded: Option<correlated::FoldedLaw>,
    hands: [Vec<Hand>; 2],
    sorted: [Vec<usize>; 2],
    same: [Vec<Option<usize>>; 2],
    z: f64,
    // Optional exact pairwise chance law (seat 0 row-major, and its transpose),
    // replacing the product of range weights. Used for belief controls only.
    joint: Option<(Vec<f64>, Vec<f64>)>,
    nodes: Vec<Node>,
    root_pot_bb: f64,
    scalar_control: bool,
}

fn finite(x: f64) -> Result<f64, String> {
    if x.is_finite() {
        Ok(x)
    } else {
        Err("nonfinite numeric value".into())
    }
}

pub const MAX_NODES: usize = 4096;
pub const MAX_STRATEGY_CELLS: usize = 2_000_000;

impl Game {
    pub fn new(
        board: [u8; 5],
        ranges: [Vec<Holding>; 2],
        nodes: Vec<Node>,
        root_pot_bb: f64,
    ) -> Result<Self, String> {
        Self::with_limits(
            board,
            ranges,
            nodes,
            root_pot_bb,
            MAX_NODES,
            MAX_STRATEGY_CELLS,
        )
    }

    /// Larger limits are for offline evaluation games, not live decisions.
    pub fn with_limits(
        board: [u8; 5],
        ranges: [Vec<Holding>; 2],
        nodes: Vec<Node>,
        root_pot_bb: f64,
        max_nodes: usize,
        max_cells: usize,
    ) -> Result<Self, String> {
        let board_set: HashSet<_> = board.iter().copied().collect();
        if board_set.len() != 5 || board.iter().any(|&c| c >= 52) {
            return Err("five distinct board cards required".into());
        }
        if !root_pot_bb.is_finite() || root_pot_bb <= 0. {
            return Err("positive finite root pot required".into());
        }
        if nodes.is_empty() || nodes.len() > max_nodes {
            return Err("public tree size outside prototype bounds".into());
        }
        let mut parents = vec![0; nodes.len()];
        let mut depth = vec![0; nodes.len()];
        let mut cells = 0usize;
        for (id, node) in nodes.iter().enumerate() {
            match node {
                Node::Leaf(t) => {
                    finite(t.base)?;
                    finite(t.win0)?;
                    finite(t.tie0)?;
                }
                Node::Decision { actor, children } => {
                    if *actor > 1 || children.is_empty() || children.len() > 8 {
                        return Err("invalid actor/action count".into());
                    }
                    cells = cells
                        .checked_add(ranges[*actor].len() * children.len())
                        .ok_or("tree allocation overflow")?;
                    for &child in children {
                        if child <= id || child >= nodes.len() {
                            return Err("children must follow parents in a finite tree".into());
                        }
                        parents[child] += 1;
                        depth[child] = depth[id] + 1;
                        if parents[child] != 1 || depth[child] > 256 {
                            return Err("shared child or excessive tree depth".into());
                        }
                    }
                }
            }
        }
        if parents.iter().skip(1).any(|&p| p != 1) || cells > max_cells {
            return Err("unreachable node or excessive strategy cells".into());
        }
        let mut hands: [Vec<Hand>; 2] = [Vec::new(), Vec::new()];
        for seat in 0..2 {
            if ranges[seat].is_empty() || ranges[seat].len() > 1081 {
                return Err("range size outside board-complete holding bounds".into());
            }
            let mut seen = HashSet::new();
            let mut largest = 0f64;
            for h in &ranges[seat] {
                if h.cards[0] == h.cards[1]
                    || h.cards.iter().any(|c| *c >= 52 || board_set.contains(c))
                    || !h.weight.is_finite()
                    || h.weight < 0.
                {
                    return Err("invalid cards or range weight".into());
                }
                let mut pair = h.cards;
                pair.sort_unstable();
                if !seen.insert(pair) {
                    return Err("duplicate holding".into());
                }
                largest = largest.max(h.weight);
            }
            if largest == 0. {
                return Err("range has no positive weight".into());
            }
            let total: f64 = ranges[seat].iter().map(|h| h.weight / largest).sum();
            for h in &ranges[seat] {
                let mut cards = h.cards;
                cards.sort_unstable();
                hands[seat].push(Hand {
                    cards,
                    mask: (1u64 << cards[0]) | (1u64 << cards[1]),
                    weight: (h.weight / largest) / total,
                    rank: evaluate(&[
                        cards[0], cards[1], board[0], board[1], board[2], board[3], board[4],
                    ]),
                });
            }
        }
        let sorted = std::array::from_fn(|seat| {
            let mut order: Vec<_> = (0..hands[seat].len()).collect();
            order.sort_by_key(|&i| (hands[seat][i].rank, hands[seat][i].cards));
            order
        });
        let same = std::array::from_fn(|seat| {
            hands[seat]
                .iter()
                .map(|h| hands[1 - seat].iter().position(|o| o.mask == h.mask))
                .collect()
        });
        // Scalar, allocation-free normalization is done once at preparation.
        // In particular, an entirely blocked law must not acquire rounding mass.
        let mut z = 0.;
        for a in &hands[0] {
            for b in &hands[1] {
                if a.mask & b.mask == 0 {
                    z += a.weight * b.weight;
                }
            }
        }
        if !z.is_finite() || z <= 0. {
            return Err("ranges have no representable compatible joint mass".into());
        }
        Ok(Self {
            board_mask: board.iter().fold(0, |m, c| m | (1u64 << c)),
            folded: None,
            hands,
            sorted,
            same,
            z,
            nodes,
            root_pot_bb,
            scalar_control: false,
            joint: None,
        })
    }

    /// Replaces the product law w0(h0) w1(h1) / Z with an explicit joint law
    /// over (seat 0, seat 1) holdings. Blocked pairs must have zero mass.
    pub fn with_joint(mut self, mut joint: Vec<f64>) -> Result<Self, String> {
        if self.folded.is_some() {
            return Err("chance law already replaced".into());
        }
        let (n0, n1) = (self.hands[0].len(), self.hands[1].len());
        if joint.len() != n0 * n1 || joint.iter().any(|x| !x.is_finite() || *x < 0.) {
            return Err("joint law shape or values invalid".into());
        }
        for (i, a) in self.hands[0].iter().enumerate() {
            for (j, b) in self.hands[1].iter().enumerate() {
                if a.mask & b.mask != 0 && joint[i * n1 + j] != 0. {
                    return Err("joint law puts mass on blocked holdings".into());
                }
            }
        }
        let total: f64 = joint.iter().sum();
        if total <= 0. {
            return Err("joint law has no mass".into());
        }
        joint.iter_mut().for_each(|x| *x /= total);
        let mut transposed = vec![0.; n0 * n1];
        for i in 0..n0 {
            for j in 0..n1 {
                transposed[j * n0 + i] = joint[i * n1 + j];
            }
        }
        self.joint = Some((joint, transposed));
        Ok(self)
    }

    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }
    pub fn holdings(&self, seat: usize) -> usize {
        self.hands[seat].len()
    }
    pub fn ranks(&self) -> [Vec<u32>; 2] {
        std::array::from_fn(|s| self.hands[s].iter().map(|h| h.rank).collect())
    }

    fn leaf_into(&self, t: Terminal, seat: usize, reach: &[f64], out: &mut [f64]) {
        if let Some(law) = &self.folded {
            law.leaf_into(self, t, seat, reach, out);
            return;
        }
        let other = 1 - seat;
        if let Some((joint, transposed)) = &self.joint {
            // Exact joint law: dense pairwise sums, parallel over own holdings.
            let law = if seat == 0 { joint } else { transposed };
            let n = self.hands[other].len();
            out.par_iter_mut().enumerate().for_each(|(i, value)| {
                let h = &self.hands[seat][i];
                let row = &law[i * n..(i + 1) * n];
                let mut sum = 0.;
                for (j, o) in self.hands[other].iter().enumerate() {
                    if row[j] == 0. {
                        continue;
                    }
                    let (a, b) = if seat == 0 { (h, o) } else { (o, h) };
                    let u = t.base
                        + t.win0 * (if a.rank > b.rank { 1. } else { 0. })
                        + t.tie0 * (if a.rank == b.rank { 1. } else { 0. });
                    sum += row[j] * reach[j] * u;
                }
                *value = if seat == 0 { sum } else { -sum };
            });
            return;
        }
        // Inclusion-exclusion loses relative accuracy when almost all chance
        // mass is blocked. Preserve values with an explicit allocation-free
        // scalar fallback; report this mode rather than claim linear cost.
        if self.z < 1e-4 || self.scalar_control {
            for (i, h) in self.hands[seat].iter().enumerate() {
                let mut value = 0.;
                for (j, o) in self.hands[other].iter().enumerate() {
                    if h.mask & o.mask != 0 {
                        continue;
                    }
                    let (a, b) = if seat == 0 { (h, o) } else { (o, h) };
                    let u = t.base
                        + t.win0 * (if a.rank > b.rank { 1. } else { 0. })
                        + t.tie0 * (if a.rank == b.rank { 1. } else { 0. });
                    value += (h.weight * o.weight / self.z) * reach[j] * u;
                }
                out[i] = if seat == 0 { value } else { -value };
            }
            return;
        }
        let mut total = 0.;
        let mut cards = [0.; 52];
        for (h, &r) in self.hands[other].iter().zip(reach) {
            let v = h.weight * r;
            total += v;
            cards[h.cards[0] as usize] += v;
            cards[h.cards[1] as usize] += v;
        }
        if t.win0 == 0. && t.tie0 == 0. {
            // A fold terminal depends only on blocker-adjusted mass, so the
            // showdown rank pass is skipped. The arithmetic is the same as below.
            for (i, h) in self.hands[seat].iter().enumerate() {
                let identical =
                    self.same[seat][i].map_or(0., |j| self.hands[other][j].weight * reach[j]);
                let mass = (total - cards[h.cards[0] as usize] - cards[h.cards[1] as usize]
                    + identical)
                    .max(0.);
                let value = (t.base * mass) * (h.weight / self.z);
                out[i] = if seat == 0 { value } else { -value };
            }
            return;
        }
        let (mut low, mut high) = (0, 0);
        let (mut below, mut through) = (0., 0.);
        let (mut low_cards, mut high_cards) = ([0.; 52], [0.; 52]);
        for &i in &self.sorted[seat] {
            let h = &self.hands[seat][i];
            while low < self.sorted[other].len()
                && self.hands[other][self.sorted[other][low]].rank < h.rank
            {
                let j = self.sorted[other][low];
                let o = &self.hands[other][j];
                let v = o.weight * reach[j];
                below += v;
                low_cards[o.cards[0] as usize] += v;
                low_cards[o.cards[1] as usize] += v;
                low += 1;
            }
            while high < self.sorted[other].len()
                && self.hands[other][self.sorted[other][high]].rank <= h.rank
            {
                let j = self.sorted[other][high];
                let o = &self.hands[other][j];
                let v = o.weight * reach[j];
                through += v;
                high_cards[o.cards[0] as usize] += v;
                high_cards[o.cards[1] as usize] += v;
                high += 1;
            }
            let a = h.cards[0] as usize;
            let b = h.cards[1] as usize;
            let identical =
                self.same[seat][i].map_or(0., |j| self.hands[other][j].weight * reach[j]);
            // Inclusion-exclusion removes the identical pair twice; add it back.
            let mass = (total - cards[a] - cards[b] + identical).max(0.);
            let weaker = (below - low_cards[a] - low_cards[b]).max(0.).min(mass);
            let equal =
                (through - below - (high_cards[a] - low_cards[a]) - (high_cards[b] - low_cards[b])
                    + identical)
                    .max(0.)
                    .min((mass - weaker).max(0.));
            let first_wins = if seat == 0 {
                weaker
            } else {
                (mass - weaker - equal).max(0.)
            };
            let value =
                (t.base * mass + t.win0 * first_wins + t.tie0 * equal) * (h.weight / self.z);
            out[i] = if seat == 0 { value } else { -value };
        }
    }

    pub fn leaf(&self, t: Terminal, seat: usize, reach: &[f64]) -> Result<Vec<f64>, String> {
        if seat > 1
            || reach.len() != self.holdings(1 - seat)
            || reach.iter().any(|x| !x.is_finite() || *x < 0. || *x > 1.)
        {
            return Err("invalid opponent reach".into());
        }
        finite(t.base)?;
        finite(t.win0)?;
        finite(t.tie0)?;
        let mut result = vec![0.; self.holdings(seat)];
        self.leaf_into(t, seat, reach, &mut result);
        for &x in &result {
            finite(x)?;
        }
        Ok(result)
    }

    fn strategy_shape(&self) -> Vec<Vec<f64>> {
        self.nodes
            .iter()
            .map(|n| match n {
                Node::Leaf(_) => Vec::new(),
                Node::Decision { actor, children } => {
                    vec![0.; self.holdings(*actor) * children.len()]
                }
            })
            .collect()
    }
}

/// Opt-in leaf timing; per-leaf clocks are off in ordinary solves.
#[derive(Clone, Copy, Default)]
struct LeafTiming {
    fold_seconds: f64,
    showdown_seconds: f64,
    folds: u64,
    showdowns: u64,
}

struct Workspace {
    value: Vec<Vec<f64>>,
    reach: Vec<Vec<f64>>,
    timing: Option<LeafTiming>,
    // Best responses only: per node, the actions the responder may use (empty = all).
    mask: Option<Vec<Vec<bool>>>,
    // Best responses only: nodes whose profile is fixed (already taken) are not deviated from.
    fixed: Option<Vec<bool>>,
}
impl Workspace {
    fn new(game: &Game, seat: usize) -> Self {
        Self {
            value: vec![vec![0.; game.holdings(seat)]; game.nodes.len()],
            reach: vec![vec![0.; game.holdings(1 - seat)]; game.nodes.len()],
            timing: None,
            mask: None,
            fixed: None,
        }
    }
    fn start(&mut self) {
        self.reach[0].fill(1.);
    }
}

fn visit(
    game: &Game,
    id: usize,
    seat: usize,
    profile: &[Vec<f64>],
    deltas: &mut [Vec<f64>],
    weight: f64,
    best: bool,
    update: bool,
    work: &mut Workspace,
) {
    match &game.nodes[id] {
        Node::Leaf(t) => match work.timing {
            None => game.leaf_into(*t, seat, &work.reach[id], &mut work.value[id]),
            Some(mut timing) => {
                let tick = Instant::now();
                game.leaf_into(*t, seat, &work.reach[id], &mut work.value[id]);
                let elapsed = tick.elapsed().as_secs_f64();
                if t.win0 == 0. && t.tie0 == 0. {
                    timing.fold_seconds += elapsed;
                    timing.folds += 1;
                } else {
                    timing.showdown_seconds += elapsed;
                    timing.showdowns += 1;
                }
                work.timing = Some(timing);
            }
        },
        Node::Decision { actor, children } => {
            let k = children.len();
            for (action, &child) in children.iter().enumerate() {
                for h in 0..game.holdings(1 - seat) {
                    work.reach[child][h] = work.reach[id][h]
                        * if *actor == seat {
                            1.
                        } else {
                            profile[id][h * k + action]
                        };
                }
                visit(
                    game, child, seat, profile, deltas, weight, best, update, work,
                );
            }
            for h in 0..game.holdings(seat) {
                let value = if *actor != seat {
                    children.iter().map(|&c| work.value[c][h]).sum()
                } else if best && !work.fixed.as_ref().is_some_and(|f| f[id]) {
                    let allowed = work.mask.as_ref().map(|m| &m[id]).filter(|m| !m.is_empty());
                    children
                        .iter()
                        .enumerate()
                        .filter(|(a, _)| allowed.is_none_or(|m| m[*a]))
                        .map(|(_, &c)| work.value[c][h])
                        .fold(f64::NEG_INFINITY, f64::max)
                } else {
                    children
                        .iter()
                        .enumerate()
                        .map(|(a, &c)| profile[id][h * k + a] * work.value[c][h])
                        .sum()
                };
                work.value[id][h] = value;
                if update && *actor == seat {
                    for (a, &child) in children.iter().enumerate() {
                        deltas[id][h * k + a] += weight * (work.value[child][h] - value);
                    }
                }
            }
        }
    }
}

/// Regret and averaging rule. `Linear` weights iteration t by t; `Discounted`
/// is DCFR: after iteration t, accumulated positive regrets are multiplied by
/// t^alpha/(t^alpha+1), negative ones by t^beta/(t^beta+1), and the average
/// strategy's accumulated contributions by (t/(t+1))^gamma.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Algorithm {
    Linear,
    Discounted { alpha: f64, beta: f64, gamma: f64 },
}
pub const DCFR: Algorithm = Algorithm::Discounted {
    alpha: 1.5,
    beta: 0.,
    gamma: 2.,
};
impl Algorithm {
    pub fn name(self) -> &'static str {
        match self {
            Self::Linear => "linear-cfr",
            Self::Discounted { .. } if self == DCFR => "dcfr-1.5-0-2",
            Self::Discounted { .. } => "dcfr-custom",
        }
    }
}

#[derive(Default)]
struct SolverTiming {
    traversal_seconds: f64,
    update_seconds: f64,
}

pub struct Solver {
    algorithm: Algorithm,
    timing: SolverTiming,
    game: Game,
    regrets: Vec<Vec<f64>>,
    numer: Vec<Vec<f64>>,
    denom: Vec<Vec<f64>>,
    profile: Vec<Vec<f64>>,
    deltas: Vec<Vec<f64>>,
    fixed: Vec<Option<Vec<f64>>>,
    work: [Workspace; 2],
    own_reach: [Vec<Vec<f64>>; 2],
    sweeps: u64,
}

impl Solver {
    pub fn new(game: Game, fixed: Vec<Option<Vec<f64>>>) -> Result<Self, String> {
        if fixed.len() != game.nodes.len() {
            return Err("fixed profile node count differs".into());
        }
        let shape = game.strategy_shape();
        for (id, row) in fixed.iter().enumerate() {
            if let Some(p) = row {
                let Node::Decision { actor, children } = &game.nodes[id] else {
                    return Err("fixed terminal profile".into());
                };
                if p.len() != game.holdings(*actor) * children.len()
                    || p.iter().any(|x| !x.is_finite() || *x < 0.)
                    || p.chunks(children.len())
                        .any(|r| (r.iter().sum::<f64>() - 1.).abs() > 1e-12)
                {
                    return Err("invalid fixed profile".into());
                }
            }
        }
        let denom = game
            .nodes
            .iter()
            .map(|n| match n {
                Node::Leaf(_) => Vec::new(),
                Node::Decision { actor, .. } => vec![0.; game.holdings(*actor)],
            })
            .collect();
        let work = std::array::from_fn(|s| Workspace::new(&game, s));
        let own_reach = std::array::from_fn(|s| vec![vec![0.; game.holdings(s)]; game.nodes.len()]);
        Ok(Self {
            algorithm: Algorithm::Linear,
            timing: SolverTiming::default(),
            game,
            regrets: shape.clone(),
            numer: shape.clone(),
            denom,
            profile: shape.clone(),
            deltas: shape,
            fixed,
            work,
            own_reach,
            sweeps: 0,
        })
    }

    pub fn set_algorithm(&mut self, algorithm: Algorithm) -> Result<(), String> {
        if self.sweeps != 0 {
            return Err("the algorithm is fixed before the first sweep".into());
        }
        self.algorithm = algorithm;
        Ok(())
    }

    /// Per-leaf clocks for profiling; sweep-level phase timing is always kept.
    pub fn profile_leaves(&mut self) {
        for work in &mut self.work {
            work.timing = Some(LeafTiming::default());
        }
    }

    pub fn timing(&self) -> Value {
        let leaves =
            self.work
                .iter()
                .filter_map(|w| w.timing)
                .fold(None, |sum: Option<LeafTiming>, t| {
                    let s = sum.unwrap_or_default();
                    Some(LeafTiming {
                        fold_seconds: s.fold_seconds + t.fold_seconds,
                        showdown_seconds: s.showdown_seconds + t.showdown_seconds,
                        folds: s.folds + t.folds,
                        showdowns: s.showdowns + t.showdowns,
                    })
                });
        let mut out = json!({"algorithm":self.algorithm.name(),"sweeps":self.sweeps,
            "traversal_seconds":self.timing.traversal_seconds,"update_seconds":self.timing.update_seconds});
        if let Some(l) = leaves {
            out["fold_leaf_seconds"] = json!(l.fold_seconds);
            out["showdown_leaf_seconds"] = json!(l.showdown_seconds);
            out["fold_leaf_evaluations"] = json!(l.folds);
            out["showdown_leaf_evaluations"] = json!(l.showdowns);
            out["traversal_excluding_leaves_seconds"] =
                json!(self.timing.traversal_seconds - l.fold_seconds - l.showdown_seconds);
        }
        out
    }

    pub fn advance(&mut self, count: u64) -> Result<(), String> {
        if count == 0 || self.sweeps.checked_add(count).is_none_or(|s| s > 1_000_000) {
            return Err("positive fixed work up to one million cumulative sweeps required".into());
        }
        for _ in 0..count {
            let started = Instant::now();
            let t = (self.sweeps + 1) as f64;
            let weight = match self.algorithm {
                Algorithm::Linear => t,
                Algorithm::Discounted { .. } => 1.,
            };
            for (id, node) in self.game.nodes.iter().enumerate() {
                if let Node::Decision { children, .. } = node {
                    let k = children.len();
                    if let Some(fixed) = &self.fixed[id] {
                        self.profile[id].copy_from_slice(fixed);
                    } else {
                        for (r, p) in self.regrets[id]
                            .chunks(k)
                            .zip(self.profile[id].chunks_mut(k))
                        {
                            let sum: f64 = r.iter().map(|v| v.max(0.)).sum();
                            for (v, &x) in p.iter_mut().zip(r) {
                                *v = if sum > 0. {
                                    x.max(0.) / sum
                                } else {
                                    1. / k as f64
                                };
                            }
                        }
                    }
                    self.deltas[id].fill(0.);
                }
            }
            let traversal = Instant::now();
            for seat in 0..2 {
                self.work[seat].start();
                visit(
                    &self.game,
                    0,
                    seat,
                    &self.profile,
                    &mut self.deltas,
                    weight,
                    false,
                    true,
                    &mut self.work[seat],
                );
            }
            let traversal = traversal.elapsed().as_secs_f64();
            // Reject numerical failure before changing either player's stored
            // regrets or averages. This prepared API has no partial-sweep mode.
            for workspace in &self.work {
                for row in &workspace.value {
                    for &x in row {
                        finite(x)?;
                    }
                }
            }
            for (regret, delta) in self.regrets.iter().zip(&self.deltas) {
                for (&r, &d) in regret.iter().zip(delta) {
                    finite(r + d)?;
                }
            }
            for seat in 0..2 {
                self.own_reach[seat][0].fill(1.);
                for (id, node) in self.game.nodes.iter().enumerate() {
                    if let Node::Decision { actor, children } = node {
                        let k = children.len();
                        for h in 0..self.game.holdings(seat) {
                            let reach = self.own_reach[seat][id][h];
                            if *actor == seat {
                                self.denom[id][h] += weight * reach;
                                for a in 0..k {
                                    self.numer[id][h * k + a] +=
                                        weight * reach * self.profile[id][h * k + a];
                                }
                            }
                            for (a, &child) in children.iter().enumerate() {
                                self.own_reach[seat][child][h] = reach
                                    * if *actor == seat {
                                        self.profile[id][h * k + a]
                                    } else {
                                        1.
                                    };
                            }
                        }
                    }
                }
            }
            // Both traversers use one frozen profile before regret publication.
            for id in 0..self.game.nodes.len() {
                if self.fixed[id].is_none() {
                    for (r, d) in self.regrets[id].iter_mut().zip(&self.deltas[id]) {
                        *r += d;
                        finite(*r)?;
                    }
                }
            }
            if let Algorithm::Discounted { alpha, beta, gamma } = self.algorithm {
                let positive = t.powf(alpha) / (t.powf(alpha) + 1.);
                let negative = t.powf(beta) / (t.powf(beta) + 1.);
                let average = (t / (t + 1.)).powf(gamma);
                for id in 0..self.game.nodes.len() {
                    if self.fixed[id].is_none() {
                        for r in &mut self.regrets[id] {
                            *r *= if *r > 0. { positive } else { negative };
                        }
                    }
                    for x in self.numer[id].iter_mut().chain(self.denom[id].iter_mut()) {
                        *x *= average;
                    }
                }
            }
            self.sweeps += 1;
            self.timing.traversal_seconds += traversal;
            self.timing.update_seconds += started.elapsed().as_secs_f64() - traversal;
        }
        Ok(())
    }

    /// Root value for `seat`: of `profile`, or with `best` of its best response,
    /// where a non-empty `mask[node]` lists the only actions the responder may use.
    pub fn value(
        &mut self,
        profile: &[Vec<f64>],
        seat: usize,
        best: bool,
        mask: Option<Vec<Vec<bool>>>,
    ) -> Result<f64, String> {
        if profile.len() != self.game.nodes.len()
            || mask
                .as_ref()
                .is_some_and(|m| m.len() != self.game.nodes.len())
        {
            return Err("profile or mask node count differs".into());
        }
        self.work[seat].mask = mask;
        self.work[seat].start();
        visit(
            &self.game,
            0,
            seat,
            profile,
            &mut self.deltas,
            0.,
            best,
            false,
            &mut self.work[seat],
        );
        self.work[seat].mask = None;
        finite(self.work[seat].value[0].iter().sum())
    }

    pub fn node(&self, id: usize) -> &Node {
        &self.game.nodes[id]
    }

    /// Approximate resident bytes of the solver state (f64 arrays only).
    pub fn memory_bytes(&self) -> usize {
        let rows = |v: &Vec<Vec<f64>>| v.iter().map(Vec::len).sum::<usize>();
        8 * (rows(&self.regrets)
            + rows(&self.numer)
            + rows(&self.denom)
            + rows(&self.profile)
            + rows(&self.deltas)
            + self
                .work
                .iter()
                .map(|w| rows(&w.value) + rows(&w.reach))
                .sum::<usize>()
            + self.own_reach.iter().map(rows).sum::<usize>())
    }

    pub fn average(&self) -> Vec<Vec<f64>> {
        self.numer
            .iter()
            .enumerate()
            .map(|(id, row)| {
                if let Some(fixed) = &self.fixed[id] {
                    return fixed.clone();
                }
                let Node::Decision { children, .. } = &self.game.nodes[id] else {
                    return Vec::new();
                };
                let k = children.len();
                row.iter()
                    .enumerate()
                    .map(|(i, &v)| {
                        if self.denom[id][i / k] > 0. {
                            v / self.denom[id][i / k]
                        } else {
                            1. / k as f64
                        }
                    })
                    .collect()
            })
            .collect()
    }

    pub fn quality(&mut self, profile: &[Vec<f64>]) -> Result<Value, String> {
        if profile.len() != self.game.nodes.len() {
            return Err("quality profile node count differs".into());
        }
        for (node, row) in self.game.nodes.iter().zip(profile) {
            match node {
                Node::Leaf(_) if !row.is_empty() => {
                    return Err("quality profile at a terminal".into())
                }
                Node::Decision { actor, children } => {
                    if row.len() != self.game.holdings(*actor) * children.len()
                        || row.iter().any(|x| !x.is_finite() || *x < 0.)
                        || row
                            .chunks(children.len())
                            .any(|r| (r.iter().sum::<f64>() - 1.).abs() > 1e-10)
                    {
                        return Err("invalid quality profile".into());
                    }
                }
                _ => (),
            }
        }
        let mut values = [0.; 2];
        let mut gains = [0.; 2];
        let fixed: Vec<bool> = self.fixed.iter().map(|f| f.is_some()).collect();
        for seat in 0..2 {
            self.work[seat].fixed = fixed.iter().any(|&f| f).then(|| fixed.clone());
            self.work[seat].start();
            visit(
                &self.game,
                0,
                seat,
                profile,
                &mut self.deltas,
                0.,
                false,
                false,
                &mut self.work[seat],
            );
            values[seat] = self.work[seat].value[0].iter().sum();
            self.work[seat].start();
            visit(
                &self.game,
                0,
                seat,
                profile,
                &mut self.deltas,
                0.,
                true,
                false,
                &mut self.work[seat],
            );
            let response: f64 = self.work[seat].value[0].iter().sum();
            gains[seat] = (response - values[seat]).max(0.);
        }
        for &x in values.iter().chain(gains.iter()) {
            finite(x)?;
        }
        let exploitability = (gains[0] + gains[1]) / 2.;
        Ok(
            json!({"profile_values_bb":values,"best_response_gains_bb":gains,"exploitability_bb":exploitability,"exploitability_root_pot":exploitability/self.game.root_pot_bb,"zero_sum_error_bb":(values[0]+values[1]).abs()}),
        )
    }
}

mod prepared;
pub use prepared::request;
pub mod live;

#[cfg(test)]
mod tests;
