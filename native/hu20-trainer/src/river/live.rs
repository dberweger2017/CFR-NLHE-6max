//! Opt-in legal public-history adapter. No deck or other private hand input.
use super::{Algorithm, Game, Holding, Node, Solver, Terminal, DCFR};
use crate::{
    cards::EquityTables,
    game::{Kind, Street},
    multi_holdem,
    multi_policy::PolicyTable,
    nplayer::{Action, Config, Event, Hand, Observation},
};
use serde_json::{json, Value};
use std::{collections::HashMap, time::Instant};

mod exact;
mod harms;

pub const LAW: &str = "three-product-action-posterior-active-marginal-projection-v1";

fn fields(v: &Value, names: &[&str]) -> Result<(), String> {
    if v.as_object()
        .ok_or("expected object")?
        .keys()
        .any(|k| !names.contains(&k.as_str()))
    {
        return Err("unexpected field in legal river request".into());
    }
    Ok(())
}
fn uint(v: &Value) -> Result<u64, String> {
    v.as_u64().ok_or("expected unsigned integer".into())
}
fn array(v: &Value) -> Result<&Vec<Value>, String> {
    v.as_array().ok_or("expected array".into())
}
fn card(v: &Value) -> Result<u8, String> {
    let c = uint(v)?;
    if c >= 52 {
        return Err("invalid card".into());
    }
    Ok(c as u8)
}
fn kind(v: &Value) -> Result<Kind, String> {
    match v.as_str() {
        Some("fold") => Ok(Kind::Fold),
        Some("check") => Ok(Kind::Check),
        Some("call") => Ok(Kind::Call),
        Some("raise") => Ok(Kind::Raise),
        _ => Err("unknown action kind".into()),
    }
}

/// Deterministic representative cards are betting-only simulator scaffolding.
/// Every range lookup overrides the observation's own holding explicitly.
fn representative(config: Config, button: usize, board: [u8; 5]) -> Result<Hand, String> {
    let mut seen = 0u64;
    for c in board {
        if seen & (1u64 << c) != 0 {
            return Err("duplicate board card".into());
        }
        seen |= 1u64 << c;
    }
    let rest: Vec<_> = (0..52).filter(|c| seen & (1u64 << c) == 0).collect();
    let deck: Vec<_> = rest[..6]
        .iter()
        .chain(board.iter())
        .chain(rest[6..].iter())
        .copied()
        .collect();
    Hand::from_deck(config, button, &deck)
}

struct PublicRoot {
    /// The first river decision; `prefix` holds the opponent's river action already taken
    /// when the hero acts second (empty when the hero acts first).
    hand: Hand,
    prefix: Vec<Action>,
    prior: Vec<(Hand, Action)>,
    board: [u8; 5],
    seat: usize,
    hole: [u8; 2],
    live: [usize; 2],
}
impl PublicRoot {
    /// The hero's decision: the first river decision with the opponent's prefix applied.
    fn decision(&self) -> Result<Hand, String> {
        let mut hand = self.hand.clone();
        for &a in &self.prefix {
            hand.apply_mut(a)?;
        }
        Ok(hand)
    }
}

fn reconstruct(v: &Value, config: Config) -> Result<PublicRoot, String> {
    fields(
        v,
        &[
            "format",
            "button",
            "board",
            "seat",
            "hole",
            "actions",
            "players",
            "legal",
            "sweeps",
            "debug",
            "mode",
            "algorithm",
            "checkpoints",
            "stop_at_target",
            "profile",
            "reference_checkpoints",
            "reference_tolerance_bb",
            "target",
            "search_menu",
            "omitted",
            "matched_accuracy",
            "belief_backend",
        ],
    )?;
    if v["format"] != "nplayer-live-river-v1"
        || config.players() != 3
        || config.stacks() != [10000, 10000, 10000]
        || config.small_blind() != 50
        || config.big_blind() != 100
    {
        return Err("expected three-player 100 BB legal river identity".into());
    }
    let b = array(&v["board"])?;
    if b.len() != 5 {
        return Err("complete board required".into());
    }
    let mut board = [0; 5];
    for (i, c) in b.iter().enumerate() {
        board[i] = card(c)?;
    }
    let mut hand = representative(config, uint(&v["button"])? as usize, board)?;
    let mut prior = Vec::new();
    let mut prefix = Vec::new();
    let mut river_start: Option<Hand> = None;
    let hero_seat = uint(&v["seat"])? as usize;
    let actions = array(&v["actions"])?;
    if actions.len() > 256 {
        return Err("public action count outside support".into());
    }
    for e in actions {
        let a = array(e)?;
        if a.len() != 5 {
            return Err("public action needs actor/street/kind/target/payment".into());
        }
        let actor = hand.actor().ok_or("history continues after settlement")?;
        // River actions are admitted only before the hero's first river decision.
        if uint(&a[0])? as usize != actor
            || uint(&a[1])? != hand.street() as u64
            || (hand.street() == Street::River && actor == hero_seat)
        {
            return Err("history must end at the hero's first river decision".into());
        }
        let action = Action {
            kind: kind(&a[2])?,
            raise_to: uint(&a[3])?,
        };
        let obs = hand.observe(actor)?;
        if !multi_holdem::menu(&obs).iter().any(|(_, x)| *x == action) {
            return Err("public action outside blueprint menu".into());
        }
        if hand.street() == Street::River {
            river_start.get_or_insert_with(|| hand.clone());
            prefix.push(action);
        } else {
            prior.push((hand.clone(), action));
        }
        hand.apply_mut(action)?;
        match hand
            .history()
            .iter()
            .rev()
            .find(|x| matches!(x, Event::Action { .. }))
        {
            Some(Event::Action { paid, .. }) if *paid == uint(&a[4])? => (),
            _ => return Err("public action payment differs".into()),
        }
    }
    let seat = uint(&v["seat"])? as usize;
    if hand.street() != Street::River || hand.actor() != Some(seat) {
        return Err("acting first-river observation required".into());
    }
    let hole = array(&v["hole"])?;
    if hole.len() != 2 {
        return Err("own holding required".into());
    }
    let mut hole = [card(&hole[0])?, card(&hole[1])?];
    hole.sort_unstable();
    if hole[0] == hole[1] || hole.iter().any(|c| board.contains(c)) {
        return Err("invalid own holding".into());
    }
    // The solved root is the first river decision; a prefix is the opponent's single first action.
    let root_hand = river_start.unwrap_or_else(|| hand.clone());
    if prefix.len() > 1 {
        return Err("the hero must act on its first river decision".into());
    }
    let live: Vec<_> = root_hand
        .players()
        .iter()
        .enumerate()
        .filter_map(|(s, p)| (!p.folded).then_some(s))
        .collect();
    if live.len() != 2
        || !live.contains(&seat)
        || live.iter().any(|&s| root_hand.players()[s].stack == 0)
        || root_hand.players()[live[0]].contributed != root_hand.players()[live[1]].contributed
        || root_hand
            .players()
            .iter()
            .any(|p| p.contributed > root_hand.players()[live[0]].contributed)
        || hand.players()[seat].folded
        || live.iter().any(|&s| hand.players()[s].stack == 0)
    {
        return Err("needs two live non-all-in seats and one contested root pot".into());
    }
    let players: Vec<_> = hand
        .players()
        .iter()
        .map(|p| json!([p.stack, p.street_bet, p.contributed, p.folded]))
        .collect();
    if v["players"] != json!(players) {
        return Err("public player snapshot differs from history".into());
    }
    let legal = hand.legal().ok_or("no legal actions")?;
    if v["legal"]
        != json!({"check":legal.check,"call_amount":legal.call_amount,"raise_to":legal.raise_to})
    {
        return Err("legal bounds differ from history".into());
    }
    Ok(PublicRoot {
        hand: root_hand,
        prefix,
        prior,
        board,
        seat,
        hole,
        live: [live[0], live[1]],
    })
}

#[derive(Default)]
struct Coverage {
    positive: u64,
    zero: u64,
    missing: u64,
    unknown: u64,
    decisions: u64,
}
impl Coverage {
    fn json(&self) -> Value {
        json!({"positive_mass":self.positive,"zero_mass":self.zero,"missing":self.missing,"mass_unknown":self.unknown,"public_decisions":self.decisions})
    }
}

/// Public action likelihoods, including the folded seat; normalized in log space.
fn likelihoods<F>(
    root: &PublicRoot,
    pairs: &[[u8; 2]],
    mut lookup: F,
) -> Result<([Vec<f64>; 3], [Coverage; 3]), String>
where
    F: FnMut(&Observation<'_>) -> Result<(Vec<f64>, u8), String>,
{
    let mut log: [Vec<f64>; 3] = std::array::from_fn(|_| vec![0.; pairs.len()]);
    let mut coverage: [Coverage; 3] = std::array::from_fn(|_| Coverage::default());
    for (prior, action) in &root.prior {
        let actor = prior.actor().unwrap();
        coverage[actor].decisions += 1;
        let mut observation = prior.observe(actor)?;
        let menu = multi_holdem::menu(&observation);
        let chosen = menu
            .iter()
            .position(|(_, a)| a == action)
            .ok_or("unrepresented action")?;
        for (i, &pair) in pairs.iter().enumerate() {
            observation.hole = pair;
            let (p, tag) = lookup(&observation)?;
            if p.len() != menu.len()
                || p.iter().any(|x| !x.is_finite() || *x < 0.)
                || (p.iter().sum::<f64>() - 1.).abs() > 1e-10
            {
                return Err("invalid blueprint action probabilities".into());
            }
            match tag {
                0 => coverage[actor].missing += 1,
                1 => coverage[actor].positive += 1,
                2 => coverage[actor].zero += 1,
                _ => coverage[actor].unknown += 1,
            }
            log[actor][i] += p[chosen].ln();
        }
    }
    for row in &mut log {
        let max = row.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        if !max.is_finite() {
            return Err("public action sequence has zero modeled likelihood".into());
        }
        for x in row.iter_mut() {
            *x = (*x - max).exp();
        }
        let sum: f64 = row.iter().sum();
        for x in row {
            *x /= sum;
        }
    }
    Ok((log, coverage))
}

struct FoldRemoval {
    singles: [f64; 52],
    pairs: [[f64; 52]; 52],
    positive: Vec<([u8; 2], f64)>,
}
impl FoldRemoval {
    fn new(holdings: &[[u8; 2]], weights: &[f64]) -> Self {
        let mut out = Self {
            singles: [0.; 52],
            pairs: [[0.; 52]; 52],
            positive: Vec::new(),
        };
        for (&[a, b], &w) in holdings.iter().zip(weights) {
            if w > 0. {
                out.positive.push(([a, b], w));
            }
            out.singles[a as usize] += w;
            out.singles[b as usize] += w;
            out.pairs[a as usize][b as usize] = w;
            out.pairs[b as usize][a as usize] = w;
        }
        out
    }
    // For four distinct active cards: a folded hand contains at most two of
    // them, so inclusion-exclusion terminates exactly at pair intersections.
    fn compatible(&self, a: [u8; 2], b: [u8; 2]) -> f64 {
        let cards = [a[0] as usize, a[1] as usize, b[0] as usize, b[1] as usize];
        let mut z = 1.;
        for i in 0..4 {
            z -= self.singles[cards[i]];
            for j in 0..i {
                z += self.pairs[cards[i]][cards[j]];
            }
        }
        if z < 1e-10 {
            // An exactly impossible folded assignment must remain zero.
            self.positive
                .iter()
                .filter(|(h, _)| disjoint(*h, a) && disjoint(*h, b))
                .map(|(_, w)| w)
                .sum()
        } else {
            z.min(1.)
        }
    }
}
fn disjoint(a: [u8; 2], b: [u8; 2]) -> bool {
    a.iter().all(|c| !b.contains(c))
}

/// Exact active marginals of the stipulated three-product likelihood law,
/// then an explicit product projection. The residual correlation is measured.
fn project(
    pairs: &[[u8; 2]],
    weights: &[Vec<f64>; 3],
    live: [usize; 2],
) -> Result<([Vec<Holding>; 2], Value), String> {
    project_with_joint(pairs, weights, live, false).map(|(r, v, _)| (r, v))
}

/// As `project`; with `keep_joint`, also returns the original active joint law
/// (row-major over `pairs` x `pairs`) that the product projection replaces.
fn project_with_joint(
    pairs: &[[u8; 2]],
    weights: &[Vec<f64>; 3],
    live: [usize; 2],
    keep_joint: bool,
) -> Result<([Vec<Holding>; 2], Value, Option<Vec<f64>>), String> {
    let folded = (0..3).find(|s| !live.contains(s)).unwrap();
    let removal = FoldRemoval::new(pairs, &weights[folded]);
    let mut marginal: [Vec<f64>; 2] = std::array::from_fn(|_| vec![0.; pairs.len()]);
    let mut z = 0.;
    for (i, &a) in pairs.iter().enumerate() {
        for (j, &b) in pairs.iter().enumerate() {
            if disjoint(a, b) {
                let w = weights[live[0]][i] * weights[live[1]][j] * removal.compatible(a, b);
                z += w;
                marginal[0][i] += w;
                marginal[1][j] += w;
            }
        }
    }
    // Do not amplify inclusion-exclusion cancellation in a nearly blocked law.
    if !z.is_finite() || z < 1e-4 {
        return Err("three-seat compatible chance mass below supported conditioning floor".into());
    }
    for m in &mut marginal {
        for x in m {
            *x /= z;
        }
    }
    let mut projected_z = 0.;
    for (i, &a) in pairs.iter().enumerate() {
        for (j, &b) in pairs.iter().enumerate() {
            if disjoint(a, b) {
                projected_z += marginal[0][i] * marginal[1][j];
            }
        }
    }
    if projected_z <= 0. {
        return Err("empty projected range law".into());
    }
    let mut tv = 0.;
    let n = pairs.len();
    let mut joint = keep_joint.then(|| vec![0.; n * n]);
    for (i, &a) in pairs.iter().enumerate() {
        for (j, &b) in pairs.iter().enumerate() {
            if disjoint(a, b) {
                let p = weights[live[0]][i] * weights[live[1]][j] * removal.compatible(a, b) / z;
                let q = marginal[0][i] * marginal[1][j] / projected_z;
                tv += (p - q).abs() / 2.;
                if let Some(joint) = &mut joint {
                    joint[i * n + j] = p;
                }
            }
        }
    }
    let ranges = std::array::from_fn(|s| {
        pairs
            .iter()
            .zip(&marginal[s])
            .map(|(&cards, &weight)| Holding { cards, weight })
            .collect()
    });
    Ok((
        ranges,
        json!({"law":LAW,"three_seat_compatible_mass":z,"projection_total_variation":tv,"folded_seat":folded,"exact_posterior":false}),
        joint,
    ))
}

/// The declared search game's action menu. `Full` is the production menu at
/// every node. A capped menu keeps the production menu at the root; below it,
/// only fold, check or call, the pot-size raise and the production all-in,
/// and no raise once the river already has `cap` raises, the root's included.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SearchMenu {
    Full,
    Capped(usize),
    RootCheckMinOpen,
    // RootCheckMinOpen plus the opponent's minimum raise as the first
    // response to a root bet.
    RootMinResponses,
}
impl SearchMenu {
    fn parse(v: Option<&Value>) -> Result<Self, String> {
        match v.map(|x| x.as_str()) {
            None | Some(Some("full")) => Ok(Self::Full),
            Some(Some("pot-jam-cap2-v1")) => Ok(Self::Capped(2)),
            Some(Some("pot-jam-cap3-v1")) => Ok(Self::Capped(3)),
            Some(Some("pot-jam-cap3-root-check-min-v1")) => Ok(Self::RootCheckMinOpen),
            Some(Some("pot-jam-cap3-root-min-responses-v1")) => Ok(Self::RootMinResponses),
            _ => Err("unknown declared search_menu".into()),
        }
    }
    fn name(self) -> String {
        match self {
            Self::Full => "full".into(),
            Self::Capped(cap) => format!("pot-jam-cap{cap}-v1"),
            Self::RootCheckMinOpen => "pot-jam-cap3-root-check-min-v1".into(),
            Self::RootMinResponses => "pot-jam-cap3-root-min-responses-v1".into(),
        }
    }
    fn actions(self, hand: &Hand, root: bool) -> Result<Vec<Action>, String> {
        let actor = hand.actor().ok_or("no actor in unfinished hand")?;
        let observation = hand.observe(actor)?;
        let full = multi_holdem::menu(&observation);
        let cap = match self {
            Self::Capped(cap) if !root => cap,
            Self::RootCheckMinOpen | Self::RootMinResponses if !root => 3,
            _ => return Ok(full.into_iter().map(|(_, a)| a).collect()),
        };
        // This arm adds exactly the first opponent's minimum opening bet after
        // a root check. It does not restore later minimum-raise ladders.
        let mut river = hand.history().iter().filter_map(|e| match e {
            Event::Action {
                street: Street::River,
                action,
                ..
            } => Some(action),
            _ => None,
        });
        // The first river action is the root's; a minimum is added only at the
        // single decision right after it.
        let first = river.next().map(|a| a.kind);
        let first_response = river.next().is_none();
        let minimum_open = matches!(self, Self::RootCheckMinOpen | Self::RootMinResponses)
            && first == Some(Kind::Check)
            && first_response;
        let minimum_raise =
            self == Self::RootMinResponses && first == Some(Kind::Raise) && first_response;
        let raises = hand
            .history()
            .iter()
            .filter(|e| {
                matches!(e, Event::Action { street: Street::River, action, .. } if action.kind == Kind::Raise)
            })
            .count();
        let legal = observation
            .legal
            .ok_or("acting observation has no legal actions")?;
        let matched = observation.players[actor].street_bet + legal.call_amount;
        let pot: u64 = observation.players.iter().map(|p| p.contributed).sum();
        let after_call = pot + legal.call_amount;
        Ok(full
            .into_iter()
            .filter(|(label, a)| {
                a.kind != Kind::Raise
                    || (raises < cap
                        && legal.raise_to.is_some_and(|(low, high)| {
                            *label == 5
                                || ((minimum_open || minimum_raise) && *label == 3)
                                || a.raise_to == (matched + after_call).clamp(low, high)
                        }))
            })
            .map(|(_, a)| a)
            .collect())
    }
}

fn path_key(path: &[Action]) -> Vec<(u8, u64)> {
    path.iter().map(|a| (a.kind as u8, a.raise_to)).collect()
}

struct Tree {
    nodes: Vec<Node>,
    menus: Vec<Vec<Action>>,
    // River actions from the root to each node; maps one tree onto another.
    paths: Vec<Vec<Action>>,
    path: Vec<Action>,
    menu: SearchMenu,
    max_nodes: usize,
    live: [usize; 2],
    stacks: [u64; 2],
    pot: u64,
    bb: f64,
}
impl Tree {
    fn new(hand: &Hand, live: [usize; 2], menu: SearchMenu, max_nodes: usize) -> Self {
        Self {
            nodes: Vec::new(),
            menus: Vec::new(),
            paths: Vec::new(),
            path: Vec::new(),
            menu,
            max_nodes,
            live,
            stacks: live.map(|s| hand.players()[s].stack),
            pot: hand.pot(),
            bb: 100.,
        }
    }
    fn compile(&mut self, hand: &mut Hand) -> Result<usize, String> {
        if self.nodes.len() >= self.max_nodes {
            return Err(format!(
                "unsupported {} tree exceeds {} nodes; no menu truncation",
                self.menu.name(),
                self.max_nodes
            ));
        }
        let id = self.nodes.len();
        self.nodes.push(Node::Leaf(Terminal {
            base: 0.,
            win0: 0.,
            tie0: 0.,
        }));
        self.menus.push(Vec::new());
        self.paths.push(self.path.clone());
        if hand.finished() {
            let first = self.live[0];
            let settled = hand.settlement().ok_or("no terminal ledger")?;
            let mut payout = settled.refunds[first] as f64;
            let (mut contested, mut tie) = (0u64, 0u64);
            let both = (1 << self.live[0]) | (1 << self.live[1]);
            let first_left = if (self.live[0] + 3 - hand.button() - 1) % 3
                < (self.live[1] + 3 - hand.button() - 1) % 3
            {
                self.live[0]
            } else {
                self.live[1]
            };
            for p in settled.pots() {
                if p.eligible == both {
                    contested += p.amount;
                    tie += p.amount / 2 + u64::from(p.amount % 2 == 1 && first_left == first);
                } else if p.eligible == 1 << first {
                    payout += p.amount as f64;
                } else if p.eligible != 1 << self.live[1] {
                    return Err("unexpected terminal pot eligibility".into());
                }
            }
            let paid = settled.contributions[first] as f64
                - (hand.config().stacks()[first] - self.stacks[0]) as f64;
            self.nodes[id] = Node::Leaf(Terminal {
                base: (payout - paid - self.pot as f64 / 2.) / self.bb,
                win0: contested as f64 / self.bb,
                tie0: tie as f64 / self.bb,
            });
        } else {
            let actor = hand.actor().unwrap();
            let seat = self
                .live
                .iter()
                .position(|&s| s == actor)
                .ok_or("unexpected live actor")?;
            let menu = self.menu.actions(hand, id == 0)?;
            let mut children = Vec::new();
            for action in &menu {
                let saved = hand.save();
                hand.apply_mut(*action)?;
                self.path.push(*action);
                let child = self.compile(hand);
                self.path.pop();
                hand.restore(saved);
                children.push(child?);
            }
            self.menus[id] = menu;
            self.nodes[id] = Node::Decision {
                actor: seat,
                children,
            };
        }
        Ok(id)
    }
}

/// Full production-menu tree size, counted without allocating terminals.
/// Counting stops once `cap` nodes are reached; a stopped count is a lower bound.
fn count_tree(
    hand: &mut Hand,
    live: [usize; 2],
    menu: SearchMenu,
    cap: usize,
    nodes: &mut usize,
    action_rows: &mut usize,
) -> Result<bool, String> {
    let root = *nodes == 0;
    *nodes += 1;
    if *nodes > cap {
        return Ok(false);
    }
    if hand.finished() {
        return Ok(true);
    }
    let actor = hand.actor().ok_or("no actor in unfinished hand")?;
    if !live.contains(&actor) {
        return Err("unexpected live actor".into());
    }
    let actions = menu.actions(hand, root)?;
    *action_rows += actions.len();
    for action in &actions {
        let saved = hand.save();
        hand.apply_mut(*action)?;
        let complete = count_tree(hand, live, menu, cap, nodes, action_rows);
        hand.restore(saved);
        if !complete? {
            return Ok(false);
        }
    }
    Ok(true)
}

pub const CLASSIFY_NODE_CAP: usize = 100_000;
// The live solver's support limits (`Tree::compile` and `Game::new`).
const SUPPORTED_NODES: usize = super::MAX_NODES;
const SUPPORTED_CELLS: usize = super::MAX_STRATEGY_CELLS;
// Offline omitted-raise evaluation games may exceed the live limits.
const EVALUATION_NODES: usize = 20_000;
const EVALUATION_CELLS: usize = 50_000_000;

/// Support and belief diagnostics for one legal root, without solving.
/// Every rejection reason that applies is reported, not only the first.
fn classify(
    root: &PublicRoot,
    pairs: &[[u8; 2]],
    menu: SearchMenu,
    table: &PolicyTable,
    tables: &EquityTables,
) -> Result<Value, String> {
    let tick = Instant::now();
    let mut rejections = Vec::new();
    let beliefs = likelihoods(root, pairs, |obs| blueprint_row(obs, table, tables));
    let likelihood_seconds = tick.elapsed().as_secs_f64();
    let (mut law, mut coverage, mut own_reach) = (Value::Null, Value::Null, Value::Null);
    match beliefs {
        // Corrupt model rows stay fatal, exactly as in a solve request.
        Err(error)
            if error.contains("invalid blueprint") || error.contains("blueprint key/menu") =>
        {
            return Err(error)
        }
        Err(error) => rejections.push(json!({"reason":"likelihood","detail":error})),
        Ok((likelihood, counts)) => {
            coverage = json!(counts.map(|c| c.json()));
            match project(pairs, &likelihood, root.live) {
                Err(error) => rejections.push(json!({"reason":"projection","detail":error})),
                Ok((ranges, projected)) => {
                    law = projected;
                    let hero = root.live.iter().position(|&s| s == root.seat).unwrap();
                    let holding = pairs
                        .iter()
                        .position(|h| *h == root.hole)
                        .ok_or("own hand outside range")?;
                    let weight = ranges[hero][holding].weight;
                    let largest = ranges[hero].iter().map(|h| h.weight).fold(0., f64::max);
                    own_reach = json!(weight / largest);
                    if weight == 0. {
                        rejections.push(json!({"reason":"own-zero-reach"}));
                    }
                }
            }
        }
    }
    let tick = Instant::now();
    let count = |menu: SearchMenu| -> Result<Value, String> {
        let (mut nodes, mut action_rows) = (0, 0);
        let complete = count_tree(
            &mut root.hand.clone(),
            root.live,
            menu,
            CLASSIFY_NODE_CAP,
            &mut nodes,
            &mut action_rows,
        )?;
        let cells = action_rows * pairs.len();
        Ok(
            json!({"menu":menu.name(),"nodes":if complete {json!(nodes)} else {Value::Null},"count_complete":complete,
            "count_cap":CLASSIFY_NODE_CAP,"action_rows":if complete {json!(action_rows)} else {Value::Null},
            "strategy_cells":if complete {json!(cells)} else {Value::Null},
            "within_limits":complete && nodes <= SUPPORTED_NODES && cells <= SUPPORTED_CELLS}),
        )
    };
    let full = count(SearchMenu::Full)?;
    let searched = count(menu)?;
    let count_seconds = tick.elapsed().as_secs_f64();
    let complete = searched["count_complete"] == true;
    if !complete || searched["nodes"].as_u64().unwrap() as usize > SUPPORTED_NODES {
        rejections.push(json!({"reason":"tree-nodes"}));
    }
    if !complete || searched["strategy_cells"].as_u64().unwrap() as usize > SUPPORTED_CELLS {
        rejections.push(json!({"reason":"strategy-cells"}));
    }
    Ok(
        json!({"format":"nplayer-live-river-classification-v1","live":root.live,"seat":root.seat,
        "pot":root.hand.pot(),"stacks":root.live.map(|s| root.hand.players()[s].stack),
        "full_menu":full,"search_menu":searched,
        "supported_limits":{"nodes":SUPPORTED_NODES,"strategy_cells":SUPPORTED_CELLS},
        "supported":rejections.is_empty(),"rejections":rejections,"law":law,"coverage":coverage,
        "own_reach_relative_to_max":own_reach,
        "timings":{"likelihood_and_projection_seconds":likelihood_seconds,"tree_count_seconds":count_seconds}}),
    )
}

fn blueprint_row(
    obs: &Observation<'_>,
    table: &PolicyTable,
    tables: &EquityTables,
) -> Result<(Vec<f64>, u8), String> {
    let d = multi_holdem::observation_decision(obs, tables);
    match table.rows.get(&d.key) {
        Some(r) => {
            if (r.owner as usize, r.street as usize, r.code) != (d.owner, d.street, d.code) {
                return Err("blueprint key/menu identity mismatch".into());
            }
            Ok((
                r.probabilities.to_vec(),
                match r.original_average_mass {
                    Some(true) => 1,
                    Some(false) => 2,
                    None => 3,
                },
            ))
        }
        None => Ok((vec![1. / d.len() as f64; d.len()], 0)),
    }
}

/// The deployed policy in the full-menu game: the capped solution on its own
/// histories, and the blueprint after any omitted raise. The blueprint alone is
/// the no-search baseline in the same game.
struct FullMenu {
    tree: Tree,
    // The capped node each full-menu node maps to, if it is on the capped tree.
    capped_of: Vec<Option<usize>>,
    deployed: Vec<Vec<f64>>,
    blueprint: Vec<Vec<f64>>,
    solver: Solver,
}

fn full_menu(
    root: &PublicRoot,
    pairs: &[[u8; 2]],
    ranges: [Vec<Holding>; 2],
    capped: &Tree,
    average: &[Vec<f64>],
    table: &PolicyTable,
    tables: &EquityTables,
) -> Result<FullMenu, String> {
    let mut full = Tree::new(&root.hand, root.live, SearchMenu::Full, EVALUATION_NODES);
    full.compile(&mut root.hand.clone())?;
    let index: HashMap<_, _> = capped
        .paths
        .iter()
        .enumerate()
        .map(|(i, p)| (path_key(p), i))
        .collect();
    let capped_of: Vec<_> = full
        .paths
        .iter()
        .map(|p| index.get(&path_key(p)).copied())
        .collect();
    let mut deployed = Vec::with_capacity(full.nodes.len());
    let mut blueprint = Vec::with_capacity(full.nodes.len());
    for (id, node) in full.nodes.iter().enumerate() {
        let Node::Decision { actor, children } = node else {
            deployed.push(Vec::new());
            blueprint.push(Vec::new());
            continue;
        };
        let k = children.len();
        let mut hand = root.hand.clone();
        for a in &full.paths[id] {
            hand.apply_mut(*a)?;
        }
        let mut observation = hand.observe(root.live[*actor])?;
        let mut baseline = vec![0.; pairs.len() * k];
        for (h, &pair) in pairs.iter().enumerate() {
            observation.hole = pair;
            let (p, _) = blueprint_row(&observation, table, tables)?;
            if p.len() != k {
                return Err("blueprint row differs from the full menu".into());
            }
            baseline[h * k..(h + 1) * k].copy_from_slice(&p);
        }
        if let Some(c) = capped_of[id] {
            let mut row = vec![0.; pairs.len() * k];
            let kc = capped.menus[c].len();
            for (j, a) in capped.menus[c].iter().enumerate() {
                let f = full.menus[id]
                    .iter()
                    .position(|b| b == a)
                    .ok_or("capped action outside the full menu")?;
                for h in 0..pairs.len() {
                    row[h * k + f] = average[c][h * kc + j];
                }
            }
            deployed.push(row);
        } else {
            deployed.push(baseline.clone());
        }
        blueprint.push(baseline);
    }
    let nodes = full.nodes.len();
    let game = Game::with_limits(
        root.board,
        ranges,
        std::mem::take(&mut full.nodes),
        root.hand.pot() as f64 / 100.,
        EVALUATION_NODES,
        EVALUATION_CELLS,
    )?;
    let solver = Solver::new(game, vec![None; nodes])?;
    Ok(FullMenu {
        tree: full,
        capped_of,
        deployed,
        blueprint,
        solver,
    })
}

fn deployed_quality(
    root: &PublicRoot,
    pairs: &[[u8; 2]],
    ranges: [Vec<Holding>; 2],
    capped: &Tree,
    average: &[Vec<f64>],
    table: &PolicyTable,
    tables: &EquityTables,
) -> Result<Value, String> {
    let mut f = full_menu(root, pairs, ranges, capped, average, table, tables)?;
    let decisions = f.deployed.iter().filter(|r| !r.is_empty()).count();
    let on_tree = (0..f.capped_of.len())
        .filter(|&i| !f.deployed[i].is_empty() && f.capped_of[i].is_some())
        .count();
    let quality = f.solver.quality(&f.deployed)?;
    let blueprint_quality = f.solver.quality(&f.blueprint)?;
    Ok(
        json!({"full_menu_nodes":f.capped_of.len(),"capped_decisions":on_tree,
        "blueprint_fallback_decisions":decisions - on_tree,
        "hero_game_seat":root.live.iter().position(|&s| s == root.seat),
        "quality":quality,"blueprint_only_quality":blueprint_quality}),
    )
}

/// Where the deployed policy's full-menu vulnerability comes from. For each
/// player, the best-response gain with only the capped actions, and with the
/// capped actions plus one omitted action at one on-tree node (an entry). Each
/// gain is a full reach-weighted value in the full-menu game.
fn diagnose(
    root: &PublicRoot,
    pairs: &[[u8; 2]],
    ranges: [Vec<Holding>; 2],
    capped: &Tree,
    average: &[Vec<f64>],
    table: &PolicyTable,
    tables: &EquityTables,
) -> Result<Value, String> {
    let mut f = full_menu(root, pairs, ranges, capped, average, table, tables)?;
    let nodes = f.capped_of.len();
    let mut players = Vec::new();
    for seat in 0..2 {
        let value = f.solver.value(&f.deployed, seat, false, None)?;
        let full = f.solver.value(&f.deployed, seat, true, None)? - value;
        let blueprint = f.solver.value(&f.blueprint, seat, true, None)?
            - f.solver.value(&f.blueprint, seat, false, None)?;
        // Capped-only mask: on the capped tree, this player may use only capped actions.
        let mut mask = vec![Vec::new(); nodes];
        let mut entries = Vec::new();
        for id in 0..nodes {
            let (Some(c), false) = (f.capped_of[id], f.deployed[id].is_empty()) else {
                continue;
            };
            let k = f.tree.menus[id].len();
            if actor_of(&f, id) != seat {
                continue;
            }
            mask[id] = f.tree.menus[id]
                .iter()
                .map(|a| capped.menus[c].contains(a))
                .collect();
            for j in 0..k {
                if !mask[id][j] {
                    entries.push((id, j));
                }
            }
        }
        let capped_only = f
            .solver
            .value(&f.deployed, seat, true, Some(mask.clone()))?
            - value;
        let mut rows = Vec::new();
        for (id, j) in entries {
            let mut m = mask.clone();
            m[id][j] = true;
            let gain = f.solver.value(&f.deployed, seat, true, Some(m))? - value;
            let mut hand = root.hand.clone();
            for a in &f.tree.paths[id] {
                hand.apply_mut(*a)?;
            }
            let obs = hand.observe(root.live[seat])?;
            let legal = obs.legal.ok_or("entry without legal actions")?;
            let action = f.tree.menus[id][j];
            let label = multi_holdem::menu(&obs)
                .iter()
                .find(|(_, a)| *a == action)
                .map(|(l, _)| *l)
                .ok_or("omitted action outside the production menu")?;
            let raises = f.tree.paths[id]
                .iter()
                .filter(|a| a.kind == Kind::Raise)
                .count();
            rows.push(json!({"node":id,"path":f.tree.paths[id].iter().map(|a|json!([a.kind.name(),a.raise_to])).collect::<Vec<_>>(),
                "action":[action.kind.name(),action.raise_to],"label":label,"river_raises_before":raises,
                "facing_bet":legal.call_amount > 0,"gain_bb":gain,"increment_over_capped_bb":gain - capped_only}));
        }
        players.push(json!({"game_seat":seat,"live_seat":root.live[seat],"hero":root.live[seat] == root.seat,
            "full_menu_gain_bb":full,"capped_actions_only_gain_bb":capped_only,"blueprint_only_gain_bb":blueprint,
            "entries":rows}));
    }
    Ok(
        json!({"format":"nplayer-live-river-diagnosis-v1","full_menu_nodes":nodes,
        "pot_bb":root.hand.pot() as f64 / 100.,"players":players}),
    )
}

fn actor_of(f: &FullMenu, id: usize) -> usize {
    match f.solver.node(id) {
        Node::Decision { actor, .. } => *actor,
        Node::Leaf(_) => usize::MAX,
    }
}

/// The quality target: each player's gain within min(fraction of the pot, cap).
/// The default is the frozen deployment target, min(1% of the pot, 0.1 BB).
fn quality_target(v: Option<&Value>, pot_bb: f64) -> Result<f64, String> {
    let Some(v) = v else {
        return Ok((0.01 * pot_bb).min(0.1));
    };
    let positive = |name: &str| {
        v[name]
            .as_f64()
            .filter(|x| x.is_finite() && *x > 0.)
            .ok_or_else(|| format!("target.{name} must be positive"))
    };
    Ok((positive("pot_fraction")? * pot_bb).min(positive("cap_bb")?))
}

const MAX_LIVE_SWEEPS: u64 = 8192;

fn fixed_sweeps(v: &Value) -> Result<u64, String> {
    let count = uint(v)?;
    if !(1..=MAX_LIVE_SWEEPS).contains(&count) {
        return Err("supports fixed 1..8192 sweeps".into());
    }
    Ok(count)
}

fn sweep_list(v: Option<&Value>) -> Result<Vec<u64>, String> {
    let list: Vec<u64> = array(v.ok_or("checkpoint list required")?)?
        .iter()
        .map(uint)
        .collect::<Result<_, _>>()?;
    if list.is_empty()
        || list[0] == 0
        || list.windows(2).any(|w| w[0] >= w[1])
        || *list.last().unwrap() > MAX_LIVE_SWEEPS
    {
        return Err("checkpoints must increase within 1..8192".into());
    }
    Ok(list)
}

fn gains(quality: &Value) -> Vec<f64> {
    quality["best_response_gains_bb"]
        .as_array()
        .unwrap()
        .iter()
        .map(|g| g.as_f64().unwrap())
        .collect()
}

struct Run {
    average: Vec<Vec<f64>>,
    quality: Value,
    sweeps: u64,
    seconds: f64,
    met: bool,
}

/// DCFR with quality checks at each checkpoint, stopping once both players'
/// gains are within `tolerance` or the checkpoints run out.
fn run_dcfr(game: Game, checkpoints: &[u64], tolerance: f64) -> Result<(Solver, Run), String> {
    let n = game.node_count();
    let mut solver = Solver::new(game, vec![None; n])?;
    solver.set_algorithm(DCFR)?;
    let tick = Instant::now();
    let mut done = 0;
    let mut last = None;
    for &checkpoint in checkpoints {
        solver.advance(checkpoint - done)?;
        done = checkpoint;
        let average = solver.average();
        let quality = solver.quality(&average)?;
        let met = gains(&quality).iter().all(|g| *g <= tolerance);
        last = Some((average, quality, met));
        if met {
            break;
        }
    }
    let (average, quality, met) = last.unwrap();
    let seconds = tick.elapsed().as_secs_f64();
    Ok((
        solver,
        Run {
            average,
            quality,
            sweeps: done,
            seconds,
            met,
        },
    ))
}

/// Belief control on one root: the deployed solve under the projected product
/// law, a DCFR reference under the original active joint law it replaces, and
/// the deployed strategy's best-response gains in the joint game. The
/// reference qualifies only if both its gains reach `tolerance` within budget.
fn belief_control(
    root: &PublicRoot,
    pairs: &[[u8; 2]],
    likelihood: &[Vec<f64>; 3],
    menu: SearchMenu,
    checkpoints: &[u64],
    reference_checkpoints: &[u64],
    tolerance: f64,
    matched_accuracy: bool,
) -> Result<Value, String> {
    let (ranges, law, joint) = project_with_joint(pairs, likelihood, root.live, true)?;
    let hero = root.live.iter().position(|&s| s == root.seat).unwrap();
    let holding = pairs
        .iter()
        .position(|h| *h == root.hole)
        .ok_or("own hand outside range")?;
    if ranges[hero][holding].weight == 0. {
        return Err("own holding has zero modeled root reach".into());
    }
    let mut tree = Tree::new(&root.hand, root.live, menu, SUPPORTED_NODES);
    tree.compile(&mut root.hand.clone())?;
    let pot = root.hand.pot() as f64 / 100.;
    // Keep the historical control unchanged unless matched accuracy is
    // explicitly requested. The comparison then uses the reference tolerance
    // for both solves, not the looser deployment threshold.
    let target = if matched_accuracy {
        tolerance
    } else {
        (0.01 * pot).min(0.1)
    };
    let projected = Game::new(root.board, ranges.clone(), tree.nodes.clone(), pot)?;
    let (_, deployed) = run_dcfr(projected, checkpoints, target)?;
    let exact = Game::new(root.board, ranges, tree.nodes, pot)?.with_joint(joint.unwrap())?;
    let (mut reference_solver, reference) = run_dcfr(exact, reference_checkpoints, tolerance)?;
    let in_exact = reference_solver.quality(&deployed.average)?;
    let excess: Vec<f64> = gains(&in_exact)
        .iter()
        .zip(gains(&reference.quality))
        .map(|(d, r)| d - r)
        .collect();
    let solver_residual = gains(&deployed.quality);
    let reference_residual = gains(&reference.quality);
    let law_shift: Vec<_> = gains(&in_exact)
        .iter()
        .zip(&solver_residual)
        .map(|(a, b)| a - b)
        .collect();
    Ok(
        json!({"format":"nplayer-live-river-belief-control-v1","search_menu":menu.name(),"law":law,
        "matched_accuracy":matched_accuracy,
        "pot_bb":pot,"target_bb":target,"nodes":tree.menus.len(),
        "deployed":{"sweeps":deployed.sweeps,"seconds":deployed.seconds,"target_met":deployed.met,
            "projected_game_quality":deployed.quality,"exact_game_quality":in_exact},
        "reference":{"sweeps":reference.sweeps,"seconds":reference.seconds,"qualified":reference.met,
            "tolerance_bb":tolerance,"exact_game_quality":reference.quality},
        "excess_gain_bb":excess,"belief_tolerance_bb":0.05,
        "decomposition":{"solver_residual_bb":solver_residual,"same_profile_law_shift_bb":law_shift,
            "reference_residual_bb":reference_residual,"identity":"E = D + S - R"},
        "qualified":reference.met && (!matched_accuracy || deployed.met),
        "passes":reference.met && (!matched_accuracy || deployed.met) && excess.iter().all(|x| *x <= 0.05)}),
    )
}

/// Receives exactly one legal observation request. Table/tables are loaded once
/// by the worker. No root/profile cache is shared across different histories.
pub fn request(v: &Value, table: &PolicyTable, tables: &EquityTables) -> Result<Value, String> {
    request_impl(v, table, tables, None)
}
fn request_impl(
    v: &Value,
    table: &PolicyTable,
    tables: &EquityTables,
    capture: Option<&mut Option<retained::Captured>>,
) -> Result<Value, String> {
    let started = Instant::now();
    let root = reconstruct(v, table.config())?;
    if table.mode != crate::multi_policy::Mode::Average || table.scope != 3 {
        return Err("full-street average blueprint required".into());
    }
    let reconstruction = started.elapsed().as_secs_f64();
    let cards: Vec<_> = (0..52).filter(|c| !root.board.contains(c)).collect();
    let pairs: Vec<_> = (0..cards.len())
        .flat_map(|i| (i + 1..cards.len()).map(move |j| (i, j)))
        .map(|(i, j)| [cards[i], cards[j]])
        .collect();
    let menu = SearchMenu::parse(v.get("search_menu"))?;
    let backend = exact::Backend::parse(v.get("belief_backend"))?;
    if backend != exact::Backend::Projected
        && !matches!(
            v["mode"].as_str(),
            None | Some("solve") | Some("exact-qualification")
        )
    {
        return Err("exact backend is supported only for solve or exact-qualification".into());
    }
    if !root.prefix.is_empty()
        && (backend != exact::Backend::Projected || !matches!(v["mode"].as_str(), None | Some("solve")))
    {
        return Err("second-to-act roots support projected solve only".into());
    }
    match v.get("mode").map(|m| m.as_str()) {
        None | Some(Some("solve")) => (),
        Some(Some("classify")) => {
            let mut out = classify(&root, &pairs, menu, table, tables)?;
            out["timings"]["reconstruction_seconds"] = json!(reconstruction);
            out["timings"]["native_before_serialization_seconds"] =
                json!(started.elapsed().as_secs_f64());
            return Ok(out);
        }
        Some(Some("exact-qualification")) => {
            let (likelihood, _) =
                likelihoods(&root, &pairs, |obs| blueprint_row(obs, table, tables))?;
            return exact::qualify(&root, &pairs, &likelihood, menu);
        }
        Some(Some("belief-control")) => {
            let checkpoints = sweep_list(v.get("checkpoints"))?;
            let reference = sweep_list(v.get("reference_checkpoints"))?;
            let tolerance = v["reference_tolerance_bb"]
                .as_f64()
                .filter(|x| x.is_finite() && *x > 0.)
                .ok_or("reference_tolerance_bb must be positive")?;
            let matched_accuracy = match v.get("matched_accuracy") {
                None => false,
                Some(x) => x.as_bool().ok_or("matched_accuracy must be boolean")?,
            };
            let (likelihood, _) =
                likelihoods(&root, &pairs, |obs| blueprint_row(obs, table, tables))?;
            let mut out = belief_control(
                &root,
                &pairs,
                &likelihood,
                menu,
                &checkpoints,
                &reference,
                tolerance,
                matched_accuracy,
            )?;
            out["timings"] =
                json!({"native_before_serialization_seconds":started.elapsed().as_secs_f64()});
            return Ok(out);
        }
        Some(Some("diagnose")) => {
            let pot = root.hand.pot() as f64 / 100.;
            let checkpoints = sweep_list(v.get("checkpoints"))?;
            let target = quality_target(v.get("target"), pot)?;
            let (likelihood, _) =
                likelihoods(&root, &pairs, |obs| blueprint_row(obs, table, tables))?;
            let (ranges, law) = project(&pairs, &likelihood, root.live)?;
            let hero = root.live.iter().position(|&s| s == root.seat).unwrap();
            let holding = pairs
                .iter()
                .position(|h| *h == root.hole)
                .ok_or("own hand outside range")?;
            if ranges[hero][holding].weight == 0. {
                return Err("own holding has zero modeled root reach".into());
            }
            let mut tree = Tree::new(&root.hand, root.live, menu, SUPPORTED_NODES);
            tree.compile(&mut root.hand.clone())?;
            let nodes = tree.nodes.len();
            let game = Game::new(
                root.board,
                ranges.clone(),
                std::mem::take(&mut tree.nodes),
                pot,
            )?;
            let (solver, run) = run_dcfr(game, &checkpoints, target)?;
            let memory = solver.memory_bytes();
            let mut out = diagnose(&root, &pairs, ranges, &tree, &run.average, table, tables)?;
            out["search"] = json!({"menu":menu.name(),"nodes":nodes,"sweeps":run.sweeps,"converged":run.met,
                "target_bb":target,"quality":run.quality,"solve_seconds":run.seconds,"solver_memory_bytes":memory});
            out["law"] = law;
            out["timings"] =
                json!({"native_before_serialization_seconds":started.elapsed().as_secs_f64()});
            return Ok(out);
        }
        _ => return Err("mode must be solve, classify, belief-control or diagnose".into()),
    }
    let sweeps = fixed_sweeps(&v["sweeps"])?;
    let debug = match v.get("debug") {
        Some(x) => x.as_bool().ok_or("debug must be boolean")?,
        None => false,
    };
    if backend != exact::Backend::Projected && debug {
        return Err("exact debug prepared-game export is unsupported".into());
    }
    let tick = Instant::now();
    let (likelihood, coverage) =
        likelihoods(&root, &pairs, |obs| blueprint_row(obs, table, tables))?;
    let likelihood_seconds = tick.elapsed().as_secs_f64();
    let tick = Instant::now();
    let (mut ranges, mut law) = project(&pairs, &likelihood, root.live)?;
    let projection_seconds = tick.elapsed().as_secs_f64();
    let hero = root.live.iter().position(|&s| s == root.seat).unwrap();
    let holding = pairs
        .iter()
        .position(|h| *h == root.hole)
        .ok_or("own hand outside range")?;
    if ranges[hero][holding].weight == 0. {
        return Err("own holding has zero modeled root reach".into());
    }
    let tick = Instant::now();
    let omitted = match v.get("omitted") {
        Some(x) => x.as_bool().ok_or("omitted must be boolean")?,
        None => false,
    };
    if omitted && menu == SearchMenu::Full {
        return Err("omitted-raise evaluation needs a capped search menu".into());
    }
    if omitted && !root.prefix.is_empty() {
        return Err("omitted-raise evaluation supports first-to-act roots only".into());
    }
    if backend != exact::Backend::Projected && omitted {
        return Err("exact solves use retained-full-menu-audit outside decision timing".into());
    }
    let evaluation_ranges = omitted.then(|| ranges.clone());
    if backend != exact::Backend::Projected {
        ranges = exact::ranges(&pairs, &likelihood, root.live);
        law["law"] = json!(exact::EXACT_LAW);
        law["projection_applied"] = json!(false);
    }
    let mut tree = Tree::new(&root.hand, root.live, menu, SUPPORTED_NODES);
    tree.compile(&mut root.hand.clone())?;
    let nodes = tree.nodes.len();
    // Hero acting second: the opponent's first river action is fixed to the blueprint, so the
    // opponent's range after it follows the same blueprint likelihoods as every earlier street,
    // and the hero's row is read at the child for the action actually taken.
    let mut fixed = vec![None; nodes];
    let mut hero_node = 0;
    // Share of the opponent's modeled range that took the observed action (1 at first-to-act roots).
    let mut taken_share = 1.;
    if let Some(&taken) = root.prefix.first() {
        let opponent = root.hand.actor().ok_or("root actor missing")?;
        let Node::Decision { children, .. } = &tree.nodes[0] else {
            return Err("terminal river root".into());
        };
        let root_menu = &tree.menus[0];
        let taken_index = root_menu
            .iter()
            .position(|x| *x == taken)
            .ok_or("opponent river action outside the search root menu")?;
        let mut obs = root.hand.observe(opponent)?;
        let full = multi_holdem::menu(&obs);
        let mut row = Vec::with_capacity(pairs.len() * root_menu.len());
        for &pair in &pairs {
            obs.hole = pair;
            let (p, _) = blueprint_row(&obs, table, tables)?;
            for x in root_menu {
                let j = full
                    .iter()
                    .position(|(_, y)| y == x)
                    .ok_or("search root action outside the blueprint menu")?;
                row.push(p[j]);
            }
        }
        let k = root_menu.len();
        if row.chunks(k).any(|r| (r.iter().sum::<f64>() - 1.).abs() > 1e-10) {
            return Err("search root menu differs from the blueprint menu".into());
        }
        let o = root.live.iter().position(|&s| s == opponent).unwrap();
        let reach: f64 = (0..pairs.len()).map(|i| ranges[o][i].weight * row[i * k + taken_index]).sum();
        if reach <= 0. {
            return Err("observed opponent river action has zero modeled likelihood".into());
        }
        hero_node = children[taken_index];
        taken_share = reach / ranges[o].iter().map(|h| h.weight).sum::<f64>();
        fixed[0] = Some(row);
    }
    let game = Game::new(
        root.board,
        ranges,
        std::mem::take(&mut tree.nodes),
        root.hand.pot() as f64 / 100.,
    )?;
    let game = match backend {
        exact::Backend::Projected => game,
        exact::Backend::Prefix => exact::prefix(game, &pairs, &likelihood, root.live)?,
        exact::Backend::Dense => {
            let (_, _, joint) = project_with_joint(&pairs, &likelihood, root.live, true)?;
            game.with_joint(joint.unwrap())?
        }
    };
    let menus = &tree.menus;
    let mut solver = Solver::new(game, fixed)?;
    if hero_node != 0 {
        solver.set_taken(0)?;
    }
    solver.set_algorithm(match v.get("algorithm").map(|a| a.as_str()) {
        None | Some(Some("linear-cfr")) => Algorithm::Linear,
        Some(Some("dcfr-1.5-0-2")) => DCFR,
        _ => return Err("algorithm must be linear-cfr or dcfr-1.5-0-2".into()),
    })?;
    if v.get("profile") == Some(&json!(true)) {
        solver.profile_leaves();
    }
    // Quality is checked at each checkpoint; elapsed time includes the checks.
    let checkpoints: Vec<u64> = match v.get("checkpoints") {
        None => vec![sweeps],
        Some(c) => array(c)?.iter().map(uint).collect::<Result<_, _>>()?,
    };
    if checkpoints.is_empty()
        || checkpoints.windows(2).any(|w| w[0] >= w[1])
        || checkpoints[0] == 0
        || *checkpoints.last().unwrap() != sweeps
    {
        return Err("checkpoints must increase and end at sweeps".into());
    }
    let stop_at_target = v.get("stop_at_target") == Some(&json!(true));
    // The frozen quality gate: each player's gain within min(1% of the pot, 0.1 BB).
    // Gains are weighted by reaching each node; at a second-to-act root the hero's played
    // subtree is reached with `taken_share`, so the same per-decision target scales by it.
    let target = quality_target(v.get("target"), root.hand.pot() as f64 / 100.)? * taken_share;
    let preparation = tick.elapsed().as_secs_f64();
    let tick = Instant::now();
    let (mut done, mut quality_seconds, mut curve) = (0, 0., Vec::new());
    let (mut average, mut quality) = (Vec::new(), Value::Null);
    for &checkpoint in &checkpoints {
        solver.advance(checkpoint - done)?;
        done = checkpoint;
        let check = Instant::now();
        average = solver.average();
        quality = solver.quality(&average)?;
        quality_seconds += check.elapsed().as_secs_f64();
        let met = quality["best_response_gains_bb"]
            .as_array()
            .unwrap()
            .iter()
            .all(|g| g.as_f64().unwrap() <= target);
        curve.push(
            json!({"sweeps":checkpoint,"elapsed_seconds":tick.elapsed().as_secs_f64(),
            "best_response_gains_bb":quality["best_response_gains_bb"],"target_met":met}),
        );
        if met && stop_at_target {
            break;
        }
    }
    let solve = tick.elapsed().as_secs_f64() - quality_seconds;
    let k = menus[hero_node].len();
    let probabilities = &average[hero_node][holding * k..(holding + 1) * k];
    let actions: Vec<_> = menus[hero_node]
        .iter()
        .map(|a| json!([a.kind.name(), a.raise_to]))
        .collect();
    let deployed = match evaluation_ranges {
        Some(ranges) => {
            let tick = Instant::now();
            let mut value =
                deployed_quality(&root, &pairs, ranges, &tree, &average, table, tables)?;
            value["seconds"] = json!(tick.elapsed().as_secs_f64());
            value
        }
        None => Value::Null,
    };
    let mut out = json!({"format":"nplayer-live-river-result-v1","sweeps":done,"requested_sweeps":sweeps,
        "algorithm":solver.timing()["algorithm"],"target_bb":target,"solver_memory_bytes":solver.memory_bytes(),"checkpoints":curve,"solver_timing":solver.timing(),"search_menu":menu.name(),"omitted_raise_evaluation":deployed,"actions":actions,"probabilities":probabilities,"live":root.live,"nodes":nodes,"holdings":pairs.len(),"law":law,"coverage":coverage.map(|c|c.json()),"quality":quality,"timings":{"reconstruction_seconds":reconstruction,"likelihood_seconds":likelihood_seconds,"projection_seconds":projection_seconds,"tree_and_solver_preparation_seconds":preparation,"solve_seconds":solve,"quality_seconds":quality_seconds,"native_before_serialization_seconds":started.elapsed().as_secs_f64()}});
    if backend != exact::Backend::Projected {
        out["chance"] = solver.game.chance_stats();
    }
    if debug {
        out["average"] = json!(average);
        out["prepared_game"] = json!({"board":root.board,"root_pot_bb":root.hand.pot() as f64/100.,"ranges":std::array::from_fn::<_,2,_>(|s|solver.game.hands[s].iter().map(|h|json!([h.cards[0],h.cards[1],h.weight])).collect::<Vec<_>>()),"nodes":solver.game.nodes.iter().map(|n|match n{Node::Leaf(t)=>json!({"terminal":[t.base,t.win0,t.tie0]}),Node::Decision{actor,children}=>json!({"actor":actor,"children":children})}).collect::<Vec<_>>()});
    }
    out["timings"]["native_before_serialization_seconds"] = json!(started.elapsed().as_secs_f64());
    if let Some(slot) = capture {
        tree.nodes = solver.game.nodes.clone();
        *slot = Some(retained::Captured::new(
            root,
            tree,
            pairs,
            average,
            v.clone(),
            &out,
        )?);
    }
    Ok(out)
}

mod retained;
pub use retained::SessionStore;
pub mod whole_hand;

#[cfg(test)]
mod tests;
