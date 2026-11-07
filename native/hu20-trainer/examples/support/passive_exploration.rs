//! Research-only perturbed-policy traversal. Production trainer/consumers never call this.
use hu20_trainer::{
    cfr::{fsum, Key, MAX_ACTIONS},
    multi_cfr::{
        child_path, Counts, Decision, Delta, Deltas, Game, PathSampler, Sampler, State, Table,
    },
};
use rand::{rngs::StdRng, RngCore, SeedableRng};
use rayon::prelude::*;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

/// Evaluator-only public-history metadata, never consumed by a policy query.
pub trait DiagnosticState: State {
    fn family(&self, owner: usize) -> u8;
}
impl DiagnosticState for hu20_trainer::multi_holdem::CashState {
    fn family(&self, owner: usize) -> u8 {
        use hu20_trainer::{game::Kind, nplayer::Event};
        let (mut own, mut passive) = (false, 0);
        let mut others = BTreeSet::new();
        for e in self.hand.history() {
            if let Event::Action {
                street,
                actor,
                action,
                ..
            } = e
            {
                if *street as usize == 0 {
                    continue;
                }
                if action.kind == Kind::Raise {
                    if *actor == owner {
                        own = true;
                    } else {
                        others.insert(*actor);
                    }
                }
                if *actor != owner && matches!(action.kind, Kind::Check | Kind::Call) {
                    passive += 1;
                }
            }
        }
        if others.is_empty() {
            u8::from(own)
        } else if others.len() == 1 && passive >= 2 {
            2
        } else {
            3
        }
    }
}
#[derive(Default)]
pub struct RootMeta {
    pub families: BTreeSet<u8>,
    pub regret_nonzero_paths: u64,
    pub regret_zero_paths: u64,
    pub average_paths: u64,
    pub regret_path_l1: f64,
}
pub type Contexts = BTreeMap<Key, RootMeta>;

pub fn policies(
    table: &Table,
    d: Decision,
    epsilon: f64,
) -> ([f64; MAX_ACTIONS], [f64; MAX_ACTIONS]) {
    assert!(epsilon.is_finite() && (0. ..1.).contains(&epsilon));
    let n = d.len();
    assert!((1..=MAX_ACTIONS).contains(&n));
    let base = match table.get(&d.key) {
        Some(e) => {
            e.check(d);
            assert!(e.regrets.iter().all(|x| x.is_finite()));
            let p = e.policy(false);
            assert!(
                e.regrets.iter().zip(p).all(|(r, p)| *r <= 0. || p > 0.),
                "normalization underflow"
            );
            p
        }
        None => [1. / n as f64; MAX_ACTIONS],
    };
    assert!(base[..n].iter().all(|p| p.is_finite() && *p >= 0.));
    assert!((fsum(base[..n].iter().copied()) - 1.).abs() < 1e-12);
    let mut actual = base;
    if epsilon != 0. {
        for a in 0..n {
            actual[a] = (1. - epsilon) * base[a] + epsilon / n as f64;
            assert!(actual[a].is_finite() && actual[a] > 0.);
        }
    }
    assert!((fsum(actual[..n].iter().copied()) - 1.).abs() < 1e-12);
    (base, actual)
}

pub fn add_counts(a: &mut Counts, b: &Counts) {
    a.nodes += b.nodes;
    a.terminals += b.terminals;
    for i in 0..4 {
        a.decisions[i] += b.decisions[i];
        a.missing[i] += b.missing[i];
    }
    for i in 0..6 {
        a.traverser[i] += b.traverser[i];
    }
    a.discarded_keys += b.discarded_keys;
    a.discarded_visits += b.discarded_visits;
    a.pruned += b.pruned;
    a.pressured += b.pressured;
    a.declined += b.declined;
}
fn absorb(all: &mut Deltas, key: Key, incoming: Delta) {
    match all.entry(key) {
        std::collections::hash_map::Entry::Vacant(v) => {
            v.insert(incoming);
        }
        std::collections::hash_map::Entry::Occupied(mut v) => {
            let d = v.get_mut();
            assert_eq!(
                (
                    d.actor,
                    d.street,
                    d.code,
                    d.regrets().len(),
                    d.average().is_some()
                ),
                (
                    incoming.actor,
                    incoming.street,
                    incoming.code,
                    incoming.regrets().len(),
                    incoming.average().is_some()
                )
            );
            for (a, b) in d.regrets_mut().iter_mut().zip(incoming.regrets()) {
                *a += b;
            }
            if let (Some(a), Some(b)) = (d.average_mut(), incoming.average()) {
                for (x, y) in a.iter_mut().zip(b) {
                    *x += y;
                }
            }
            d.visits += incoming.visits;
        }
    }
}

pub struct Walk<'a, P> {
    pub table: &'a Table,
    pub deltas: &'a mut Deltas,
    pub counts: &'a mut Counts,
    pub sampler: P,
    pub traverser: usize,
    pub weight: f64,
    pub epsilon: f64,
    pub contexts: &'a mut Contexts,
}
impl<P> Walk<'_, P> {
    pub fn run<S: DiagnosticState + Clone>(&mut self, s: &mut S) -> f64
    where
        P: Sampler<S> + Clone,
    {
        assert!(self.weight.is_finite() && self.weight > 0.);
        self.visit(s, 0, 0)
    }
    fn visit<S: DiagnosticState + Clone>(&mut self, s: &mut S, path: u64, depth: u8) -> f64
    where
        P: Sampler<S> + Clone,
    {
        self.counts.nodes += 1;
        let Some(d) = s.decision() else {
            self.counts.terminals += 1;
            let u = s.payoff(self.traverser);
            assert!(u.is_finite());
            return u;
        };
        assert!(d.actor < s.players() && self.traverser < s.players());
        self.contexts
            .entry(d.key)
            .or_default()
            .families
            .insert(s.family(d.actor));
        self.counts.decisions[d.street] += 1;
        self.counts.missing[d.street] += u64::from(!self.table.contains_key(&d.key));
        let n = d.len();
        let (pi, sigma) = policies(self.table, d, self.epsilon);
        if d.actor != self.traverser {
            let delta = self.deltas.entry(d.key).or_insert_with(|| Delta::new(d, 3));
            delta.check(d);
            for (a, p) in delta.average_mut().unwrap().iter_mut().zip(sigma) {
                *a += self.weight * p;
            }
            self.contexts.get_mut(&d.key).unwrap().average_paths += 1;
            let action = self.sampler.sample(&sigma[..n], path);
            assert!(action < n && sigma[action] > 0.);
            let saved = s.save();
            s.apply(action);
            let value = self.visit(s, child_path(path, action), depth);
            s.restore(saved);
            return value;
        }
        self.counts.traverser[d.actor] += 1;
        let mut values = [0.; MAX_ACTIONS];
        if depth < hu20_trainer::multi_cfr::FORK_DEPTH {
            // Preserve fast-mode delta grouping and action-order absorption,
            // even though root-level parallelism suffices for this small probe.
            for (a, value) in values[..n].iter_mut().enumerate() {
                let mut child = s.clone();
                child.apply(a);
                let (mut deltas, mut counts, mut contexts) =
                    (Deltas::default(), Counts::default(), Contexts::new());
                *value = Walk {
                    table: self.table,
                    deltas: &mut deltas,
                    counts: &mut counts,
                    sampler: self.sampler.clone(),
                    traverser: self.traverser,
                    weight: self.weight,
                    epsilon: self.epsilon,
                    contexts: &mut contexts,
                }
                .visit(&mut child, child_path(path, a), depth + 1);
                add_counts(self.counts, &counts);
                for (key, delta) in deltas {
                    absorb(self.deltas, key, delta);
                }
                for (key, meta) in contexts {
                    let to = self.contexts.entry(key).or_default();
                    to.families.extend(meta.families);
                    to.regret_nonzero_paths += meta.regret_nonzero_paths;
                    to.regret_zero_paths += meta.regret_zero_paths;
                    to.average_paths += meta.average_paths;
                    to.regret_path_l1 += meta.regret_path_l1;
                }
            }
        } else {
            for (a, value) in values[..n].iter_mut().enumerate() {
                let saved = s.save();
                s.apply(a);
                *value = self.visit(s, child_path(path, a), depth + 1);
                s.restore(saved);
            }
        }
        let value = fsum((0..n).map(|a| sigma[a] * values[a]));
        assert!(value.is_finite());
        let baseline = if self.epsilon == 0. {
            value
        } else {
            fsum((0..n).map(|a| pi[a] * values[a]))
        };
        let delta = self.deltas.entry(d.key).or_insert_with(|| Delta::new(d, 3));
        delta.check(d);
        let mut path_l1 = 0.;
        for (a, r) in delta.regrets_mut().iter_mut().enumerate() {
            let inc = if self.epsilon == 0. {
                self.weight * (values[a] - value)
            } else {
                self.weight * ((1. - self.epsilon) * (values[a] - baseline))
            };
            assert!(inc.is_finite());
            *r += inc;
            assert!(r.is_finite());
            path_l1 += inc.abs();
        }
        let meta = self.contexts.get_mut(&d.key).unwrap();
        meta.regret_nonzero_paths += u64::from(path_l1 > 0.);
        meta.regret_zero_paths += u64::from(path_l1 == 0.);
        meta.regret_path_l1 += path_l1;
        assert!(meta.regret_path_l1.is_finite());
        delta.visits += 1;
        value
    }
}

fn root(seed: u64, iteration: u64, seat: usize, extra: Option<usize>, domain: &[u8]) -> StdRng {
    let mut h = Sha256::new();
    h.update(domain);
    h.update(seed.to_le_bytes());
    h.update(iteration.to_le_bytes());
    h.update((seat as u64).to_le_bytes());
    if let Some(r) = extra {
        h.update((r as u64).to_le_bytes());
    }
    StdRng::from_seed(h.finalize().into())
}
pub fn roots(seed: u64, iteration: u64, seat: usize, r: usize) -> (StdRng, u64) {
    let deal = if r == 0 {
        root(seed, iteration, seat, None, b"nplayer-external-sampling-v1")
    } else {
        root(seed, iteration, seat, Some(r), b"nplayer-fast-root-v1")
    };
    let path = root(seed, iteration, seat, Some(r), b"nplayer-path-sampling-v1").next_u64();
    (deal, path)
}
pub struct ResearchTrainer {
    pub table: Table,
    pub counts: Counts,
    pub iteration: u64,
    pub frozen_at: Option<u64>,
    pub seed: u64,
    pub cap: usize,
    pub epsilon: f64,
    pub root_inventory: Vec<(u64, usize, usize, u64)>,
}
impl ResearchTrainer {
    pub fn new(seed: u64, cap: usize, epsilon: f64) -> Self {
        assert!(cap > 0 && epsilon.is_finite() && (0. ..1.).contains(&epsilon));
        Self {
            table: Table::default(),
            counts: Counts::default(),
            iteration: 0,
            frozen_at: None,
            seed,
            cap,
            epsilon,
            root_inventory: Vec::new(),
        }
    }
    pub fn step<G>(
        &mut self,
        game: &G,
        mut observer: impl FnMut(f64, &Table, &Deltas, &Contexts, bool) -> Result<(), String>,
    ) -> Result<(), String>
    where
        G: Game + Sync,
        G::State: DiagnosticState + Clone + Send + Sync,
    {
        self.iteration += 1;
        assert!(self.iteration <= 1 << 53);
        let weight = self.iteration as f64;
        let jobs: Vec<_> = (0..game.players())
            .flat_map(|p| (0..8).map(move |r| (p, r)))
            .collect();
        let tasks: Vec<_> = jobs
            .into_par_iter()
            .map(|(p, r)| {
                let (mut rng, path) = roots(self.seed, self.iteration, p, r);
                let mut state = game.sample(&mut rng);
                let (mut deltas, mut counts, mut contexts) =
                    (Deltas::default(), Counts::default(), Contexts::new());
                Walk {
                    table: &self.table,
                    deltas: &mut deltas,
                    counts: &mut counts,
                    sampler: PathSampler(path),
                    traverser: p,
                    weight,
                    epsilon: self.epsilon,
                    contexts: &mut contexts,
                }
                .run(&mut state);
                ((self.iteration, p, r, path), deltas, counts, contexts)
            })
            .collect();
        let mut all = Vec::with_capacity(tasks.len());
        for (id, deltas, counts, contexts) in tasks {
            observer(
                weight,
                &self.table,
                &deltas,
                &contexts,
                self.frozen_at.is_some(),
            )?;
            self.root_inventory.push(id);
            add_counts(&mut self.counts, &counts);
            all.push(deltas);
        }
        let (keys, visits, declined) =
            self.table
                .merge_all(all, self.frozen_at.is_some(), false, true);
        self.counts.discarded_keys += keys;
        self.counts.discarded_visits += visits;
        assert_eq!(declined, 0);
        if self.frozen_at.is_none() && self.table.len() >= self.cap {
            self.frozen_at = Some(self.iteration);
        }
        Ok(())
    }
}
