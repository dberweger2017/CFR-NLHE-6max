//! N-player external sampling. The legacy HU traversal is intentionally separate.
use crate::cfr::{fsum, regret_match, Key, KeyHasher, MAX_ACTIONS};
use crate::gz::Gzip;
use crate::store::{Allocation, Store, View};
use rand::{Rng, SeedableRng};
use std::collections::HashMap;
use std::hash::BuildHasherDefault;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Decision {
    pub key: Key,
    pub actor: usize,
    /// Stable identity inside the key (button-relative in cash games).
    pub owner: usize,
    pub street: usize,
    /// Ordered actions have ascending bit positions; identity is checked on every hit.
    pub code: u16,
}
impl Decision {
    pub fn len(self) -> usize {
        self.code.count_ones() as usize
    }
}

/// Privileged simulator interface. Only `decision` constructs policy inputs;
/// root sampling and terminal payoffs may use the hidden simulated deal.
pub trait State {
    type Saved;
    fn players(&self) -> usize;
    fn decision(&self) -> Option<Decision>;
    fn payoff(&self, player: usize) -> f64;
    fn save(&self) -> Self::Saved;
    fn restore(&mut self, saved: Self::Saved);
    fn apply(&mut self, action_index: usize);
}

pub trait Game {
    type State: State;
    fn players(&self) -> usize;
    fn identity(&self) -> serde_json::Value;
    fn sample(&self, rng: &mut rand::rngs::StdRng) -> Self::State;
}

#[derive(Clone, Debug, PartialEq)]
pub struct Entry {
    pub actor: u8,
    pub street: u8,
    pub code: u16,
    pub regrets: Box<[f64]>,
    /// No allocation for excluded streets, including opponent-only visits.
    pub average: Option<Box<[f64]>>,
    pub visits: u64,
}
impl Entry {
    pub fn new(d: Decision, last_average_street: usize) -> Self {
        assert!((1..=MAX_ACTIONS).contains(&d.len()) && d.street < 4 && d.actor < 6 && d.owner < 6);
        Self {
            actor: d.owner as u8,
            street: d.street as u8,
            code: d.code,
            regrets: vec![0.; d.len()].into_boxed_slice(),
            average: (d.street <= last_average_street)
                .then(|| vec![0.; d.len()].into_boxed_slice()),
            visits: 0,
        }
    }
    pub fn stored(&self) -> Stored<'_> {
        Stored {
            actor: self.actor,
            street: self.street,
            code: self.code,
            visits: self.visits,
            regrets: &self.regrets,
            average: self.average.as_deref(),
        }
    }
    pub fn check(&self, d: Decision) {
        self.stored().check(d)
    }
}

/// One iteration's update of an entry, stored inline so building deltas allocates nothing per
/// entry.
#[derive(Clone, Copy, Debug)]
pub struct Delta {
    pub actor: u8,
    pub street: u8,
    pub code: u16,
    len: u8,
    averaged: bool,
    regrets: [f64; MAX_ACTIONS],
    average: [f64; MAX_ACTIONS],
    pub visits: u64,
}
impl Delta {
    pub fn new(d: Decision, last_average_street: usize) -> Self {
        assert!((1..=MAX_ACTIONS).contains(&d.len()) && d.street < 4 && d.actor < 6 && d.owner < 6);
        Self {
            actor: d.owner as u8,
            street: d.street as u8,
            code: d.code,
            len: d.len() as u8,
            averaged: d.street <= last_average_street,
            regrets: [0.; MAX_ACTIONS],
            average: [0.; MAX_ACTIONS],
            visits: 0,
        }
    }
    pub fn regrets(&self) -> &[f64] {
        &self.regrets[..self.len as usize]
    }
    pub fn regrets_mut(&mut self) -> &mut [f64] {
        &mut self.regrets[..self.len as usize]
    }
    /// None for streets outside the averaging scope.
    pub fn average(&self) -> Option<&[f64]> {
        self.averaged.then(|| &self.average[..self.len as usize])
    }
    pub fn average_mut(&mut self) -> Option<&mut [f64]> {
        self.averaged.then(|| &mut self.average[..self.len as usize])
    }
    fn stored(&self) -> Stored<'_> {
        Stored {
            actor: self.actor,
            street: self.street,
            code: self.code,
            visits: self.visits,
            regrets: self.regrets(),
            average: self.average(),
        }
    }
    pub fn check(&self, d: Decision) {
        self.stored().check(d)
    }
}

/// An entry as the table holds it.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Stored<'a> {
    pub actor: u8,
    pub street: u8,
    pub code: u16,
    pub visits: u64,
    pub regrets: &'a [f64],
    pub average: Option<&'a [f64]>,
}
impl<'a> Stored<'a> {
    /// The store's `meta`: owner in the low byte, street in the next.
    fn meta(&self) -> u32 {
        self.actor as u32 | (self.street as u32) << 8
    }
    fn view(&self) -> View<'a> {
        View { code: self.code, meta: self.meta(), visits: self.visits, regrets: self.regrets, average: self.average }
    }
    fn of(v: View<'a>) -> Self {
        Stored {
            actor: v.meta as u8,
            street: (v.meta >> 8) as u8,
            code: v.code,
            visits: v.visits,
            regrets: v.regrets,
            average: v.average,
        }
    }
    pub fn check(&self, d: Decision) {
        assert_eq!(
            (
                self.actor as usize,
                self.street as usize,
                self.code,
                self.regrets.len()
            ),
            (d.owner, d.street, d.code, d.len()),
            "information key changed owner, street or actions"
        );
    }
    pub fn policy(&self, average: bool) -> [f64; MAX_ACTIONS] {
        if average {
            regret_match(self.average.expect("average not stored for this street"))
        } else {
            regret_match(self.regrets)
        }
    }
}

/// One iteration's updates, in deterministic DFS order per key.
pub type Deltas = HashMap<Key, Delta, BuildHasherDefault<KeyHasher>>;

/// The training table: the HU trainer's compact sharded store.
#[derive(Clone, Default)]
pub struct Table(Store);
impl Table {
    pub fn len(&self) -> usize {
        self.0.len()
    }
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
    pub fn get(&self, key: &Key) -> Option<Stored<'_>> {
        self.0.view(key).map(Stored::of)
    }
    pub fn contains_key(&self, key: &Key) -> bool {
        self.0.contains(key)
    }
    /// Adds a new key's entry; false if the key is already stored.
    pub fn insert(&mut self, key: Key, entry: Entry) -> bool {
        self.0.insert_view(key, entry.stored().view())
    }
    /// Merges `tasks` shard by shard, each key's deltas summed in task order. Returns the keys and
    /// visits discarded when `frozen`, then the new keys declined because `traverser_admission`
    /// admits only summed deltas with a traverser visit.
    pub fn merge_all(&mut self, tasks: Vec<Deltas>, frozen: bool, traverser_admission: bool, parallel: bool) -> (u64, u64, u64) {
        use rayon::prelude::*;
        let shards = self.0 .0.len();
        let split = |deltas: Deltas| {
            let mut parts: Vec<Vec<(Key, Delta)>> = (0..shards).map(|_| Vec::new()).collect();
            for (key, delta) in deltas {
                parts[Store::shard(&key)].push((key, delta));
            }
            parts
        };
        let split: Vec<Vec<Vec<(Key, Delta)>>> = if parallel { tasks.into_par_iter().map(split).collect() } else { tasks.into_iter().map(split).collect() };
        let mut by_shard: Vec<Vec<Vec<(Key, Delta)>>> = (0..shards).map(|_| Vec::with_capacity(split.len())).collect();
        for task in split {
            for (s, part) in task.into_iter().enumerate() {
                by_shard[s].push(part);
            }
        }
        let merge = |(shard, parts): (&mut crate::store::Shard, Vec<Vec<(Key, Delta)>>)| {
            let part: Vec<(Key, Delta)> = if parts.len() == 1 {
                parts.into_iter().next().unwrap()
            } else {
                let mut combined = Deltas::default();
                for (key, delta) in parts.into_iter().flatten() {
                    absorb(&mut combined, key, delta);
                }
                combined.into_iter().collect()
            };
            let mut discarded = (0, 0, 0);
            for (key, delta) in part {
                if frozen && !shard.contains(&key) {
                    discarded = (discarded.0 + 1, discarded.1 + delta.visits, discarded.2);
                } else if traverser_admission && delta.visits == 0 && !shard.contains(&key) {
                    discarded.2 += 1;
                } else {
                    shard.merge(key, delta.stored().view());
                }
            }
            discarded
        };
        let sum = |a: (u64, u64, u64), b: (u64, u64, u64)| (a.0 + b.0, a.1 + b.1, a.2 + b.2);
        if parallel {
            self.0 .0.par_iter_mut().zip(by_shard).map(merge).reduce(|| (0, 0, 0), sum)
        } else {
            self.0 .0.iter_mut().zip(by_shard).map(merge).fold((0, 0, 0), sum)
        }
    }
    /// Every entry, in no particular order.
    pub fn iter(&self) -> impl Iterator<Item = (Key, Stored<'_>)> + '_ {
        self.0.views().map(|(k, v)| (k, Stored::of(v)))
    }
    /// Every entry in key order.
    pub fn sorted(&self) -> impl Iterator<Item = (Key, Stored<'_>)> + '_ {
        self.0.sorted_views().map(|(k, v)| (k, Stored::of(v)))
    }
    pub fn keys(&self) -> impl Iterator<Item = Key> + '_ {
        self.iter().map(|(k, _)| k)
    }
    pub fn values(&self) -> impl Iterator<Item = Stored<'_>> + '_ {
        self.iter().map(|(_, v)| v)
    }
    pub fn allocation(&self) -> Allocation {
        self.0.allocation()
    }
    /// Bytes of stored regrets and stored averages.
    pub fn payload_bytes(&self) -> (usize, usize) {
        self.0.payload_bytes()
    }
    pub fn index_capacity(&self) -> usize {
        self.0.index_capacity()
    }
    /// `head`, then one `row` per entry in key order, formatted in parallel.
    pub fn write_sorted(&self, file: std::fs::File, gzip: Gzip, head: &[u8],
                        row: impl Fn(Key, Stored, &mut Vec<u8>) + Sync) -> std::io::Result<std::fs::File> {
        self.0.write_sorted(file, gzip, head, |shard, i, out| {
            let (key, v) = shard.row_view(i);
            row(key, Stored::of(v), out)
        })
    }
}
impl PartialEq for Table {
    fn eq(&self, other: &Self) -> bool {
        self.len() == other.len() && self.sorted().eq(other.sorted())
    }
}
impl std::fmt::Debug for Table {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_map().entries(self.sorted()).finish()
    }
}

fn sample_policy<R: Rng>(rng: &mut R, policy: &[f64]) -> usize {
    pick(rng.gen(), policy)
}

/// The action whose cumulative probability first exceeds `draw` in [0, 1).
fn pick(draw: f64, policy: &[f64]) -> usize {
    let mut cumulative = 0.;
    for (i, &p) in policy.iter().enumerate() {
        cumulative += p;
        if draw < cumulative {
            return i;
        }
    }
    // Rounded cumulative probabilities can end just below one. The fallback
    // must still have positive mass; the last legal action may have zero regret.
    policy
        .iter()
        .rposition(|&p| p > 0.)
        .expect("empty policy support")
}

const PRESSURE_SALT: u64 = 0x7072_6573_7375_7265;

/// Cash-game menu labels (multi_holdem::menu): the pot-size raise is label 4; when its
/// target equals the minimum raise the menu keeps only label 3, which is then the pot raise.
pub fn pressure_action(d: Decision) -> Option<usize> {
    [4u16, 3].into_iter().find(|&label| d.code & (1 << label) != 0)
        .map(|label| (d.code & ((1 << label) - 1)).count_ones() as usize)
}

fn splitmix(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9E37_79B9_7F4A_7C15);
    x = (x ^ (x >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    x ^ (x >> 31)
}

/// A node's identity within its traversal: the root is 0, each child hashes its parent and action.
pub fn child_path(path: u64, action: usize) -> u64 {
    splitmix(path ^ splitmix(action as u64 + 1))
}

/// How a traversal draws opponent actions, and whether it forks traverser subtrees.
pub trait Sampler<S: State>: Sized {
    fn sample(&mut self, policy: &[f64], path: u64) -> usize;
    /// An extra uniform draw in [0, 1) for opponent pressure; only drawn when pressure is on.
    fn pressure_draw(&mut self, path: u64) -> f64;
    /// Every child's value, deltas and counts, visited in parallel; None visits in order.
    fn fork(_t: &Traversal<'_, Self>, _state: &S, _n: usize, _pruned: &[bool; MAX_ACTIONS], _path: u64, _depth: u8) -> Option<Vec<(f64, Deltas, Counts)>> {
        None
    }
}

/// The production recipe: one random stream per root, consumed in DFS order.
pub struct Stream<'a, R: Rng>(pub &'a mut R);
impl<R: Rng, S: State> Sampler<S> for Stream<'_, R> {
    fn sample(&mut self, policy: &[f64], _path: u64) -> usize {
        sample_policy(self.0, policy)
    }
    fn pressure_draw(&mut self, _path: u64) -> f64 {
        self.0.gen()
    }
}

/// Fast mode: each draw depends only on the root's seed and the node's path, so subtrees are
/// independent and can run in parallel.
#[derive(Clone, Copy, Debug)]
pub struct PathSampler(pub u64);
impl<S: State + Clone + Send + Sync> Sampler<S> for PathSampler {
    fn sample(&mut self, policy: &[f64], path: u64) -> usize {
        pick((splitmix(self.0 ^ path) >> 11) as f64 * (1.0 / (1u64 << 53) as f64), policy)
    }
    fn pressure_draw(&mut self, path: u64) -> f64 {
        // Domain-separated from the action draw at the same node.
        (splitmix(self.0 ^ path ^ PRESSURE_SALT) >> 11) as f64 * (1.0 / (1u64 << 53) as f64)
    }
    fn fork(t: &Traversal<'_, Self>, state: &S, n: usize, pruned: &[bool; MAX_ACTIONS], path: u64, depth: u8) -> Option<Vec<(f64, Deltas, Counts)>> {
        use rayon::prelude::*;
        (depth < t.fork_depth).then(|| {
            (0..n).into_par_iter().map(|a| {
                let (mut deltas, mut counts) = (Deltas::default(), Counts::default());
                if pruned[a] {
                    return (0., deltas, counts);
                }
                let mut child = state.clone();
                child.apply(a);
                let value = Traversal { table: t.table, deltas: &mut deltas, sampler: t.sampler, traverser: t.traverser,
                    weight: t.weight, last_average_street: t.last_average_street, counts: &mut counts, fork_depth: t.fork_depth,
                    prune_below: t.prune_below, pressure: t.pressure }
                    .visit(&mut child, child_path(path, a), depth + 1);
                (value, deltas, counts)
            }).collect()
        })
    }
}

/// Traverser depths that fork in fast mode; changes only the summation order.
pub const FORK_DEPTH: u8 = 1;
/// Checkpoint `sampling` of fast mode; absent for the production stream.
pub const PATH_SAMPLING: &str = "path-v1";

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Sampling {
    #[default]
    Stream,
    Path,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Counts {
    pub nodes: u64,
    pub terminals: u64,
    pub decisions: [u64; 4],
    pub missing: [u64; 4],
    pub traverser: [u64; 6],
    pub discarded_keys: u64,
    pub discarded_visits: u64,
    /// Actions skipped by pruning; recorded under the checkpoint's `pruning`, not `counts`.
    pub pruned: u64,
    /// Opponent pot raises forced by pressure; recorded under `opponent_pressure`, not `counts`.
    pub pressured: u64,
    /// New keys with only opponent updates, declined by traverser admission and summed over
    /// iterations; recorded under `admission`, not `counts`.
    pub declined: u64,
}
impl Counts {
    fn add(&mut self, other: &Counts) {
        self.nodes += other.nodes;
        self.terminals += other.terminals;
        for i in 0..4 {
            self.decisions[i] += other.decisions[i];
            self.missing[i] += other.missing[i];
        }
        for i in 0..6 {
            self.traverser[i] += other.traverser[i];
        }
        self.discarded_keys += other.discarded_keys;
        self.discarded_visits += other.discarded_visits;
        self.pruned += other.pruned;
        self.pressured += other.pressured;
        self.declined += other.declined;
    }
}

/// Adds `delta` to `key`'s entry in `deltas`, or stores it as a new entry.
fn absorb(deltas: &mut Deltas, key: Key, delta: Delta) {
    match deltas.entry(key) {
        std::collections::hash_map::Entry::Vacant(slot) => {
            slot.insert(delta);
        }
        std::collections::hash_map::Entry::Occupied(mut slot) => {
            let e = slot.get_mut();
            assert_eq!((e.actor, e.street, e.code, e.len, e.averaged), (delta.actor, delta.street, delta.code, delta.len, delta.averaged));
            for (sum, inc) in e.regrets_mut().iter_mut().zip(delta.regrets()) {
                *sum += inc;
            }
            if let (Some(sum), Some(inc)) = (e.average_mut(), delta.average()) {
                for (s, i) in sum.iter_mut().zip(inc) {
                    *s += i;
                }
            }
            e.visits += delta.visits;
        }
    }
}

/// Immutable snapshot until *all* traversers finish: no branch or seat observes
/// an earlier branch's update. Deltas are accumulated in deterministic DFS order;
/// forked subtrees are added in action order.
pub struct Traversal<'a, P> {
    pub table: &'a Table,
    pub deltas: &'a mut Deltas,
    pub sampler: P,
    pub traverser: usize,
    pub weight: f64,
    pub last_average_street: usize,
    pub counts: &'a mut Counts,
    pub fork_depth: u8,
    /// Regret-based pruning limit of this iteration; None explores every action.
    pub prune_below: Option<f64>,
    /// Probability that a sampled opponent decision takes the pot-size raise instead of its policy.
    pub pressure: Option<f64>,
}
impl<P> Traversal<'_, P> {
    pub fn run<S: State>(&mut self, state: &mut S) -> f64
    where
        P: Sampler<S>,
    {
        self.visit(state, 0, 0)
    }
    fn visit<S: State>(&mut self, state: &mut S, path: u64, depth: u8) -> f64
    where
        P: Sampler<S>,
    {
        self.counts.nodes += 1;
        let Some(d) = state.decision() else {
            self.counts.terminals += 1;
            let payoff = state.payoff(self.traverser);
            assert!(payoff.is_finite(), "non-finite terminal utility");
            return payoff;
        };
        assert!(d.actor < state.players() && self.traverser < state.players());
        self.counts.decisions[d.street] += 1;
        let n = d.len();
        let stored = self.table.get(&d.key);
        let policy = if let Some(entry) = stored {
            entry.check(d);
            entry.policy(false)
        } else {
            self.counts.missing[d.street] += 1;
            [1. / n as f64; MAX_ACTIONS]
        };
        if d.actor != self.traverser {
            // For N>2 this retains the requested opponent-sampled estimator,
            // whose visitation also includes other sampled players' reach.
            if d.street <= self.last_average_street {
                let delta = self
                    .deltas
                    .entry(d.key)
                    .or_insert_with(|| Delta::new(d, self.last_average_street));
                delta.check(d);
                for (sum, p) in delta.average_mut().unwrap().iter_mut().zip(policy) {
                    *sum += self.weight * p;
                }
            }
            let pressured = self.pressure.and_then(|p| pressure_action(d).map(|a| (p, a)));
            let action = match pressured {
                Some((p, a)) if self.sampler.pressure_draw(path) < p => {
                    self.counts.pressured += 1;
                    a
                }
                _ => self.sampler.sample(&policy[..n], path),
            };
            let saved = state.save();
            state.apply(action);
            let value = self.visit(state, child_path(path, action), depth);
            state.restore(saved);
            return value;
        }
        self.counts.traverser[d.actor] += 1;
        // Pruned: zero probability and stored regret below the limit; `value` is unchanged.
        let mut pruned = [false; MAX_ACTIONS];
        if let (Some(limit), Some(entry)) = (self.prune_below, stored) {
            for a in 0..n {
                pruned[a] = policy[a] == 0. && entry.regrets[a] < limit;
            }
            self.counts.pruned += pruned.iter().filter(|&&p| p).count() as u64;
        }
        let mut values = [0.; MAX_ACTIONS];
        if let Some(children) = P::fork(self, state, n, &pruned, path, depth) {
            for (a, (value, deltas, counts)) in children.into_iter().enumerate() {
                values[a] = value;
                self.counts.add(&counts);
                for (key, delta) in deltas {
                    absorb(self.deltas, key, delta);
                }
            }
        } else {
            for (a, value) in values[..n].iter_mut().enumerate().filter(|(a, _)| !pruned[*a]) {
                let saved = state.save();
                state.apply(a);
                *value = self.visit(state, child_path(path, a), depth + 1);
                state.restore(saved);
            }
        }
        let value = fsum((0..n).map(|a| policy[a] * values[a]));
        let delta = self
            .deltas
            .entry(d.key)
            .or_insert_with(|| Delta::new(d, self.last_average_street));
        delta.check(d);
        for (a, r) in delta.regrets_mut().iter_mut().enumerate().filter(|(a, _)| !pruned[*a]) {
            *r += self.weight * (values[a] - value);
        }
        delta.visits += 1;
        value
    }
}

#[cfg(test)]
mod sampling_tests {
    #[test]
    fn rounding_cannot_sample_a_zero_probability_action() {
        let mut rng = rand::rngs::mock::StepRng::new(u64::MAX, 0);
        let mut policy = [1. / 6.; 7];
        policy[6] = 0.;
        assert_eq!(super::sample_policy(&mut rng, &policy), 5);
    }
}

#[derive(Clone, Debug)]
pub struct Trainer {
    pub identity: serde_json::Value,
    pub players: usize,
    pub seed: u64,
    pub iteration: u64,
    pub last_average_street: usize,
    pub max_entries: usize,
    pub freeze_at_cap: bool,
    pub frozen_at: Option<u64>,
    pub table: Table,
    pub counts: Counts,
    pub sampling: Sampling,
    /// Fast mode: traversals per seat and iteration.
    pub roots_per_seat: usize,
    /// Fast mode: regret-based pruning (docs/nplayer-pruning.md).
    pub prune: Option<Prune>,
    /// Fast cash-game mode: probability that a sampled opponent decision takes the pot-size
    /// raise (docs/nplayer-opponent-pressure.md). Average strategies still record the policy.
    pub pressure: Option<f64>,
    /// Fast mode: a new key enters the table only with a traverser update
    /// (docs/nplayer-traverser-admission.md). Opponent-only rows keep zero regrets and so play
    /// exactly the uniform fallback while holding capacity.
    pub traverser_admission: bool,
}

/// Skip traverser actions with zero probability whose regret shows an average loss above `bb`
/// per iteration, after iteration `after`, except in about one iteration in 20.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Prune {
    pub bb: f64,
    pub after: u64,
}
impl Prune {
    /// This iteration's limit: `-bb` per root, times the linear weights so far; None in full
    /// iterations.
    pub fn limit(self, seed: u64, iteration: u64, roots_per_seat: usize) -> Option<f64> {
        let full = child_path(seed, iteration as usize) % 20 == 0;
        let t = iteration as f64;
        (iteration > self.after && !full).then(|| -self.bb * roots_per_seat as f64 * t * (t + 1.) / 2.)
    }
}
impl Trainer {
    pub fn new<G: Game>(
        game: &G,
        seed: u64,
        last_average_street: usize,
        max_entries: usize,
        freeze_at_cap: bool,
    ) -> Self {
        assert!((2..=6).contains(&game.players()) && last_average_street < 4 && max_entries > 0);
        Self {
            identity: game.identity(),
            players: game.players(),
            seed,
            iteration: 0,
            last_average_street,
            max_entries,
            freeze_at_cap,
            frozen_at: None,
            table: Table::default(),
            counts: Counts::default(),
            sampling: Sampling::Stream,
            roots_per_seat: 1,
            prune: None,
            pressure: None,
            traverser_admission: false,
        }
    }
    /// Starts the next iteration; its linear weight.
    fn begin<G: Game>(&mut self, game: &G, sampling: Sampling) -> f64 {
        assert_eq!(self.sampling, sampling, "training continues with the checkpoint's sampling");
        assert!(match sampling { Sampling::Stream => self.roots_per_seat == 1, Sampling::Path => (1..=1024).contains(&self.roots_per_seat) },
            "roots per seat: 1 in production, 1 to 1024 in fast mode");
        assert!(self.prune.map_or(true, |p| sampling == Sampling::Path && p.bb.is_finite() && p.bb > 0.),
            "pruning: fast mode only, with a positive finite limit");
        assert!(self.pressure.map_or(true, |p| sampling == Sampling::Path && p > 0. && p <= 1.),
            "opponent pressure: fast mode only, probability in (0, 1]");
        assert!(!self.traverser_admission || sampling == Sampling::Path, "traverser admission: fast mode only");
        assert_eq!(game.identity(), self.identity);
        assert_eq!(game.players(), self.players);
        assert!(
            self.freeze_at_cap || self.table.len() < self.max_entries,
            "table cap reached"
        );
        self.iteration = self.iteration.checked_add(1).expect("iteration overflow");
        // Exact integer linear weights; checkpoint boundaries never split a sweep.
        assert!(
            self.iteration <= 1 << 53,
            "linear weight no longer exactly representable"
        );
        self.iteration as f64
    }
    /// Domain-separated deterministic root streams need no opaque RNG state
    /// in checkpoints and do not depend on thread scheduling or hash order.
    pub(crate) fn root(&self, player: usize, domain: &[u8]) -> rand::rngs::StdRng {
        use sha2::{Digest, Sha256};
        let mut hash = Sha256::new();
        hash.update(domain);
        hash.update(self.seed.to_le_bytes());
        hash.update(self.iteration.to_le_bytes());
        hash.update((player as u64).to_le_bytes());
        rand::rngs::StdRng::from_seed(hash.finalize().into())
    }
    /// One iteration of the production recipe: seats in order, draws from each root's stream.
    pub fn step<G: Game>(&mut self, game: &G) {
        let weight = self.begin(game, Sampling::Stream);
        let mut deltas = Deltas::default();
        let mut counts = std::mem::take(&mut self.counts);
        for player in 0..self.players {
            let mut rng = self.root(player, b"nplayer-external-sampling-v1");
            let mut state = game.sample(&mut rng);
            assert_eq!(state.players(), self.players);
            Traversal {
                table: &self.table,
                deltas: &mut deltas,
                sampler: Stream(&mut rng),
                traverser: player,
                weight,
                last_average_street: self.last_average_street,
                counts: &mut counts,
                fork_depth: 0,
                prune_below: None,
                pressure: None,
            }
            .run(&mut state);
        }
        self.counts = counts;
        self.apply(vec![deltas]);
    }
    /// One iteration of fast mode (docs/nplayer-fast-mode.md); identical for any thread count.
    pub fn step_fast<G: Game + Sync>(&mut self, game: &G)
    where
        G::State: Clone + Send + Sync,
    {
        use rayon::prelude::*;
        let weight = self.begin(game, Sampling::Path);
        let prune_below = self.prune.and_then(|p| p.limit(self.seed, self.iteration, self.roots_per_seat));
        let roots: Vec<(usize, usize)> = (0..self.players).flat_map(|p| (0..self.roots_per_seat).map(move |r| (p, r))).collect();
        let tasks: Vec<(Deltas, Counts)> = roots.into_par_iter().map(|(player, r)| {
            let (mut rng, seed) = self.fast_root(player, r);
            let mut state = game.sample(&mut rng);
            assert_eq!(state.players(), self.players);
            let (mut deltas, mut counts) = (Deltas::default(), Counts::default());
            Traversal {
                table: &self.table,
                deltas: &mut deltas,
                sampler: PathSampler(seed),
                traverser: player,
                weight,
                last_average_street: self.last_average_street,
                counts: &mut counts,
                fork_depth: FORK_DEPTH,
                prune_below,
                pressure: self.pressure,
            }
            .run(&mut state);
            (deltas, counts)
        }).collect();
        let mut all = Vec::with_capacity(tasks.len());
        for (deltas, counts) in tasks {
            self.counts.add(&counts);
            all.push(deltas);
        }
        self.apply(all);
    }
    /// A fast root's deal stream and path seed: root 0 deals the production deal.
    pub(crate) fn fast_root(&self, player: usize, root: usize) -> (rand::rngs::StdRng, u64) {
        let deal = if root == 0 { self.root(player, b"nplayer-external-sampling-v1") } else { self.extra_root(player, root, b"nplayer-fast-root-v1") };
        (deal, rand::RngCore::next_u64(&mut self.extra_root(player, root, b"nplayer-path-sampling-v1")))
    }
    fn extra_root(&self, player: usize, root: usize, domain: &[u8]) -> rand::rngs::StdRng {
        use sha2::{Digest, Sha256};
        let mut hash = Sha256::new();
        hash.update(domain);
        hash.update(self.seed.to_le_bytes());
        hash.update(self.iteration.to_le_bytes());
        hash.update((player as u64).to_le_bytes());
        hash.update((root as u64).to_le_bytes());
        rand::rngs::StdRng::from_seed(hash.finalize().into())
    }
    /// Production merges on its own thread, fast mode in parallel.
    fn apply(&mut self, tasks: Vec<Deltas>) {
        let parallel = self.sampling == Sampling::Path;
        let (keys, visits, declined) = self.table.merge_all(tasks, self.frozen_at.is_some(), self.traverser_admission, parallel);
        self.counts.discarded_keys += keys;
        self.counts.discarded_visits += visits;
        self.counts.declined += declined;
        if self.freeze_at_cap && self.frozen_at.is_none() && self.table.len() >= self.max_entries {
            self.frozen_at = Some(self.iteration);
        }
    }
}
