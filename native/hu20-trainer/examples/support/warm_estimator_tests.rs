use super::probe;
use hu20_trainer::multi_cfr::{self, Decision, Entry, Sampler, State, Table, Traversal};
use std::collections::BTreeMap;

#[derive(Clone)]
struct Toy {
    node: usize,
    players: usize,
}
impl Toy {
    fn decision_at(&self, id: usize) -> Option<Decision> {
        let actor = match id {
            0 => 1,
            1 | 2 => 0,
            5 => self.players - 1,
            6 => 1,
            _ => return None,
        };
        let mut key = [0; 16];
        key[0] = id as u8 + 1;
        Some(Decision {
            key,
            actor,
            owner: actor,
            street: if id < 1 {
                0
            } else if id < 3 {
                2
            } else {
                3
            },
            code: (1 << 1) | (1 << 3),
        })
    }
    fn children(id: usize) -> [usize; 2] {
        match id {
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
        self.players
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
        };
        if p == 0 {
            v
        } else {
            -v
        }
    }
    fn save(&self) -> usize {
        self.node
    }
    fn restore(&mut self, v: usize) {
        self.node = v;
    }
    fn apply(&mut self, a: usize) {
        self.node = Self::children(self.node)[a];
    }
}
fn table(state: &Toy) -> Table {
    let mut t = Table::default();
    for (id, p) in [
        (0, [0., 1.]),
        (2, [0.4, 0.6]),
        (5, [0.25, 0.75]),
        (6, [0.8, 0.2]),
    ] {
        let d = state.decision_at(id).unwrap();
        let mut e = Entry::new(d, 3);
        e.regrets = p.to_vec().into_boxed_slice();
        assert!(t.insert(d.key, e));
    }
    t
}
fn opponent_paths(state: &Toy, id: usize, path: u64, v: &mut Vec<(usize, u64)>) {
    let Some(d) = state.decision_at(id) else {
        return;
    };
    if d.actor != 0 {
        v.push((id, path));
    }
    for (a, child) in Toy::children(id).into_iter().enumerate() {
        opponent_paths(state, child, multi_cfr::child_path(path, a), v);
    }
}
#[derive(Clone)]
struct Fixed(BTreeMap<u64, usize>);
impl Sampler<Toy> for Fixed {
    fn sample(&mut self, _: &[f64], path: u64) -> usize {
        self.0[&path]
    }
}
fn probability(table: &Table, state: &Toy, id: usize, action: usize, biased: bool) -> f64 {
    let d = state.decision_at(id).unwrap();
    let p = table.get(&d.key).unwrap().policy(false);
    probe::proposal(&p[..d.len()], probe::passive_index(d).unwrap(), biased).unwrap()[action]
}
fn add(to: &mut BTreeMap<[u8; 16], Vec<f64>>, key: [u8; 16], r: &[f64], a: &[f64], p: f64) {
    let out = to.entry(key).or_insert_with(|| vec![0.; r.len() + a.len()]);
    for (sum, v) in out.iter_mut().zip(r.iter().chain(a)) {
        *sum += p * v;
    }
}

/// An independent oracle executes the UNMODIFIED production Traversal under
/// every complete opponent action map. No corrected-walk formulas enter it.
#[test]
fn expected_updates_match_existing_traversal_with_warm_zeros_for_two_to_four_players() {
    for players in [2, 3, 4] {
        let state = Toy { node: 0, players };
        let table = table(&state);
        let mut paths = Vec::new();
        opponent_paths(&state, 0, 0, &mut paths);
        let mut expected = BTreeMap::new();
        let mut actual = BTreeMap::new();
        let mut expected_value = 0.;
        let mut actual_value = 0.;
        let mut total = [0., 0.];
        for bits in 0..(1 << paths.len()) {
            let choices = paths
                .iter()
                .enumerate()
                .map(|(i, (_, path))| (*path, (bits >> i) & 1))
                .collect::<BTreeMap<_, _>>();
            let probs = [false, true].map(|biased| {
                paths
                    .iter()
                    .enumerate()
                    .map(|(i, (id, _))| probability(&table, &state, *id, (bits >> i) & 1, biased))
                    .product::<f64>()
            });
            total[0] += probs[0];
            total[1] += probs[1];
            if probs[0] > 0. {
                let mut s = state.clone();
                let mut deltas = multi_cfr::Deltas::default();
                let mut counts = multi_cfr::Counts::default();
                let v = Traversal {
                    table: &table,
                    deltas: &mut deltas,
                    sampler: Fixed(choices.clone()),
                    traverser: 0,
                    weight: 3.,
                    last_average_street: 3,
                    counts: &mut counts,
                    fork_depth: 0,
                    prune_below: None,
                }
                .run(&mut s);
                expected_value += probs[0] * v;
                assert_eq!(s.node, 0);
                for (k, d) in deltas {
                    add(
                        &mut expected,
                        k,
                        d.regrets(),
                        d.average().unwrap(),
                        probs[0],
                    );
                }
            }
            if probs[1] > 0. {
                let mut s = state.clone();
                let mut draw = |_: &[f64], path: u64| choices[&path];
                let r = probe::run(&table, &mut s, 0, true, 3., &mut draw, &|_, _| {
                    "fixture".into()
                })
                .unwrap();
                actual_value += probs[1] * r.value;
                assert_eq!(s.node, 0);
                for (k, d) in r.increments {
                    add(&mut actual, k, &d.regret, &d.average, probs[1]);
                }
            }
        }
        for t in total {
            assert!((t - 1.).abs() < 1e-14);
        }
        assert!((expected_value - actual_value).abs() < 1e-12);
        for (k, v) in &actual {
            let e = expected
                .get(k)
                .cloned()
                .unwrap_or_else(|| vec![0.; v.len()]);
            for (a, b) in v.iter().zip(e) {
                assert!((a - b).abs() < 1e-12, "key {k:?}: {a} != {b}");
            }
        }
        for k in expected.keys() {
            assert!(actual.contains_key(k));
        }
    }
}

#[test]
fn zero_prefix_is_not_reset_at_missing_hero_row() {
    let mut s = Toy {
        node: 0,
        players: 4,
    };
    let t = table(&s);
    let mut draw = |_: &[f64], _: u64| 0;
    let root = probe::run(&t, &mut s, 0, true, 7., &mut draw, &|_, _| "P0".into()).unwrap();
    let d = s.decision_at(1).unwrap();
    let i = &root.increments[&d.key];
    assert!(i.missing);
    assert!(i.regret.iter().chain(&i.average).all(|v| *v == 0.));
    assert_eq!(i.regret_coeff.zero, 1);
    assert_eq!(root.first_zero[0]["sigma"], 0.);
    assert_eq!(s.node, 0);
}
fn zero_root() -> probe::Root {
    let mut s = Toy {
        node: 0,
        players: 4,
    };
    let t = table(&s);
    probe::run(
        &t,
        &mut s,
        0,
        true,
        1.,
        &mut |_: &[f64], _: u64| 0,
        &|_, _| "P0".into(),
    )
    .unwrap()
}
fn positive_root(key: [u8; 16]) -> probe::Root {
    let mut root = zero_root();
    let mut inc = root
        .increments
        .remove(&[2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        .unwrap();
    inc.key = key;
    inc.regret = vec![1., -1.];
    inc.average = vec![1., 0.];
    inc.regret_coeff = probe::Moments::default();
    inc.regret_coeff.add(1.).unwrap();
    inc.average_coeff = inc.regret_coeff.clone();
    inc.regret_linear_coeff = inc.regret_coeff.clone();
    inc.average_linear_coeff = inc.regret_coeff.clone();
    root.increments.clear();
    root.increments.insert(key, inc);
    root
}
#[test]
fn admission_uses_whole_batch_and_does_not_call_first_root_zero_capacity_waste() {
    let key = [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    let mut shadow = probe::Shadow::new(1, &BTreeMap::new()).unwrap();
    shadow.batch(&[zero_root(), positive_root(key)]).unwrap();
    assert_eq!(shadow.summary()["zero_at_admission"], 0);
    assert_eq!(shadow.summary()["zero_end"], 0);
    assert_eq!(shadow.frozen, Some(1));
}
#[test]
fn zero_rows_can_fill_shadow_cap_but_existing_rows_still_learn_after_freeze() {
    let key = [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    let other = [99; 16];
    let never = [100; 16];
    let mut shadow = probe::Shadow::new(1, &BTreeMap::from([(other, 2), (never, 3)])).unwrap();
    shadow.batch(&[zero_root()]).unwrap();
    assert_eq!(shadow.summary()["zero_end"], 1);
    shadow
        .batch(&[positive_root(key), positive_root(other)])
        .unwrap();
    assert_eq!(shadow.summary()["zero_at_admission_later_positive"], 1);
    assert!(shadow.rows[&other].potential.zero() == false);
    assert!(shadow.rows[&other].retained.zero());
    assert!(shadow.rows[&other].admitted.is_none());
    assert!(shadow.rows[&never].first_batch.is_none());
}
#[test]
fn passive_menu_mapping_and_zero_underflow_are_distinct() {
    let d = Decision {
        key: [0; 16],
        actor: 0,
        owner: 0,
        street: 0,
        code: (1 << 0) | (1 << 2) | (1 << 3),
    };
    assert_eq!(probe::passive_index(d).unwrap(), 1);
    assert_eq!(probe::product(0., 1e-200).unwrap(), 0.);
    assert!(probe::product(1e-200, 1e-200)
        .unwrap_err()
        .contains("underflow"));
    let q = probe::proposal(&[0.8, 0.2, 0.], 1, true).unwrap();
    assert!((q[0] - 0.6).abs() < 1e-14);
    assert!((q[1] - 0.4).abs() < 1e-14);
    assert_eq!(q[2], 0.);
    let mut m = probe::Moments::default();
    for w in [0., 1., 1., 1., 1.] {
        m.add(w).unwrap();
    }
    assert_eq!(m.ess(), 4.);
    assert_eq!(m.zero, 1);
}

#[test]
fn reference_mode_is_bitwise_equal_to_existing_traversal_for_supported_draws() {
    let state = Toy {
        node: 0,
        players: 4,
    };
    let table = table(&state);
    let mut paths = Vec::new();
    opponent_paths(&state, 0, 0, &mut paths);
    for bits in 0..(1 << paths.len()) {
        if paths
            .iter()
            .enumerate()
            .any(|(i, (id, _))| probability(&table, &state, *id, (bits >> i) & 1, false) == 0.)
        {
            continue;
        }
        let choices = paths
            .iter()
            .enumerate()
            .map(|(i, (_, path))| (*path, (bits >> i) & 1))
            .collect::<BTreeMap<_, _>>();
        let mut s = state.clone();
        let mut deltas = multi_cfr::Deltas::default();
        let mut counts = multi_cfr::Counts::default();
        let old = Traversal {
            table: &table,
            deltas: &mut deltas,
            sampler: Fixed(choices.clone()),
            traverser: 0,
            weight: 7.,
            last_average_street: 3,
            counts: &mut counts,
            fork_depth: 0,
            prune_below: None,
        }
        .run(&mut s);
        let root = probe::run(
            &table,
            &mut s,
            0,
            false,
            7.,
            &mut |_: &[f64], p: u64| choices[&p],
            &|_, _| "fixture".into(),
        )
        .unwrap();
        assert_eq!(old.to_bits(), root.value.to_bits());
        assert_eq!(deltas.len(), root.increments.len());
        for (k, d) in deltas {
            let r = &root.increments[&k];
            for (a, b) in d
                .regrets()
                .iter()
                .chain(d.average().unwrap())
                .zip(r.regret.iter().chain(&r.average))
            {
                assert_eq!(a.to_bits(), b.to_bits());
            }
        }
    }
}

#[test]
fn traverser_zero_probability_does_not_zero_counterfactual_updates() {
    let mut state = Toy {
        node: 0,
        players: 4,
    };
    let original = table(&state);
    let mut table = Table::default();
    let d = state.decision_at(2).unwrap();
    for (key, stored) in original.iter() {
        let decision = state.decision_at((key[0] - 1) as usize).unwrap();
        let mut entry = Entry::new(decision, 3);
        entry.regrets = if key == d.key {
            vec![0., 1.].into_boxed_slice()
        } else {
            stored.regrets.into()
        };
        table.insert(key, entry);
    }
    let root_path = 0;
    let mut draw = |_: &[f64], path: u64| if path == root_path { 1 } else { 0 };
    let root = probe::run(&table, &mut state, 0, true, 1., &mut draw, &|_, _| {
        "fixture".into()
    })
    .unwrap();
    let key = state.decision_at(5).unwrap().key;
    assert!(root.increments[&key].average.iter().sum::<f64>() > 0.);
    assert_eq!(
        root.metrics["terminal_root_value_coefficient_with_own_reach"].zero,
        1
    );
}

#[test]
fn root_order_and_ledgers_match_across_one_two_eight_sixteen_threads() {
    use rayon::prelude::*;
    let make = |threads| {
        rayon::ThreadPoolBuilder::new()
            .num_threads(threads)
            .build()
            .unwrap()
            .install(|| {
                (0..32usize)
                    .into_par_iter()
                    .map(|i| {
                        let mut state = Toy {
                            node: 0,
                            players: 4,
                        };
                        let table = table(&state);
                        let mut sampler = multi_cfr::PathSampler(i as u64 + 100);
                        probe::run(
                            &table,
                            &mut state,
                            i % 4,
                            true,
                            7.,
                            &mut |p: &[f64], path: u64| {
                                <multi_cfr::PathSampler as Sampler<Toy>>::sample(
                                    &mut sampler,
                                    p,
                                    path,
                                )
                            },
                            &|_, _| "fixture".into(),
                        )
                        .unwrap()
                    })
                    .collect::<Vec<_>>()
            })
    };
    let expected = make(1);
    let mut shadow = probe::Shadow::new(1, &BTreeMap::new()).unwrap();
    shadow.batch(&expected).unwrap();
    for threads in [2, 8, 16] {
        let actual = make(threads);
        assert_eq!(
            expected.iter().map(probe::Root::value).collect::<Vec<_>>(),
            actual.iter().map(probe::Root::value).collect::<Vec<_>>()
        );
        let mut other = probe::Shadow::new(1, &BTreeMap::new()).unwrap();
        other.batch(&actual).unwrap();
        assert_eq!(shadow.summary(), other.summary());
        assert_eq!(
            shadow
                .rows
                .iter()
                .map(|(k, v)| v.value(k))
                .collect::<Vec<_>>(),
            other
                .rows
                .iter()
                .map(|(k, v)| v.value(k))
                .collect::<Vec<_>>()
        );
    }
}

#[test]
fn ties_are_zero_updates_despite_positive_weight() {
    #[derive(Clone)]
    struct Tied(Toy);
    impl State for Tied {
        type Saved = usize;
        fn players(&self) -> usize {
            self.0.players()
        }
        fn decision(&self) -> Option<Decision> {
            self.0.decision()
        }
        fn payoff(&self, _: usize) -> f64 {
            0.
        }
        fn save(&self) -> usize {
            self.0.save()
        }
        fn restore(&mut self, s: usize) {
            self.0.restore(s)
        }
        fn apply(&mut self, a: usize) {
            self.0.apply(a)
        }
    }
    let mut s = Tied(Toy {
        node: 0,
        players: 4,
    });
    let t = table(&s.0);
    let r = probe::run(
        &t,
        &mut s,
        0,
        true,
        1.,
        &mut |_: &[f64], _: u64| 1,
        &|_, _| "fixture".into(),
    )
    .unwrap();
    let inc = &r.increments[&s.0.decision_at(2).unwrap().key];
    assert!(inc.regret_coeff.sum > 0.);
    assert!(inc.regret.iter().all(|v| *v == 0.));
    assert_eq!(
        r.metrics["street2:fixture:all_estimated_action_values_tied"].sum,
        1.
    );
}

#[test]
fn normalized_policy_underflow_is_not_reported_as_structural_zero() {
    let state = Toy {
        node: 0,
        players: 4,
    };
    let d = state.decision().unwrap();
    let mut e = Entry::new(d, 3);
    e.regrets = vec![f64::from_bits(1), 1e100].into_boxed_slice();
    let mut table = Table::default();
    table.insert(d.key, e);
    assert!(probe::frozen_sigma(&table, d)
        .unwrap_err()
        .contains("normalization underflow"));
}

#[test]
fn watched_tied_updates_keep_unconditional_positive_coefficients() {
    let key = [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    let never = [100; 16];
    let mut root = positive_root(key);
    let i = root.increments.get_mut(&key).unwrap();
    i.regret.fill(0.);
    i.average.fill(0.);
    i.average_coeff = probe::Moments::default();
    i.average_linear_coeff = probe::Moments::default();
    let mut shadow = probe::Shadow::new(100, &BTreeMap::from([(key, 2), (never, 3)])).unwrap();
    shadow.batch(&[root]).unwrap();
    let p = shadow.rows[&key].value(&key)["potential"].clone();
    assert_eq!(p["regret_event_coeff"]["sum"], 1.);
    assert_eq!(p["regret_root_coeff"]["sum"], 1.);
    assert_eq!(p["regret_linear_root_coeff"]["sum"], 1.);
    assert_eq!(p["nonzero_regret_update_root_coeff"]["sum"], 0.);
    assert_eq!(p["zero_update_with_positive_coefficient"], true);
    assert_eq!(p["encountered_only_zero_coefficient"], false);
    assert_eq!(
        shadow.rows[&never].value(&never)["potential"]["never_encountered"],
        true
    );
}

#[test]
fn terminal_ess_groups_correlated_branches_and_keeps_linear_weights() {
    let mut first = probe::Root::default();
    let mut second = probe::Root::default();
    for (name, left, right) in [
        (
            "terminal_counterfactual_coefficient",
            vec![1., 1.],
            vec![2.],
        ),
        (
            "linear_terminal_counterfactual_coefficient",
            vec![7., 7.],
            vec![14.],
        ),
        (
            "terminal_root_value_coefficient_with_own_reach",
            vec![0.5, 0.5],
            vec![1.],
        ),
        (
            "linear_terminal_root_value_coefficient_with_own_reach",
            vec![3.5, 3.5],
            vec![7.],
        ),
    ] {
        for value in left {
            first
                .metrics
                .entry(name.into())
                .or_default()
                .add(value)
                .unwrap();
        }
        for value in right {
            second
                .metrics
                .entry(name.into())
                .or_default()
                .add(value)
                .unwrap();
        }
    }
    second
        .metrics
        .entry("late_group".into())
        .or_default()
        .add(1.)
        .unwrap();
    let mut shadow = probe::Shadow::new(100, &BTreeMap::new()).unwrap();
    shadow
        .batch(&[first, second, probe::Root::default()])
        .unwrap();
    let s = shadow.summary();
    assert!(
        (s["metrics"]["terminal_counterfactual_coefficient"]["ess"]
            .as_f64()
            .unwrap()
            - 8. / 3.)
            .abs()
            < 1e-14
    );
    for name in [
        "terminal_counterfactual_coefficient",
        "linear_terminal_counterfactual_coefficient",
        "terminal_root_value_coefficient_with_own_reach",
        "linear_terminal_root_value_coefficient_with_own_reach",
    ] {
        let m = &s["root_grouped_metrics"][name];
        assert_eq!(m["events"], 3);
        assert_eq!(m["exact_zero"], 1);
        assert!((m["ess"].as_f64().unwrap() - 2.).abs() < 1e-14);
    }
    assert_eq!(s["root_grouped_metrics"]["late_group"]["events"], 3);
    assert_eq!(s["root_grouped_metrics"]["late_group"]["exact_zero"], 2);
}
