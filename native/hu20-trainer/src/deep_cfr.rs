//! Deep CFR traversals over the menu abstraction (docs/neural-deep-cfr.md).
//!
//! One traversal deals a root (a player count from the run's list, wide-grid stacks, a shuffled
//! deck, a button and a traverser), then walks the hand by external sampling:
//! - at the traverser's decisions every menu action is explored, and the sampled regrets
//!   `v(a) − v` become one advantage sample;
//! - at other seats' decisions one action is drawn from the current strategy, which becomes one
//!   strategy sample.
//!
//! The current strategy is regret matching on the advantage network's outputs at the acting seat's
//! `policy_features` (quantized, as the networks train on them). Samples carry the iteration, which
//! is their linear-CFR weight. Everything is a function of (seed, iteration, traversal index).
use crate::cards::EquityTables;
use crate::multi_arena::stream_seed;
use crate::multi_holdem::menu;
use crate::multi_stacks::{live_draw, DepthGrid};
use crate::nplayer::{Action, Hand, Saved};
use crate::policy_features::{self as features, ACTIONS};
use crate::policy_network::Fast;
use rand::{seq::SliceRandom, Rng, SeedableRng};

pub const MAGIC: &[u8; 8] = b"NPDCF001";
pub const FORMAT: &str = "nplayer-deep-cfr-samples-v1";
pub const ADVANTAGE: u8 = 0;
pub const STRATEGY: u8 = 1;
/// A traversal that runs past this many nodes is an error, not a silent truncation.
pub const NODE_LIMIT: u64 = 50_000_000;

/// kind u8, players u8, street u8, legal mask u8, iteration u32, six f32 targets, features u8.
pub fn record_bytes() -> usize {
    8 + 4 * ACTIONS + features::len()
}
pub fn record_layout() -> serde_json::Value {
    serde_json::json!(["kind u8 (0 advantage: sampled regrets; 1 strategy: current strategy)", "players u8", "street u8",
        "legal_mask u8", "iteration u32 (linear weight)", "targets 6 f32 by menu label", "features u8 (x/255)"])
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Counts {
    pub traversals: u64,
    pub nodes: u64,
    pub terminals: u64,
    pub advantage: u64,
    pub strategy: u64,
    /// Traverser decisions past the exploration bound, where one action was sampled instead.
    pub sampled: u64,
    /// Advantage samples and sampled traverser decisions by street (preflop..river).
    pub advantage_by_street: [u64; 4],
    pub sampled_by_street: [u64; 4],
    /// Nodes of the largest single traversal.
    pub max_nodes: u64,
}
impl Counts {
    pub fn add(&mut self, o: &Counts) {
        self.traversals += o.traversals;
        self.nodes += o.nodes;
        self.terminals += o.terminals;
        self.advantage += o.advantage;
        self.strategy += o.strategy;
        self.sampled += o.sampled;
        for k in 0..4 {
            self.advantage_by_street[k] += o.advantage_by_street[k];
            self.sampled_by_street[k] += o.sampled_by_street[k];
        }
        self.max_nodes = self.max_nodes.max(o.max_nodes);
    }
}

/// Where the traverser stops exploring every action: past `per_street` explored decisions in the
/// current betting round, or `total` on the whole path, it samples one action from the current
/// strategy instead. The per-street limit targets long raising sequences within a round without
/// starving later streets; the total bounds a traversal at 6^total explored paths.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Bound {
    pub per_street: u32,
    pub total: u32,
}
impl Bound {
    pub const NONE: Bound = Bound { per_street: u32::MAX, total: u32::MAX };
}

/// The traverser's explored decisions on the current path.
#[derive(Clone, Copy)]
struct Explored {
    total: u32,
    street: usize,
    in_street: u32,
}

/// A traversal root: the dealt hand, the traverser and the traversal's own random stream.
pub fn root(seed: u64, iteration: u64, index: u64, players: &[usize]) -> Result<(Hand, usize, rand::rngs::StdRng), String> {
    if players.is_empty() || players.iter().any(|n| !(2..=6).contains(n)) {
        return Err("player counts are 2..=6".into());
    }
    let mut rng = rand::rngs::StdRng::seed_from_u64(stream_seed(seed, b"deep-cfr", iteration, index));
    let n = players[rng.gen_range(0..players.len())];
    let config = live_draw(n, DepthGrid::Wide, &mut rng, |_| {});
    let mut deck: Vec<u8> = (0..52).collect();
    deck.shuffle(&mut rng);
    let button = rng.gen_range(0..n);
    let traverser = rng.gen_range(0..n);
    Ok((Hand::from_deck(config, button, &deck)?, traverser, rng))
}

/// What one traversal needs besides its own state: the current strategy's network, the card
/// tables, the iteration (the samples' linear weight) and the exploration bound.
#[derive(Clone, Copy)]
pub struct Context<'a> {
    pub net: &'a Fast,
    pub tables: &'a EquityTables,
    pub iteration: u32,
    pub bound: Bound,
}

/// A decision waiting for the network: the acting seat's quantized features and what the walk
/// does with the strategy once it has it.
struct Decision {
    actor: usize,
    choices: Vec<(u8, Action)>,
    legal: u8,
    street: usize,
    bytes: Vec<u8>,
}

/// A decision the walk is below. `Follow` played one action; `Explore` plays each menu action in
/// turn, collecting their values for the regrets.
enum Frame {
    Follow(Saved),
    Explore { saved: Option<Saved>, choices: Vec<(u8, Action)>, next: usize, values: [f64; ACTIONS], sigma: [f64; ACTIONS],
              legal: u8, street: usize, bytes: Vec<u8>, below: Explored },
}

/// One traversal as an explicit stack instead of recursion, so a thread can hold many and give
/// their network calls to one batched forward pass. The walk is the depth-first external-sampling
/// traversal: the same nodes in the same order, the same random draws and the same records.
pub struct Walk {
    hand: Hand,
    traverser: usize,
    rng: rand::rngs::StdRng,
    frames: Vec<Frame>,
    /// The current node's explored decisions; meaningful while entering or waiting at a node.
    explored: Explored,
    waiting: Option<Decision>,
    pub out: Vec<u8>,
    pub counts: Counts,
}

/// Where a walk stopped: at a decision that needs the network, or at its root's value.
pub enum Step {
    Network,
    Done(f64),
}

impl Walk {
    /// Traversal `index` of the context's iteration.
    pub fn new(seed: u64, iteration: u32, index: u64, players: &[usize]) -> Result<Self, String> {
        let (hand, traverser, rng) = root(seed, iteration as u64, index, players)?;
        Ok(Self::from(hand, traverser, rng))
    }
    fn from(hand: Hand, traverser: usize, rng: rand::rngs::StdRng) -> Self {
        let counts = Counts { traversals: 1, ..Counts::default() };
        Self { hand, traverser, rng, frames: Vec::new(), explored: Explored { total: 0, street: 0, in_street: 0 }, waiting: None,
               out: Vec::new(), counts }
    }
    /// The waiting decision's quantized features.
    pub fn features(&self) -> &[u8] {
        &self.waiting.as_ref().expect("the walk is not waiting for the network").bytes
    }
    /// Starts the walk: runs to its first network call (or its end, if the hand is already over).
    pub fn start(&mut self, ctx: &Context<'_>) -> Result<Step, String> {
        self.descend(ctx)
    }
    /// Gives the waiting decision the network's outputs and runs to the next call or the end.
    pub fn resume(&mut self, ctx: &Context<'_>, logits: [f32; ACTIONS]) -> Result<Step, String> {
        let d = self.waiting.take().expect("the walk is not waiting for the network");
        let sigma = ctx.net.strategy_of(logits, d.legal);
        let players = self.hand.config().players();
        if d.actor != self.traverser {
            self.record(ctx, STRATEGY, players, d.street, d.legal, &sigma, &d.bytes);
            self.counts.strategy += 1;
            return self.follow(ctx, &d.choices, &sigma);
        }
        let in_street = if self.explored.street == d.street { self.explored.in_street } else { 0 };
        if in_street >= ctx.bound.per_street || self.explored.total >= ctx.bound.total {
            self.counts.sampled += 1;
            self.counts.sampled_by_street[d.street.min(3)] += 1;
            return self.follow(ctx, &d.choices, &sigma);
        }
        let below = Explored { total: self.explored.total + 1, street: d.street, in_street: in_street + 1 };
        self.frames.push(Frame::Explore { saved: None, choices: d.choices, next: 0, values: [0.; ACTIONS], sigma, legal: d.legal,
                                          street: d.street, bytes: d.bytes, below });
        self.enter_next()?;
        self.descend(ctx)
    }
    fn record(&mut self, ctx: &Context<'_>, kind: u8, players: usize, street: usize, legal: u8, targets: &[f64; ACTIONS], bytes: &[u8]) {
        self.out.extend_from_slice(&[kind, players as u8, street as u8, legal]);
        self.out.extend_from_slice(&ctx.iteration.to_le_bytes());
        for t in targets {
            self.out.extend_from_slice(&(*t as f32).to_le_bytes());
        }
        self.out.extend_from_slice(bytes);
    }
    /// Plays one action drawn from `sigma` and enters the node below it.
    fn follow(&mut self, ctx: &Context<'_>, choices: &[(u8, Action)], sigma: &[f64; ACTIONS]) -> Result<Step, String> {
        let draw: f64 = self.rng.gen();
        let mut sum = 0.;
        let mut pick = None;
        for (i, (label, _)) in choices.iter().enumerate() {
            let p = sigma[*label as usize];
            if p > 0. {
                pick = Some(i);
                sum += p;
                if draw < sum {
                    break;
                }
            }
        }
        let action = choices[pick.ok_or("empty strategy")?].1;
        let saved = self.hand.save();
        self.hand.apply_mut(action)?;
        self.frames.push(Frame::Follow(saved));
        self.descend(ctx)
    }
    /// Applies the top `Explore` frame's next action; the walk then enters the node below it.
    fn enter_next(&mut self) -> Result<(), String> {
        let Some(Frame::Explore { saved, choices, next, below, .. }) = self.frames.last_mut() else { unreachable!() };
        *saved = Some(self.hand.save());
        self.hand.apply_mut(choices[*next].1)?;
        self.explored = *below;
        Ok(())
    }
    /// Enters nodes until one needs the network; terminal values travel up through the frames.
    fn descend(&mut self, ctx: &Context<'_>) -> Result<Step, String> {
        loop {
            self.counts.nodes += 1;
            if self.counts.nodes > NODE_LIMIT {
                return Err("traversal node limit".into());
            }
            let Some(actor) = self.hand.actor() else {
                self.counts.terminals += 1;
                let s = self.hand.settlement().ok_or("finished hand without settlement")?;
                let value = s.rewards[self.traverser] as f64 / self.hand.config().big_blind() as f64;
                match self.ascend(ctx, value)? {
                    Some(root) => return Ok(Step::Done(root)),
                    None => continue,
                }
            };
            let view = self.hand.observe(actor)?;
            let choices = menu(&view);
            let legal = features::legal_mask(&view);
            let bytes = features::quantize(&features::encode(&view, Some(ctx.tables))?);
            let street = view.street as usize;
            self.waiting = Some(Decision { actor, choices, legal, street, bytes });
            return Ok(Step::Network);
        }
    }
    /// Carries `value` up the frames. Returns the root's value when the walk is over, or `None`
    /// when an `Explore` frame entered its next action and the walk should keep descending.
    fn ascend(&mut self, ctx: &Context<'_>, mut value: f64) -> Result<Option<f64>, String> {
        loop {
            match self.frames.pop() {
                None => {
                    self.counts.max_nodes = self.counts.nodes;
                    return Ok(Some(value));
                }
                Some(Frame::Follow(saved)) => self.hand.restore(saved),
                Some(Frame::Explore { saved, choices, next, mut values, sigma, legal, street, bytes, below }) => {
                    self.hand.restore(saved.expect("an explored action was entered"));
                    values[choices[next].0 as usize] = value;
                    if next + 1 < choices.len() {
                        self.frames.push(Frame::Explore { saved: None, choices, next: next + 1, values, sigma, legal, street, bytes, below });
                        self.enter_next()?;
                        return Ok(None);
                    }
                    value = choices.iter().map(|(l, _)| sigma[*l as usize] * values[*l as usize]).sum();
                    let mut regrets = [0.; ACTIONS];
                    for (label, _) in &choices {
                        regrets[*label as usize] = values[*label as usize] - value;
                    }
                    let players = self.hand.config().players();
                    self.record(ctx, ADVANTAGE, players, street, legal, &regrets, &bytes);
                    self.counts.advantage += 1;
                    self.counts.advantage_by_street[street.min(3)] += 1;
                }
            }
        }
    }
    /// Runs the walk to its end, one forward pass per decision.
    fn finish(&mut self, ctx: &Context<'_>, scratch: &mut crate::policy_network::Scratch) -> Result<f64, String> {
        let mut step = self.start(ctx)?;
        loop {
            match step {
                Step::Done(v) => return Ok(v),
                Step::Network => {
                    let logits = ctx.net.logits(self.features(), scratch);
                    step = self.resume(ctx, logits)?;
                }
            }
        }
    }
}

/// Runs traversals `indices` of the context's iteration, stepping up to `width` walks at once so
/// that their network calls share batched forward passes. Each traversal's records, counts and
/// value are exactly what it gives alone, in index order: the walks are independent, each with
/// its own random stream, and a batched forward pass equals separate ones bit for bit.
pub fn run_batched(ctx: &Context<'_>, seed: u64, players: &[usize], indices: std::ops::Range<u64>, width: usize)
                   -> Result<Vec<(Vec<u8>, Counts, f64)>, String> {
    let width = width.max(1);
    let first = indices.start;
    let mut results: Vec<Option<(Vec<u8>, Counts, f64)>> = (first..indices.end).map(|_| None).collect();
    let mut queue = indices;
    let mut active: Vec<(u64, Walk)> = Vec::with_capacity(width);
    let mut scratch = Default::default();
    let mut logits = Vec::with_capacity(width);
    // Fills free slots from the queue; walks that end without a network call finish at once.
    let mut refill = |active: &mut Vec<(u64, Walk)>, results: &mut Vec<Option<(Vec<u8>, Counts, f64)>>| -> Result<(), String> {
        while active.len() < width {
            let Some(i) = queue.next() else { break };
            let mut walk = Walk::new(seed, ctx.iteration, i, players)?;
            match walk.start(ctx)? {
                Step::Network => active.push((i, walk)),
                Step::Done(v) => results[(i - first) as usize] = Some((walk.out, walk.counts, v)),
            }
        }
        Ok(())
    };
    refill(&mut active, &mut results)?;
    while !active.is_empty() {
        {
            let inputs: Vec<&[u8]> = active.iter().map(|(_, w)| w.features()).collect();
            if inputs.len() == 1 {
                logits.clear();
                logits.push(ctx.net.logits(inputs[0], &mut scratch));
            } else {
                ctx.net.logits_batch(&inputs, &mut scratch, &mut logits);
            }
        }
        let mut done = Vec::new();
        for (k, z) in logits.drain(..).enumerate() {
            if let Step::Done(v) = active[k].1.resume(ctx, z)? {
                done.push((k, v));
            }
        }
        // Highest slot first, so each swap_remove moves a walk that is still running.
        for (k, v) in done.into_iter().rev() {
            let (i, walk) = active.swap_remove(k);
            results[(i - first) as usize] = Some((walk.out, walk.counts, v));
        }
        refill(&mut active, &mut results)?;
    }
    Ok(results.into_iter().map(|r| r.expect("every traversal ran")).collect())
}

/// Traversals one at a time, accumulating their records and counts.
pub struct Traversal<'a> {
    pub ctx: Context<'a>,
    pub out: Vec<u8>,
    pub counts: Counts,
    scratch: crate::policy_network::Scratch,
}
impl<'a> Traversal<'a> {
    pub fn new(net: &'a Fast, tables: &'a EquityTables, iteration: u32) -> Self {
        Self::bounded(net, tables, iteration, Bound::NONE)
    }
    /// A traversal whose traverser stops exploring at `bound`.
    ///
    /// Past the bound the traverser's action is drawn from the current strategy, so the value
    /// returned upward is still an unbiased estimate of the node's value under the current profile;
    /// those decisions write no advantage sample. Unbounded exploration grows sixfold with each
    /// traverser decision, which long raising sequences at deep stacks turn into tens of millions
    /// of nodes.
    pub fn bounded(net: &'a Fast, tables: &'a EquityTables, iteration: u32, bound: Bound) -> Self {
        Self { ctx: Context { net, tables, iteration, bound }, out: Vec::new(), counts: Counts::default(), scratch: Default::default() }
    }
    /// Runs traversal `index` of `iteration`; returns the traverser's value in big blinds.
    pub fn run(&mut self, seed: u64, index: u64, players: &[usize]) -> Result<f64, String> {
        let mut walk = Walk::new(seed, self.ctx.iteration, index, players)?;
        let value = walk.finish(&self.ctx, &mut self.scratch);
        self.out.append(&mut walk.out);
        self.counts.add(&walk.counts);
        value
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::policy_network::PolicyNetwork;

    fn tables() -> Option<&'static EquityTables> {
        let dir = std::env::var("HU20_K50_TABLES").ok()?;
        Some(EquityTables::load(std::path::Path::new(&dir), false).unwrap())
    }

    /// A one-layer advantage network whose regrets are its biases.
    fn constant(biases: [f32; ACTIONS]) -> PolicyNetwork {
        let n = features::len();
        let header = serde_json::to_vec(&serde_json::json!({"format":crate::policy_network::FORMAT,"layout_sha256":features::layout_sha256(),
            "features":n,"layers":[{"in":n,"out":ACTIONS}],"activation":"relu","output":"advantage-6"})).unwrap();
        let mut f = crate::policy_network::MAGIC.to_vec();
        f.extend_from_slice(&(header.len() as u64).to_le_bytes());
        f.extend_from_slice(&header);
        for _ in 0..n * ACTIONS {
            f.extend_from_slice(&0f32.to_le_bytes());
        }
        for b in biases {
            f.extend_from_slice(&b.to_le_bytes());
        }
        PolicyNetwork::parse(&f).unwrap()
    }

    #[test]
    fn roots_are_a_function_of_seed_iteration_and_index() {
        let (a, ta, _) = root(5, 3, 7, &[3, 4, 5, 6]).unwrap();
        let (b, tb, _) = root(5, 3, 7, &[3, 4, 5, 6]).unwrap();
        assert_eq!((a.config().stacks(), a.button(), ta), (b.config().stacks(), b.button(), tb));
        let counts: std::collections::BTreeSet<usize> = (0..200).map(|i| root(5, 3, i, &[3, 6]).unwrap().0.config().players()).collect();
        assert_eq!(counts.into_iter().collect::<Vec<_>>(), vec![3, 6]);
        assert!(root(5, 3, 7, &[7]).is_err() && root(5, 3, 7, &[]).is_err());
    }

    #[test]
    fn traversals_are_deterministic_and_regrets_are_centred() {
        let Some(t) = tables() else { return };
        // Regrets favor calling and the pot raise: a mixed current strategy everywhere they're legal.
        let net = constant([0.1, 0.2, 1.0, -1.0, 0.5, -0.3]);
        let fast = net.fast();
        let mut a = Traversal::new(&fast, t, 4);
        let mut b = Traversal::new(&fast, t, 4);
        for i in 0..20 {
            assert_eq!(a.run(11, i, &[3, 6]).unwrap(), b.run(11, i, &[3, 6]).unwrap());
        }
        assert_eq!(a.out, b.out);
        assert_eq!(a.counts, b.counts);
        assert_eq!(a.out.len() as u64, (a.counts.advantage + a.counts.strategy) * record_bytes() as u64);
        assert!(a.counts.advantage > 0 && a.counts.strategy > 0);
        let r = record_bytes();
        for rec in a.out.chunks_exact(r) {
            assert_eq!(u32::from_le_bytes(rec[4..8].try_into().unwrap()), 4);
            let legal = rec[3];
            let targets: Vec<f64> = (0..ACTIONS).map(|k| f32::from_le_bytes(rec[8 + 4 * k..12 + 4 * k].try_into().unwrap()) as f64).collect();
            let mut regrets = [0.; ACTIONS];
            for k in 0..ACTIONS {
                regrets[k] = [0.1, 0.2, 1.0, -1.0, 0.5, -0.3][k];
            }
            let sigma = crate::policy_network::regret_match(&regrets, legal);
            for k in 0..ACTIONS {
                if legal >> k & 1 == 0 {
                    assert_eq!(targets[k], 0., "illegal labels carry no target");
                }
            }
            if rec[0] == STRATEGY {
                for k in 0..ACTIONS {
                    assert!((targets[k] - sigma[k]).abs() < 1e-6);
                }
            } else {
                // The strategy-weighted regret is zero: v = sum of sigma(a) v(a).
                let centred: f64 = (0..ACTIONS).map(|k| sigma[k] * targets[k]).sum();
                assert!(centred.abs() < 1e-3, "{centred}");
            }
        }
    }

    fn bound(per_street: u32, total: u32) -> Bound {
        Bound { per_street, total }
    }

    #[test]
    fn exploration_bounds_limit_the_tree_and_only_drop_bounded_advantage_samples() {
        let Some(t) = tables() else { return };
        // Positive regrets on every label: a uniform current strategy.
        let net = constant([1.; ACTIONS]);
        let fast = net.fast();
        let run = |b: Option<Bound>| {
            let mut x = match b { Some(b) => Traversal::bounded(&fast, t, 1, b), None => Traversal::new(&fast, t, 1) };
            for i in 0..30 {
                x.run(9, i, &[3, 6]).unwrap();
            }
            x
        };
        let (free, none) = (run(None), run(Some(Bound::NONE)));
        // No bound is the original traversal, byte for byte.
        assert_eq!(free.out, none.out);
        assert_eq!((free.counts, free.counts.sampled), (none.counts, 0));
        assert!(free.counts.max_nodes > 0 && free.counts.max_nodes <= free.counts.nodes);
        assert_eq!(free.counts.advantage_by_street.iter().sum::<u64>(), free.counts.advantage);
        // A zero bound samples everywhere: no advantage samples.
        let zero = run(Some(bound(0, u32::MAX)));
        assert_eq!(zero.counts.advantage, 0);
        assert!(zero.counts.sampled > 0 && zero.counts.strategy > 0);
        // One explored decision per street still writes samples after preflop.
        let street = run(Some(bound(1, u32::MAX)));
        assert!(street.counts.advantage_by_street[1..].iter().sum::<u64>() > 0);
        assert!(street.counts.nodes < free.counts.nodes && street.counts.sampled > 0);
        assert_eq!(street.counts.sampled_by_street.iter().sum::<u64>(), street.counts.sampled);
        // A total of two explored decisions bounds the whole path.
        let total = run(Some(bound(u32::MAX, 2)));
        assert!(zero.counts.nodes < total.counts.nodes && total.counts.nodes < free.counts.nodes);
        // Bounded traversals stay deterministic.
        assert_eq!(run(Some(bound(1, 3))).out, run(Some(bound(1, 3))).out);
    }

    /// The traverser's root value under the current profile is the same whether it explores or
    /// samples below the bound: averaged over many sampled continuations of one fixed root, the two
    /// estimates agree within sampling error.
    fn unbiased(players: usize, b: Bound) {
        let Some(t) = tables() else { return };
        let net = constant([0.1, 0.2, 1.0, -1.0, 0.5, -0.3]);
        let fast = net.fast();
        let n = 4000;
        let (mut full, mut cut) = (Vec::with_capacity(n), Vec::with_capacity(n));
        let mut scratch = Default::default();
        let walk = |ctx: Context<'_>, stream: u64, scratch: &mut crate::policy_network::Scratch| {
            let (hand, traverser, _) = root(17, 2, 3, &[players]).unwrap();
            Walk::from(hand, traverser, rand::rngs::StdRng::seed_from_u64(stream)).finish(&ctx, scratch).unwrap()
        };
        for k in 0..n as u64 {
            full.push(walk(Context { net: &fast, tables: t, iteration: 2, bound: Bound::NONE }, 1_000_000 + k, &mut scratch));
            cut.push(walk(Context { net: &fast, tables: t, iteration: 2, bound: b }, 2_000_000 + k, &mut scratch));
        }
        let stats = |v: &[f64]| {
            let m = v.iter().sum::<f64>() / v.len() as f64;
            (m, v.iter().map(|x| (x - m).powi(2)).sum::<f64>() / (v.len() - 1) as f64 / v.len() as f64)
        };
        let ((full, va), (cut, vb)) = (stats(&full), stats(&cut));
        let se = (va + vb).sqrt();
        assert!(se > 0. && (full - cut).abs() < 4. * se, "explored {full} sampled {cut} se {se}");
    }

    #[test]
    fn sampling_past_the_bound_keeps_the_root_value_unbiased() {
        unbiased(3, bound(u32::MAX, 1));
        unbiased(6, bound(u32::MAX, 2));
        unbiased(6, bound(1, 3));
    }

    /// The recursive traversal the walk replaced (PR477's), kept as the parity oracle.
    mod reference {
        use super::super::*;
        pub struct Recursive<'a> {
            pub ctx: Context<'a>,
            pub out: Vec<u8>,
            pub counts: Counts,
            scratch: crate::policy_network::Scratch,
        }
        impl<'a> Recursive<'a> {
            pub fn new(ctx: Context<'a>) -> Self {
                Self { ctx, out: Vec::new(), counts: Counts::default(), scratch: Default::default() }
            }
            pub fn run(&mut self, seed: u64, index: u64, players: &[usize]) -> Result<f64, String> {
                let (mut hand, traverser, mut rng) = root(seed, self.ctx.iteration as u64, index, players)?;
                self.counts.traversals += 1;
                let before = self.counts.nodes;
                let value = self.visit(&mut hand, traverser, Explored { total: 0, street: 0, in_street: 0 }, &mut rng);
                self.counts.max_nodes = self.counts.max_nodes.max(self.counts.nodes - before);
                value
            }
            fn record(&mut self, kind: u8, players: usize, street: usize, legal: u8, targets: &[f64; ACTIONS], bytes: &[u8]) {
                self.out.extend_from_slice(&[kind, players as u8, street as u8, legal]);
                self.out.extend_from_slice(&self.ctx.iteration.to_le_bytes());
                for t in targets {
                    self.out.extend_from_slice(&(*t as f32).to_le_bytes());
                }
                self.out.extend_from_slice(bytes);
            }
            fn visit(&mut self, hand: &mut Hand, traverser: usize, explored: Explored, rng: &mut rand::rngs::StdRng) -> Result<f64, String> {
                self.counts.nodes += 1;
                let Some(actor) = hand.actor() else {
                    self.counts.terminals += 1;
                    let s = hand.settlement().ok_or("finished hand without settlement")?;
                    return Ok(s.rewards[traverser] as f64 / hand.config().big_blind() as f64);
                };
                let view = hand.observe(actor)?;
                let choices = menu(&view);
                let legal = features::legal_mask(&view);
                let bytes = features::quantize(&features::encode(&view, Some(self.ctx.tables))?);
                let sigma = self.ctx.net.strategy(&bytes, legal, &mut self.scratch);
                let players = hand.config().players();
                let street = view.street as usize;
                if actor != traverser {
                    self.record(STRATEGY, players, street, legal, &sigma, &bytes);
                    self.counts.strategy += 1;
                    return self.follow(hand, traverser, explored, &choices, &sigma, rng);
                }
                let in_street = if explored.street == street { explored.in_street } else { 0 };
                if in_street >= self.ctx.bound.per_street || explored.total >= self.ctx.bound.total {
                    self.counts.sampled += 1;
                    self.counts.sampled_by_street[street.min(3)] += 1;
                    return self.follow(hand, traverser, explored, &choices, &sigma, rng);
                }
                let below = Explored { total: explored.total + 1, street, in_street: in_street + 1 };
                let mut values = [0.; ACTIONS];
                for (label, action) in &choices {
                    let saved = hand.save();
                    hand.apply_mut(*action)?;
                    values[*label as usize] = self.visit(hand, traverser, below, rng)?;
                    hand.restore(saved);
                }
                let value: f64 = choices.iter().map(|(l, _)| sigma[*l as usize] * values[*l as usize]).sum();
                let mut regrets = [0.; ACTIONS];
                for (label, _) in &choices {
                    regrets[*label as usize] = values[*label as usize] - value;
                }
                self.record(ADVANTAGE, players, street, legal, &regrets, &bytes);
                self.counts.advantage += 1;
                self.counts.advantage_by_street[street.min(3)] += 1;
                Ok(value)
            }
            fn follow(&mut self, hand: &mut Hand, traverser: usize, explored: Explored, choices: &[(u8, Action)], sigma: &[f64; ACTIONS],
                      rng: &mut rand::rngs::StdRng) -> Result<f64, String> {
                let draw: f64 = rng.gen();
                let mut sum = 0.;
                let mut pick = None;
                for (i, (label, _)) in choices.iter().enumerate() {
                    let p = sigma[*label as usize];
                    if p > 0. {
                        pick = Some(i);
                        sum += p;
                        if draw < sum {
                            break;
                        }
                    }
                }
                let action = choices[pick.ok_or("empty strategy")?].1;
                let saved = hand.save();
                hand.apply_mut(action)?;
                let value = self.visit(hand, traverser, explored, rng)?;
                hand.restore(saved);
                Ok(value)
            }
        }
    }

    /// A three-layer advantage network with random weights: mixed strategies that differ by node,
    /// with many ReLU zeros, so parity covers the skipped-zero paths.
    fn random(seed: u64, hidden: &[usize]) -> PolicyNetwork {
        use rand::Rng;
        let mut rng = rand::rngs::StdRng::seed_from_u64(seed);
        let mut dims = vec![features::len()];
        dims.extend_from_slice(hidden);
        dims.push(ACTIONS);
        let layers: Vec<_> = dims.windows(2).map(|w| serde_json::json!({"in":w[0],"out":w[1]})).collect();
        let header = serde_json::to_vec(&serde_json::json!({"format":crate::policy_network::FORMAT,"layout_sha256":features::layout_sha256(),
            "features":features::len(),"layers":layers,"activation":"relu","output":"advantage-6"})).unwrap();
        let mut f = crate::policy_network::MAGIC.to_vec();
        f.extend_from_slice(&(header.len() as u64).to_le_bytes());
        f.extend_from_slice(&header);
        for w in dims.windows(2) {
            let scale = (2. / w[0] as f64).sqrt() as f32;
            for _ in 0..w[0] * w[1] + w[1] {
                f.extend_from_slice(&(rng.gen_range(-1f32..1.) * scale).to_le_bytes());
            }
        }
        PolicyNetwork::parse(&f).unwrap()
    }

    #[test]
    fn the_walk_reproduces_the_recursive_traversal_byte_for_byte() {
        let Some(t) = tables() else { return };
        for (net, b) in [(random(3, &[64, 32]), bound(3, 8)), (constant([0.1, 0.2, 1.0, -1.0, 0.5, -0.3]), bound(2, 5)),
                         (random(4, &[32]), Bound::NONE)] {
            let fast = net.fast();
            let ctx = Context { net: &fast, tables: t, iteration: 7, bound: b };
            let mut old = reference::Recursive::new(ctx);
            let mut new = Traversal::bounded(&fast, t, 7, b);
            for i in 0..40 {
                assert_eq!(old.run(21, i, &[3, 4, 5, 6]).unwrap().to_bits(), new.run(21, i, &[3, 4, 5, 6]).unwrap().to_bits(), "value {i}");
            }
            assert!(old.counts.advantage > 0 && old.counts.strategy > 0);
            assert_eq!(old.out, new.out);
            assert_eq!(old.counts, new.counts);
        }
    }

    #[test]
    fn batched_walks_equal_single_traversals_at_every_width() {
        let Some(t) = tables() else { return };
        let net = random(5, &[64, 64, 32]);
        let fast = net.fast();
        let ctx = Context { net: &fast, tables: t, iteration: 3, bound: bound(3, 8) };
        let single: Vec<(Vec<u8>, Counts, u64)> = (10..70).map(|i| {
            let mut x = Traversal::bounded(&fast, t, 3, ctx.bound);
            let v = x.run(8, i, &[3, 6]).unwrap();
            (x.out, x.counts, v.to_bits())
        }).collect();
        for width in [1, 2, 7, 16, 64, 100] {
            let got: Vec<_> = run_batched(&ctx, 8, &[3, 6], 10..70, width).unwrap().into_iter().map(|(o, c, v)| (o, c, v.to_bits())).collect();
            assert!(got == single, "width {width}");
        }
    }
}
