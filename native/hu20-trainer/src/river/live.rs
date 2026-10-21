//! Opt-in legal public-history adapter. No deck or other private hand input.
use super::{Game, Holding, Node, Solver, Terminal};
use crate::{
    cards::EquityTables,
    game::{Kind, Street},
    multi_holdem,
    multi_policy::PolicyTable,
    nplayer::{Action, Config, Event, Hand, Observation},
};
use serde_json::{json, Value};
use std::time::Instant;

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
    hand: Hand,
    prior: Vec<(Hand, Action)>,
    board: [u8; 5],
    seat: usize,
    hole: [u8; 2],
    live: [usize; 2],
}
fn reconstruct(v: &Value, config: Config) -> Result<PublicRoot, String> {
    fields(
        v,
        &[
            "format", "button", "board", "seat", "hole", "actions", "players", "legal", "sweeps",
            "debug",
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
        if uint(&a[0])? as usize != actor
            || uint(&a[1])? != hand.street() as u64
            || hand.street() == Street::River
        {
            return Err("history must end at the first river decision".into());
        }
        let action = Action {
            kind: kind(&a[2])?,
            raise_to: uint(&a[3])?,
        };
        let obs = hand.observe(actor)?;
        if !multi_holdem::menu(&obs).iter().any(|(_, x)| *x == action) {
            return Err("public action outside blueprint menu".into());
        }
        prior.push((hand.clone(), action));
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
    let live: Vec<_> = hand
        .players()
        .iter()
        .enumerate()
        .filter_map(|(s, p)| (!p.folded).then_some(s))
        .collect();
    if live.len() != 2
        || !live.contains(&seat)
        || live.iter().any(|&s| hand.players()[s].stack == 0)
        || hand.players()[live[0]].contributed != hand.players()[live[1]].contributed
        || hand
            .players()
            .iter()
            .any(|p| p.contributed > hand.players()[live[0]].contributed)
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
        hand,
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
    for (i, &a) in pairs.iter().enumerate() {
        for (j, &b) in pairs.iter().enumerate() {
            if disjoint(a, b) {
                let p = weights[live[0]][i] * weights[live[1]][j] * removal.compatible(a, b) / z;
                let q = marginal[0][i] * marginal[1][j] / projected_z;
                tv += (p - q).abs() / 2.;
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
    ))
}

struct Tree {
    nodes: Vec<Node>,
    menus: Vec<Vec<Action>>,
    live: [usize; 2],
    stacks: [u64; 2],
    pot: u64,
    bb: f64,
}
impl Tree {
    fn compile(&mut self, hand: &mut Hand) -> Result<usize, String> {
        if self.nodes.len() >= 4096 {
            return Err(
                "unsupported full production tree exceeds 4096 nodes; no menu truncation".into(),
            );
        }
        let id = self.nodes.len();
        self.nodes.push(Node::Leaf(Terminal {
            base: 0.,
            win0: 0.,
            tie0: 0.,
        }));
        self.menus.push(Vec::new());
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
            let menu = multi_holdem::menu(&hand.observe(actor)?);
            let mut children = Vec::new();
            for (_, action) in &menu {
                let saved = hand.save();
                hand.apply_mut(*action)?;
                let child = self.compile(hand);
                hand.restore(saved);
                children.push(child?);
            }
            self.menus[id] = menu.into_iter().map(|(_, a)| a).collect();
            self.nodes[id] = Node::Decision {
                actor: seat,
                children,
            };
        }
        Ok(id)
    }
}

/// Receives exactly one legal observation request. Table/tables are loaded once
/// by the worker. No root/profile cache is shared across different histories.
pub fn request(v: &Value, table: &PolicyTable, tables: &EquityTables) -> Result<Value, String> {
    let started = Instant::now();
    let root = reconstruct(v, table.config())?;
    if table.mode != crate::multi_policy::Mode::Average || table.scope != 3 {
        return Err("full-street average blueprint required".into());
    }
    let reconstruction = started.elapsed().as_secs_f64();
    let sweeps = uint(&v["sweeps"])?;
    if !(1..=1024).contains(&sweeps) {
        return Err("pilot supports fixed 1..1024 sweeps".into());
    }
    let debug = match v.get("debug") {
        Some(x) => x.as_bool().ok_or("debug must be boolean")?,
        None => false,
    };
    let cards: Vec<_> = (0..52).filter(|c| !root.board.contains(c)).collect();
    let pairs: Vec<_> = (0..cards.len())
        .flat_map(|i| (i + 1..cards.len()).map(move |j| (i, j)))
        .map(|(i, j)| [cards[i], cards[j]])
        .collect();
    let tick = Instant::now();
    let (likelihood, coverage) = likelihoods(&root, &pairs, |obs| {
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
    })?;
    let likelihood_seconds = tick.elapsed().as_secs_f64();
    let tick = Instant::now();
    let (ranges, law) = project(&pairs, &likelihood, root.live)?;
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
    let mut tree = Tree {
        nodes: Vec::new(),
        menus: Vec::new(),
        live: root.live,
        stacks: root.live.map(|s| root.hand.players()[s].stack),
        pot: root.hand.pot(),
        bb: 100.,
    };
    tree.compile(&mut root.hand.clone())?;
    let menus = tree.menus;
    let nodes = tree.nodes.len();
    let game = Game::new(
        root.board,
        ranges,
        tree.nodes,
        root.hand.pot() as f64 / 100.,
    )?;
    let mut solver = Solver::new(game, vec![None; nodes])?;
    let preparation = tick.elapsed().as_secs_f64();
    let tick = Instant::now();
    solver.advance(sweeps)?;
    let solve = tick.elapsed().as_secs_f64();
    let tick = Instant::now();
    let average = solver.average();
    let quality = solver.quality(&average)?;
    let quality_seconds = tick.elapsed().as_secs_f64();
    let k = menus[0].len();
    let probabilities = &average[0][holding * k..(holding + 1) * k];
    let actions: Vec<_> = menus[0]
        .iter()
        .map(|a| json!([a.kind.name(), a.raise_to]))
        .collect();
    let mut out = json!({"format":"nplayer-live-river-result-v1","sweeps":sweeps,"actions":actions,"probabilities":probabilities,"live":root.live,"nodes":nodes,"holdings":pairs.len(),"law":law,"coverage":coverage.map(|c|c.json()),"quality":quality,"timings":{"reconstruction_seconds":reconstruction,"likelihood_seconds":likelihood_seconds,"projection_seconds":projection_seconds,"tree_and_solver_preparation_seconds":preparation,"solve_seconds":solve,"quality_seconds":quality_seconds,"native_before_serialization_seconds":started.elapsed().as_secs_f64()}});
    if debug {
        out["average"] = json!(average);
        out["prepared_game"] = json!({"board":root.board,"root_pot_bb":root.hand.pot() as f64/100.,"ranges":std::array::from_fn::<_,2,_>(|s|solver.game.hands[s].iter().map(|h|json!([h.cards[0],h.cards[1],h.weight])).collect::<Vec<_>>()),"nodes":solver.game.nodes.iter().map(|n|match n{Node::Leaf(t)=>json!({"terminal":[t.base,t.win0,t.tie0]}),Node::Decision{actor,children}=>json!({"actor":actor,"children":children})}).collect::<Vec<_>>()});
    }
    out["timings"]["native_before_serialization_seconds"] = json!(started.elapsed().as_secs_f64());
    Ok(out)
}

#[cfg(test)]
mod tests;
