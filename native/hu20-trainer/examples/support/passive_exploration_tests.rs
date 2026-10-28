use super::probe;
use hu20_trainer::{
    cfr::Key,
    multi_cfr::{
        self, Counts, Decision, Deltas, Entry, Game, PathSampler, Sampler, State, Table, Trainer,
        Traversal,
    },
};
use rand::{rngs::StdRng, Rng};
use std::collections::BTreeMap;

#[derive(Clone)]
struct Toy {
    node: usize,
    n: usize,
    scale: f64,
}
impl Toy {
    fn decision_at(&self, node: usize) -> Option<Decision> {
        let actor = match node {
            0 => 1,
            1 | 2 => 0,
            5 => self.n - 1,
            6 => 1,
            _ => return None,
        };
        let mut key = [0; 16];
        key[0] = match node {
            2 => 2,
            _ => node as u8 + 1,
        };
        Some(Decision {
            key,
            actor,
            owner: actor,
            street: if node == 0 { 0 } else { 3 },
            code: 6,
        })
    }
    fn children(node: usize) -> [usize; 2] {
        match node {
            0 => [1, 2],
            1 => [3, 4],
            2 => [5, 6],
            5 => [7, 8],
            6 => [9, 10],
            _ => panic!("terminal"),
        }
    }
}
impl State for Toy {
    type Saved = usize;
    fn players(&self) -> usize {
        self.n
    }
    fn decision(&self) -> Option<Decision> {
        self.decision_at(self.node)
    }
    fn payoff(&self, p: usize) -> f64 {
        let v = match self.node {
            3 => 3.,
            4 => -2.,
            7 => 5.,
            8 => -3.,
            9 => -1.,
            10 => 2.,
            _ => panic!("nonterminal"),
        } * self.scale;
        if p == 0 {
            v
        } else {
            -v / (self.n - 1) as f64
        }
    }
    fn save(&self) -> usize {
        self.node
    }
    fn restore(&mut self, x: usize) {
        self.node = x;
    }
    fn apply(&mut self, a: usize) {
        self.node = Self::children(self.node)[a];
    }
}
impl probe::DiagnosticState for Toy {
    fn family(&self, _: usize) -> u8 {
        0
    }
}
struct ToyGame(usize);
impl Game for ToyGame {
    type State = Toy;
    fn players(&self) -> usize {
        self.0
    }
    fn identity(&self) -> serde_json::Value {
        serde_json::json!({"game":"perturbed-fixture","players":self.0})
    }
    fn sample(&self, rng: &mut StdRng) -> Toy {
        Toy {
            node: 0,
            n: self.0,
            scale: if rng.gen::<bool>() { 1. } else { -0.5 },
        }
    }
}
fn setup(n: usize) -> (Toy, Table) {
    let s = Toy {
        node: 0,
        n,
        scale: 1.,
    };
    let mut t = Table::default();
    for (id, p) in [
        (0, [0., 1.]),
        (1, [0.4, 0.6]),
        (5, [0.25, 0.75]),
        (6, [0.8, 0.2]),
    ] {
        let d = s.decision_at(id).unwrap();
        let mut e = Entry::new(d, 3);
        e.regrets = p.to_vec().into_boxed_slice();
        assert!(t.insert(d.key, e));
    }
    (s, t)
}
#[derive(Clone)]
struct Fixed(BTreeMap<u64, usize>);
impl Sampler<Toy> for Fixed {
    fn sample(&mut self, _: &[f64], path: u64) -> usize {
        self.0[&path]
    }
    fn pressure_draw(&mut self, _: u64) -> f64 {
        panic!("no pressure")
    }
}
fn paths(s: &Toy, node: usize, path: u64, out: &mut Vec<(usize, u64)>) {
    let Some(d) = s.decision_at(node) else { return };
    if d.actor != 0 {
        out.push((node, path));
    }
    for (a, c) in Toy::children(node).into_iter().enumerate() {
        paths(s, c, multi_cfr::child_path(path, a), out);
    }
}
fn base_and_actual(s: &Toy, t: &Table, eps: f64) -> ([f64; 2], [f64; 2]) {
    // Independent normalization, not the research policy helper.
    let d = s.decision().unwrap();
    let r = t
        .get(&d.key)
        .map(|e| e.regrets.to_vec())
        .unwrap_or(vec![0.; 2]);
    let z = r.iter().map(|x| x.max(0.)).sum::<f64>();
    let p = if z == 0. {
        [0.5, 0.5]
    } else {
        [r[0].max(0.) / z, r[1].max(0.) / z]
    };
    (
        p,
        [(1. - eps) * p[0] + eps / 2., (1. - eps) * p[1] + eps / 2.],
    )
}
#[derive(Default, Clone)]
struct Expected {
    regret: [f64; 2],
    average: [f64; 2],
}
fn oracle(
    s: &mut Toy,
    t: &Table,
    eps: f64,
    prefix: f64,
    w: f64,
    out: &mut BTreeMap<Key, Expected>,
) -> f64 {
    let Some(d) = s.decision() else {
        return s.payoff(0);
    };
    let (_p, sigma) = base_and_actual(s, t, eps);
    let saved = s.save();
    let mut v = [0.; 2];
    for a in 0..2 {
        s.apply(a);
        v[a] = oracle(
            s,
            t,
            eps,
            if d.actor == 0 {
                prefix
            } else {
                prefix * sigma[a]
            },
            w,
            out,
        );
        s.restore(saved);
    }
    let value = sigma[0] * v[0] + sigma[1] * v[1];
    let e = out.entry(d.key).or_default();
    if d.actor == 0 {
        // Explicit perturbed pure-action utilities, independent of v - pi*v formula.
        let uniform = (v[0] + v[1]) / 2.;
        for a in 0..2 {
            let pure = (1. - eps) * v[a] + eps * uniform;
            e.regret[a] += prefix * w * (pure - value);
        }
    } else {
        for a in 0..2 {
            e.average[a] += prefix * w * sigma[a];
        }
    }
    value
}
fn close(a: f64, b: f64) {
    assert!((a - b).abs() < 2e-12, "{a} != {b}");
}
fn as_table(d: Deltas) -> Table {
    let mut t = Table::default();
    t.merge_all(vec![d], false, false, false);
    t
}

#[test]
fn perturbed_action_regret_is_not_naive_floored_baseline() {
    let pi: [f64; 2] = [1., 0.];
    let v = [2., -1.];
    let eps = 0.02;
    let sigma = [0.99, 0.01];
    let value = sigma[0] * v[0] + sigma[1] * v[1];
    close(value, 1.97);
    let base = pi[0] * v[0] + pi[1] * v[1];
    close((1. - eps) * (v[0] - base), 0.);
    close((1. - eps) * (v[1] - base), -2.94);
    assert!((v[0] - value).abs() > 0.02);
}
#[test]
fn exhaustive_two_three_four_player_values_and_complete_updates() {
    for n in [2, 3, 4] {
        let (s, t) = setup(n);
        for eps in [0., 0.02, 0.3] {
            let (mut expected, mut exact) = (BTreeMap::new(), s.clone());
            let ev = oracle(&mut exact, &t, eps, 1., 3., &mut expected);
            let mut nodes = Vec::new();
            paths(&s, 0, 0, &mut nodes);
            let mut actual = BTreeMap::<Key, Expected>::new();
            let (mut probsum, mut val) = (0., 0.);
            for mask in 0..(1 << nodes.len()) {
                let mut map = BTreeMap::new();
                let mut probability = 1.;
                for (i, (node, path)) in nodes.iter().enumerate() {
                    let a = (mask >> i) & 1;
                    let mut x = s.clone();
                    x.node = *node;
                    let (_, p) = base_and_actual(&x, &t, eps);
                    probability *= p[a];
                    map.insert(*path, a);
                }
                if probability == 0. {
                    continue;
                }
                probsum += probability;
                let (mut deltas, mut counts, mut contexts) =
                    (Deltas::default(), Counts::default(), probe::Contexts::new());
                let mut x = s.clone();
                let value = probe::Walk {
                    table: &t,
                    deltas: &mut deltas,
                    counts: &mut counts,
                    sampler: Fixed(map),
                    traverser: 0,
                    weight: 3.,
                    epsilon: eps,
                    contexts: &mut contexts,
                }
                .run(&mut x);
                assert_eq!(x.node, 0);
                val += probability * value;
                for (k, d) in deltas {
                    let e = actual.entry(k).or_default();
                    for a in 0..2 {
                        e.regret[a] += probability * d.regrets()[a];
                        e.average[a] += probability * d.average().unwrap()[a];
                    }
                }
            }
            close(probsum, 1.);
            close(val, ev);
            assert_eq!(actual.len(), expected.len());
            for (k, e) in expected {
                for a in 0..2 {
                    close(actual[&k].regret[a], e.regret[a]);
                    close(actual[&k].average[a], e.average[a]);
                }
            }
        }
    }
}
#[test]
fn zero_epsilon_has_exact_fast_traversal_grouping_and_values() {
    for n in [2, 3, 4] {
        let (s, t) = setup(n);
        for who in 0..n {
            for seed in 0..32 {
                let (mut a, mut ac, mut b, mut bc, mut ctx) = (
                    Deltas::default(),
                    Counts::default(),
                    Deltas::default(),
                    Counts::default(),
                    probe::Contexts::new(),
                );
                let (mut x, mut y) = (s.clone(), s.clone());
                let av = Traversal {
                    table: &t,
                    deltas: &mut a,
                    sampler: PathSampler(seed),
                    traverser: who,
                    weight: 7.,
                    last_average_street: 3,
                    counts: &mut ac,
                    fork_depth: 1,
                    prune_below: None,
                    pressure: None,
                }
                .run(&mut x);
                let bv = probe::Walk {
                    table: &t,
                    deltas: &mut b,
                    sampler: PathSampler(seed),
                    traverser: who,
                    weight: 7.,
                    epsilon: 0.,
                    counts: &mut bc,
                    contexts: &mut ctx,
                }
                .run(&mut y);
                assert_eq!(av.to_bits(), bv.to_bits());
                assert_eq!(ac, bc);
                assert_eq!(as_table(a), as_table(b));
                assert_eq!(x.node, y.node);
            }
        }
    }
}
#[test]
fn adaptive_zero_epsilon_matches_production_roots_updates_and_freeze() {
    for n in [2, 3, 4] {
        let game = ToyGame(n);
        let mut a = Trainer::new(&game, 20261028456011, 3, 3, true);
        a.sampling = multi_cfr::Sampling::Path;
        a.roots_per_seat = 8;
        let mut b = probe::ResearchTrainer::new(20261028456011, 3, 0.);
        for _ in 0..32 {
            a.step_fast(&game);
            b.step(&game, |_, _, _, _, _| Ok(())).unwrap();
            assert_eq!(a.table, b.table);
            assert_eq!(a.counts, b.counts);
            assert_eq!(a.frozen_at, b.frozen_at);
        }
    }
}
#[test]
fn invalid_epsilon_fails_and_positive_floor_has_complete_support() {
    let (s, t) = setup(3);
    let d = s.decision().unwrap();
    let (base, p) = probe::policies(&t, d, 0.02);
    assert_eq!(base[0], 0.);
    assert!(p[..2].iter().all(|x| *x >= 0.01));
    for eps in [-0.1, 1., f64::NAN, f64::INFINITY] {
        assert!(std::panic::catch_unwind(|| probe::policies(&t, d, eps)).is_err());
    }
}

fn meta(family: u8, paths: u64, averages: u64) -> probe::RootMeta {
    probe::RootMeta {
        families: std::iter::once(family).collect(),
        regret_nonzero_paths: paths,
        regret_zero_paths: 0,
        average_paths: averages,
        regret_path_l1: 2. * paths as f64,
    }
}
fn diagnostic_delta(d: Decision, r: [f64; 2], average: bool, visits: u64) -> Deltas {
    let mut v = multi_cfr::Delta::new(d, 3);
    v.regrets_mut().copy_from_slice(&r);
    v.visits = visits;
    if average {
        v.average_mut().unwrap().copy_from_slice(&[0.5, 0.5]);
    }
    let mut all = Deltas::default();
    all.insert(d.key, v);
    all
}
fn watch_meta(keys: impl Iterator<Item = Key>) -> BTreeMap<Key, serde_json::Value> {
    keys.map(|k| (k, serde_json::json!({"families":[0]})))
        .collect()
}
#[test]
fn target_family_evidence_never_hit_and_declined_keys_stay_distinct() {
    let (s, _) = setup(3);
    let d = s.decision_at(1).unwrap();
    let mut missing = d;
    missing.key[2] = 7;
    let mut t = Table::default();
    let mut l = super::ledger::Ledger::new(watch_meta(
        [d.key, missing.key, {
            let mut k = d.key;
            k[2] = 8;
            k
        }]
        .into_iter(),
    ));
    for f in [3, 0] {
        for _ in 0..8 {
            let ds = diagnostic_delta(d, [1., -1.], true, 1);
            let mut contexts = probe::Contexts::new();
            contexts.insert(d.key, meta(f, 1, 1));
            l.observe(1., &t, &ds, &contexts, false, 0.02).unwrap();
            t.merge_all(vec![ds], false, false, false);
            l.after_merge(&t, false);
        }
        let x = l.value(&t);
        let w = x["watch"]
            .as_array()
            .unwrap()
            .iter()
            .find(|w| w["key"] == hu20_trainer::multi_checkpoint::key_hex(&d.key))
            .unwrap();
        assert_eq!(w["all_history_key_proxy"], true);
        assert_eq!(w["replicated_learning_proxy"], f == 0);
    }
    for _ in 0..8 {
        let ds = diagnostic_delta(missing, [1., -1.], true, 1);
        let mut contexts = probe::Contexts::new();
        contexts.insert(missing.key, meta(0, 1, 1));
        l.observe(1., &t, &ds, &contexts, true, 0.02).unwrap();
    }
    let x = l.value(&t);
    assert_eq!(x["watch_keys"], 3);
    assert_eq!(x["qualified_retained_watch_keys"], 1);
    let w = x["watch"]
        .as_array()
        .unwrap()
        .iter()
        .find(|w| w["key"] == hu20_trainer::multi_checkpoint::key_hex(&missing.key))
        .unwrap();
    assert_eq!(w["retained_root_groups"], 0);
    assert_eq!(w["declined_root_groups"], 8);
    assert_eq!(w["final_retained"], false);
}
#[test]
fn zero_admission_and_path_root_cancellation_are_not_positive_learning() {
    let (s, _) = setup(3);
    let d = s.decision_at(1).unwrap();
    let mut t = Table::default();
    let mut l = super::ledger::Ledger::new(watch_meta(std::iter::once(d.key)));
    let ds = diagnostic_delta(d, [0., 0.], false, 2);
    let mut contexts = probe::Contexts::new();
    contexts.insert(d.key, meta(0, 2, 0));
    l.observe(1., &t, &ds, &contexts, false, 0.02).unwrap();
    t.merge_all(vec![ds], false, false, false);
    l.after_merge(&t, false);
    let x = l.value(&t);
    assert_eq!(x["zero_at_admission"], 1);
    assert_eq!(x["fully_zero_final_rows"], 1);
    assert_eq!(x["watch"][0]["nonzero_path_but_zero_root_regret_groups"], 1);
    assert_eq!(x["qualified_retained_watch_keys"], 0);
    let ds = diagnostic_delta(d, [1., -1.], true, 1);
    contexts.insert(d.key, meta(0, 1, 1));
    l.observe(1., &t, &ds, &contexts, false, 0.02).unwrap();
    t.merge_all(vec![ds], false, false, false);
    l.after_merge(&t, false);
    let x = l.value(&t);
    assert_eq!(x["initially_zero_later_nonzero"], 1);
    assert_eq!(x["fully_zero_final_rows"], 0);
}
#[test]
fn positive_epsilon_thread_parity_includes_learning_ledger() {
    let game = ToyGame(3);
    let (_, setup) = setup(3);
    let mut results = Vec::new();
    for threads in [1, 2] {
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(threads)
            .build()
            .unwrap();
        let (mut t, mut l) = (
            probe::ResearchTrainer::new(20261028456011, 3, 0.02),
            super::ledger::Ledger::new(watch_meta(setup.keys())),
        );
        pool.install(|| {
            for _ in 0..32 {
                t.step(&game, |w, table, d, c, f| {
                    l.observe(w, table, d, c, f, 0.02)
                })
                .unwrap();
                l.after_merge(&t.table, t.frozen_at.is_some());
            }
        });
        let value = l.value(&t.table);
        results.push((t.table, t.counts, t.frozen_at, value, t.root_inventory));
    }
    assert_eq!(results[0], results[1]);
}
