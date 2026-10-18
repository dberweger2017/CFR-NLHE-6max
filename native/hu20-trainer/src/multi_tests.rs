use crate::multi_cfr::*;
use crate::small_exact::Tree;
use crate::small_games::{published_kuhn_policy, Kind, SmallGame};
use rand::RngCore;

#[test]
fn published_kuhn_family_and_an_exploitable_control() {
    let game = SmallGame::new(Kind::Kuhn, 3);
    let tree = Tree::new(game, 1000);
    assert_eq!((tree.nodes(), tree.infos.len()), (600, 48));
    for beta in [0., 0.0625, 0.125, 0.25] {
        let profile = tree
            .infos
            .iter()
            .map(|i| published_kuhn_policy(&i.example, beta))
            .collect::<Vec<_>>();
        let e = tree.evaluate(&profile);
        assert!(e.gains.iter().all(|g| g.abs() < 1e-12));
        for (a, b) in e
            .values
            .iter()
            .zip([-(0.5 + beta) / 24., -0.5 / 24., (1. + beta) / 24.])
        {
            assert!((a - b).abs() < 1e-12);
        }
    }
    let e = tree.evaluate(&tree.profile(&Table::default(), false));
    assert!(e.gains.iter().all(|g| *g > 0.1));
}

#[test]
fn all_player_counts_restore_and_conserve() {
    for n in 2..=6 {
        for kind in [Kind::Kuhn, Kind::Leduc] {
            let game = SmallGame::new(kind, n);
            for seed in 0..20 {
                use rand::SeedableRng;
                let mut rng = rand::rngs::StdRng::seed_from_u64(seed);
                let mut hand = game.sample(&mut rng);
                while let Some(d) = hand.decision() {
                    for a in 0..d.len() {
                        let saved = hand.save();
                        hand.apply(a);
                        let child = hand;
                        hand.restore(saved);
                        assert_eq!(hand, saved);
                        hand.apply(a);
                        assert_eq!(hand, child);
                        hand.restore(saved);
                    }
                    use rand::Rng;
                    hand.apply(rng.gen_range(0..d.len()));
                }
                assert!((0..n).map(|p| hand.payoff(p)).sum::<f64>().abs() < 1e-12);
            }
        }
    }
}

#[test]
fn hidden_private_and_future_public_cards_never_enter_small_keys() {
    let game = SmallGame::new(Kind::Leduc, 3);
    let mut a = game.from_cards(&[0, 1, 2, 3]);
    let mut b = game.from_cards(&[0, 3, 1, 2]);
    assert_eq!(a.decision(), b.decision());
    for _ in 0..3 {
        a.play(1);
        b.play(1);
    }
    assert_ne!(a.decision(), b.decision(), "board is now public");
    let mut c = game.from_cards(&[0, 2, 1, 3]);
    for _ in 0..3 {
        c.play(1);
    }
    assert_eq!(
        a.decision(),
        c.decision(),
        "opponents remain private after the reveal"
    );
}

#[test]
fn resume_matches_complete_bytes_and_frozen_membership() {
    let game = SmallGame::new(Kind::Leduc, 3);
    use crate::gz::Gzip;
    for (freeze, street, gzip) in [false, true].into_iter()
        .flat_map(|f| [0, 3].into_iter().flat_map(move |s| [Gzip::Compatible, Gzip::Parallel].map(|g| (f, s, g))))
    {
        {
            let cap = if freeze { 30 } else { usize::MAX };
            let mut fresh = Trainer::new(&game, 71, street, cap, freeze);
            let mut prefix = fresh.clone();
            for _ in 0..20 {
                prefix.step(&game);
            }
            let path = std::env::temp_dir()
                .join(format!("multi-{}-{freeze}-{street}-{gzip:?}.gz", std::process::id()));
            // A resume from a gzip-member checkpoint equals one from a single stream.
            crate::multi_checkpoint::save(&prefix, &path, gzip).unwrap();
            let mut resumed = crate::multi_checkpoint::load(&path).unwrap();
            let frozen_keys: std::collections::HashSet<_> = resumed.table.keys().collect();
            for _ in 0..40 {
                fresh.step(&game);
            }
            for _ in 20..40 {
                resumed.step(&game);
            }
            assert_eq!(fresh.table, resumed.table);
            assert_eq!(fresh.counts, resumed.counts);
            crate::multi_checkpoint::save(&fresh, &path, Gzip::Compatible).unwrap();
            let bytes = std::fs::read(&path).unwrap();
            crate::multi_checkpoint::save(&resumed, &path, Gzip::Compatible).unwrap();
            assert_eq!(bytes, std::fs::read(&path).unwrap());
            std::fs::remove_file(&path).unwrap();
            assert!(fresh.counts.traverser[..3].iter().all(|&n| n > 0));
            if freeze {
                assert_eq!(frozen_keys, fresh.table.keys().collect());
                assert!(fresh.counts.discarded_keys > 0 && fresh.counts.discarded_visits > 0);
            }
            for e in fresh.table.values() {
                assert_eq!(e.average.is_some(), e.street as usize <= street);
            }
        }
    }
}

struct Tape {
    bits: usize,
    used: usize,
}
impl RngCore for Tape {
    fn next_u64(&mut self) -> u64 {
        assert!(self.used < 8, "increase exact sampling tape support");
        let bit = (self.bits >> self.used) & 1;
        self.used += 1;
        if bit == 0 {
            0
        } else {
            u64::MAX
        }
    }
    fn next_u32(&mut self) -> u32 {
        self.next_u64() as u32
    }
    fn fill_bytes(&mut self, _: &mut [u8]) {
        unreachable!()
    }
    fn try_fill_bytes(&mut self, _: &mut [u8]) -> Result<(), rand::Error> {
        unreachable!()
    }
}

#[test]
fn exhaustive_sample_expectation_equals_full_tree_counterfactual_updates() {
    fn full(
        hand: crate::small_games::Hand,
        player: usize,
        reach: f64,
        expected: &mut Deltas,
    ) -> f64 {
        let Some(d) = hand.decision() else {
            return hand.payoff(player);
        };
        let mut values = Vec::new();
        for a in 0..d.len() {
            let mut child = hand;
            child.apply(a);
            values.push(full(
                child,
                player,
                reach * if d.actor == player { 1. } else { 0.5 },
                expected,
            ));
        }
        let v = values.iter().sum::<f64>() / 2.;
        let e = expected.entry(d.key).or_insert_with(|| Delta::new(d, 3));
        if d.actor == player {
            for (r, value) in e.regrets_mut().iter_mut().zip(values) {
                *r += 3. * reach * (value - v);
            }
        } else {
            for a in e.average_mut().unwrap().iter_mut() {
                *a += 3. * reach * 0.5;
            }
        }
        v
    }
    let game = SmallGame::new(Kind::Kuhn, 3);
    for player in 0..3 {
        let mut expected = Deltas::default();
        let mut actual: HashMap<[u8; 16], ([f64; 2], [f64; 2])> = HashMap::new();
        for (hand, p) in game.deals() {
            full(hand, player, p, &mut expected);
            for bits in 0..256 {
                let mut state = hand;
                let mut deltas = Deltas::default();
                let mut counts = Counts::default();
                let mut rng = Tape { bits, used: 0 };
                Traversal {
                    table: &Table::default(),
                    deltas: &mut deltas,
                    sampler: Stream(&mut rng),
                    traverser: player,
                    weight: 3.,
                    last_average_street: 3,
                    counts: &mut counts,
                    fork_depth: 0,
                    prune_below: None,
                }
                .run(&mut state);
                assert_eq!(state, hand);
                for (key, e) in deltas {
                    let a = actual.entry(key).or_insert(([0.; 2], [0.; 2]));
                    for i in 0..2 {
                        a.0[i] += p * e.regrets()[i] / 256.;
                        a.1[i] += p * e.average().unwrap()[i] / 256.;
                    }
                }
            }
        }
        for (key, e) in expected {
            let (regrets, average) = actual[&key];
            for i in 0..2 {
                assert!((regrets[i] - e.regrets()[i]).abs() < 1e-11);
                assert!((average[i] - e.average().unwrap()[i]).abs() < 1e-11);
            }
        }
    }
}
use std::collections::HashMap;

#[test]
fn corrupt_checkpoint_metadata_and_accumulators_are_rejected() {
    use std::io::{Read, Write};
    let game = SmallGame::new(Kind::Kuhn, 3);
    let mut trainer = Trainer::new(&game, 23, 3, usize::MAX, false);
    for _ in 0..5 {
        trainer.step(&game);
    }
    let path = std::env::temp_dir().join(format!("multi-invalid-{}.gz", std::process::id()));
    crate::multi_checkpoint::save(&trainer, &path, crate::gz::Gzip::Compatible).unwrap();
    let mut plain = String::new();
    flate2::read::MultiGzDecoder::new(std::fs::File::open(&path).unwrap())
        .read_to_string(&mut plain)
        .unwrap();
    let original: Vec<serde_json::Value> = plain
        .lines()
        .map(|line| serde_json::from_str(line).unwrap())
        .collect();
    for case in 0..8 {
        let mut records = original.clone();
        match case {
            0 => records[0]["players"] = serde_json::json!(2),
            1 => records[0]["counts"]["nodes"] = serde_json::json!(0),
            2 => records[1][1] = serde_json::json!(6),
            3 => records[1][3] = serde_json::json!(0),
            4 => records[1][5] = serde_json::json!([null, null]),
            5 => records[1][6] = serde_json::json!([-1., 1.]),
            6 => records.push(records[1].clone()),
            7 => records[0]["frozen_at"] = serde_json::json!(1),
            _ => unreachable!(),
        }
        let mut out = flate2::write::GzEncoder::new(
            std::fs::File::create(&path).unwrap(),
            flate2::Compression::default(),
        );
        for record in records {
            writeln!(out, "{record}").unwrap();
        }
        out.finish().unwrap();
        assert!(
            crate::multi_checkpoint::load(&path).is_err(),
            "corruption case {case}"
        );
    }
    std::fs::remove_file(path).unwrap();
}

fn checkpoint_bytes(trainer: &Trainer, name: &str) -> Vec<u8> {
    let path = std::env::temp_dir().join(format!("multi-fast-{}-{name}.gz", std::process::id()));
    crate::multi_checkpoint::save(trainer, &path, crate::gz::Gzip::Compatible).unwrap();
    let bytes = std::fs::read(&path).unwrap();
    std::fs::remove_file(path).unwrap();
    bytes
}

fn fast_trainer(game: &SmallGame, steps: usize, threads: usize) -> Trainer {
    fast_roots(game, steps, threads, 1)
}

fn fast_roots(game: &SmallGame, steps: usize, threads: usize, roots_per_seat: usize) -> Trainer {
    fast_seeded(game, 31, steps, threads, roots_per_seat)
}

fn fast_seeded(game: &SmallGame, seed: u64, steps: usize, threads: usize, roots_per_seat: usize) -> Trainer {
    let mut t = Trainer { sampling: Sampling::Path, roots_per_seat, ..Trainer::new(game, seed, 3, usize::MAX, false) };
    let pool = rayon::ThreadPoolBuilder::new().num_threads(threads).build().unwrap();
    pool.install(|| (0..steps).for_each(|_| t.step_fast(game)));
    t
}

#[test]
fn fast_mode_is_identical_for_every_thread_count() {
    for (kind, n, roots) in [(Kind::Kuhn, 3, 1), (Kind::Leduc, 3, 1), (Kind::Leduc, 4, 1), (Kind::Leduc, 3, 5)] {
        let game = SmallGame::new(kind, n);
        let one = fast_roots(&game, 40, 1, roots);
        let bytes = checkpoint_bytes(&one, "one");
        for threads in [2, 4, 8, 16] {
            let many = fast_roots(&game, 40, threads, roots);
            assert_eq!(one.counts, many.counts, "{kind:?} {n} roots {roots} threads {threads}");
            assert!(bytes == checkpoint_bytes(&many, "many"), "{kind:?} {n} roots {roots} threads {threads}");
        }
    }
}

#[test]
fn fast_roots_have_their_own_deals_and_draws() {
    use rand::RngCore;
    let game = SmallGame::new(Kind::Leduc, 3);
    let mut t = fast_roots(&game, 3, 1, 4);
    t.iteration += 1;
    for player in 0..3 {
        // Root 0 deals the production deal of the same seat and iteration.
        let (mut first, _) = t.fast_root(player, 0);
        assert_eq!(first.next_u64(), t.root(player, b"nplayer-external-sampling-v1").next_u64());
        let roots: Vec<(u64, u64)> = (0..4).map(|r| { let (mut deal, seed) = t.fast_root(player, r); (deal.next_u64(), seed) }).collect();
        for a in 0..4 {
            for b in a + 1..4 {
                assert!(roots[a].0 != roots[b].0 && roots[a].1 != roots[b].1, "player {player} roots {a} {b}");
            }
        }
        let other = t.fast_root((player + 1) % 3, 1);
        assert!(roots[1].1 != other.1, "seats do not share draws");
    }
}

#[test]
fn fast_resume_is_exact_and_keeps_its_sampling() {
    let game = SmallGame::new(Kind::Leduc, 3);
    let mut prefix = fast_roots(&game, 20, 4, 3);
    let path = std::env::temp_dir().join(format!("multi-fast-resume-{}.gz", std::process::id()));
    crate::multi_checkpoint::save(&prefix, &path, crate::gz::Gzip::Parallel).unwrap();
    let mut resumed = crate::multi_checkpoint::load(&path).unwrap();
    assert_eq!((resumed.sampling, resumed.roots_per_seat), (Sampling::Path, 3));
    for _ in 0..20 {
        resumed.step_fast(&game);
        prefix.step_fast(&game);
    }
    assert!(checkpoint_bytes(&prefix, "a") == checkpoint_bytes(&resumed, "b"));
    assert!(checkpoint_bytes(&fast_roots(&game, 40, 2, 3), "c") == checkpoint_bytes(&resumed, "b"));
    // Roots per seat belong to fast checkpoints only.
    let text = std::io::read_to_string(flate2::read::MultiGzDecoder::new(std::fs::File::open(&path).unwrap())).unwrap();
    for (from, to) in [(r#""sampling":"path-v1","#, ""), (r#""roots_per_seat":3"#, r#""roots_per_seat":0"#)] {
        assert!(text.contains(from), "{from}");
        let bad = std::env::temp_dir().join(format!("multi-fast-bad-{}.gz", std::process::id()));
        let mut out = flate2::write::GzEncoder::new(std::fs::File::create(&bad).unwrap(), flate2::Compression::default());
        std::io::Write::write_all(&mut out, text.replacen(from, to, 1).as_bytes()).unwrap();
        out.finish().unwrap();
        assert!(crate::multi_checkpoint::load(&bad).is_err(), "{from} -> {to}");
        std::fs::remove_file(bad).unwrap();
    }
    std::fs::remove_file(&path).unwrap();
    let production = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| resumed.clone().step(&game)));
    assert!(production.is_err(), "a fast checkpoint cannot continue with the production recipe");
    for (sampling, roots) in [(Sampling::Path, 0), (Sampling::Path, 1025), (Sampling::Stream, 2)] {
        let mut bad = Trainer { sampling, roots_per_seat: roots, ..Trainer::new(&game, 31, 3, usize::MAX, false) };
        let step = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| match sampling {
            Sampling::Path => bad.step_fast(&game),
            Sampling::Stream => bad.step(&game),
        }));
        assert!(step.is_err(), "{sampling:?} with {roots} roots per seat");
    }
}

#[test]
fn forks_change_only_the_order_deltas_are_summed() {
    let game = SmallGame::new(Kind::Leduc, 3);
    let trained = fast_trainer(&game, 30, 4);
    for seed in 0..40u64 {
        use rand::SeedableRng;
        let deal = game.sample(&mut rand::rngs::StdRng::seed_from_u64(seed));
        let run = |fork_depth| {
            let (mut deltas, mut counts) = (Deltas::default(), Counts::default());
            let mut state = deal;
            let value = Traversal { table: &trained.table, deltas: &mut deltas, sampler: PathSampler(seed), traverser: (seed % 3) as usize,
                weight: 31., last_average_street: 3, counts: &mut counts, fork_depth, prune_below: None }.run(&mut state);
            (value, deltas, counts)
        };
        let (v0, d0, c0) = run(0);
        let (v2, d2, c2) = run(FORK_DEPTH + 2);
        assert_eq!(c0, c2, "same nodes: the same draws");
        assert!((v0 - v2).abs() <= 1e-12 * v0.abs().max(1.));
        assert_eq!(d0.len(), d2.len());
        for (key, a) in &d0 {
            let b = &d2[key];
            assert_eq!((a.visits, a.code), (b.visits, b.code));
            let close = |x: &f64, y: &f64| (x - y).abs() <= 1e-9 * x.abs().max(1.);
            assert!(a.regrets().iter().zip(b.regrets()).all(|(x, y)| close(x, y)));
            assert!(a.average().into_iter().flatten().zip(b.average().into_iter().flatten()).all(|(x, y)| close(x, y)));
        }
    }
}

#[test]
fn path_draws_follow_the_policy() {
    let policy = [0.5, 0.0, 0.2, 0.3];
    let mut counts = [0usize; 4];
    let draws = 200_000;
    for i in 0..draws {
        let mut sampler = PathSampler(i as u64 / 64);
        let action = <PathSampler as Sampler<crate::small_games::Hand>>::sample(&mut sampler, &policy, child_path(0, i % 64));
        counts[action] += 1;
    }
    assert_eq!(counts[1], 0, "zero probability is never drawn");
    for (c, p) in counts.iter().zip(policy) {
        let expected = p * draws as f64;
        // Six binomial standard deviations.
        assert!((*c as f64 - expected).abs() <= 6. * (expected * (1. - p)).sqrt() + 1., "{counts:?}");
    }
}

#[test]
fn fast_mode_converges_like_the_production_recipe() {
    // One seed is too noisy to compare recipes; compare means over eight.
    const SEEDS: u64 = 8;
    for (kind, iterations) in [(Kind::Kuhn, 20_000), (Kind::Leduc, 2_000)] {
        let game = SmallGame::new(kind, 3);
        let tree = Tree::new(game, 10_000_000);
        let gain = |t: &Trainer| tree.evaluate(&tree.profile(&t.table, true)).gains.iter().fold(0f64, |m, g| m.max(*g));
        let (mut p, mut f, mut r) = (0., 0., 0.);
        for seed in 1..=SEEDS {
            let mut production = Trainer::new(&game, seed, 3, usize::MAX, false);
            (0..iterations).for_each(|_| production.step(&game));
            p += gain(&production) / SEEDS as f64;
            f += gain(&fast_seeded(&game, seed, iterations, 8, 1)) / SEEDS as f64;
            // Four roots per seat at equal nodes: a quarter of the iterations.
            r += gain(&fast_seeded(&game, seed, iterations / 4, 8, 4)) / SEEDS as f64;
        }
        eprintln!("{kind:?} 3 players, {iterations} iterations, mean largest best-response gain over {SEEDS} seeds: production {p:.5}, fast {f:.5}, fast 4 roots {r:.5}");
        assert!(f < 1.25 * p, "{kind:?}: fast {f} against production {p}");
        assert!(r < 1.25 * p, "{kind:?}: fast with 4 roots {r} against production {p}");
    }
}

fn rows_text(trainer: &Trainer) -> String {
    let path = std::env::temp_dir().join(format!("multi-rows-{}-{}.gz", std::process::id(), trainer.iteration));
    crate::multi_checkpoint::save(trainer, &path, crate::gz::Gzip::Compatible).unwrap();
    let text = std::io::read_to_string(flate2::read::MultiGzDecoder::new(std::fs::File::open(&path).unwrap())).unwrap();
    std::fs::remove_file(path).unwrap();
    text.split_once('\n').unwrap().1.to_string()
}

fn pruned_trainer(game: &SmallGame, seed: u64, steps: usize, threads: usize, prune: Option<Prune>) -> Trainer {
    let mut t = Trainer { sampling: Sampling::Path, roots_per_seat: 2, prune, ..Trainer::new(game, seed, 3, usize::MAX, false) };
    let pool = rayon::ThreadPoolBuilder::new().num_threads(threads).build().unwrap();
    pool.install(|| (0..steps).for_each(|_| t.step_fast(game)));
    t
}

#[test]
fn pruning_that_never_triggers_changes_no_row() {
    let game = SmallGame::new(Kind::Leduc, 3);
    let plain = pruned_trainer(&game, 5, 60, 4, None);
    let unreachable = pruned_trainer(&game, 5, 60, 4, Some(Prune { bb: 1e300, after: 0 }));
    assert_eq!(unreachable.counts.pruned, 0);
    assert!(rows_text(&plain) == rows_text(&unreachable));
    assert_eq!(plain.counts, unreachable.counts);
}

#[test]
fn pruning_keeps_node_values_and_the_other_updates_bit_identical() {
    let game = SmallGame::new(Kind::Leduc, 3);
    let trained = pruned_trainer(&game, 7, 300, 4, None);
    let mut total = 0;
    // Fork depth 0 skips in the unforked loop only; depth 4 also in forked children.
    for (seed, fork_depth) in (0..60u64).flat_map(|s| [(s, 0u8), (s, 4)]) {
        use rand::SeedableRng;
        let deal = game.sample(&mut rand::rngs::StdRng::seed_from_u64(seed));
        let traverser = (seed % 3) as usize;
        let run = |prune_below| {
            let (mut deltas, mut counts) = (Deltas::default(), Counts::default());
            let mut state = deal;
            let value = Traversal { table: &trained.table, deltas: &mut deltas, sampler: PathSampler(seed), traverser,
                weight: 301., last_average_street: 3, counts: &mut counts, fork_depth, prune_below }.run(&mut state);
            (value, deltas, counts)
        };
        let (v, d, c) = run(None);
        // The largest limit prunes every zero-probability action.
        let (vmax, _, cmax) = run(Some(f64::MAX));
        assert_eq!(v.to_bits(), vmax.to_bits(), "seed {seed}: the traverser's value with every possible skip");
        // A skipped subtree is not visited: every skip saves at least one node.
        assert!(cmax.nodes + cmax.pruned <= c.nodes, "seed {seed} fork depth {fork_depth}");
        let (vp, dp, cp) = run(Some(0.));
        total += cp.pruned;
        assert_eq!(v.to_bits(), vp.to_bits(), "seed {seed}: the traverser's value");
        assert!(cp.nodes + cp.pruned <= c.nodes, "seed {seed} fork depth {fork_depth}");
        // Where the root is the traverser's: pruned actions get no update, the others the same one.
        let Some(decision) = deal.decision().filter(|d| d.actor == traverser) else { continue };
        let Some(entry) = trained.table.get(&decision.key) else { continue };
        let (a, b) = (&d[&decision.key], &dp[&decision.key]);
        let policy = entry.policy(false);
        for i in 0..decision.len() {
            if policy[i] == 0. && entry.regrets[i] < 0. {
                assert_eq!(b.regrets()[i].to_bits(), 0f64.to_bits(), "seed {seed}: pruned action {i}");
            } else {
                assert_eq!(a.regrets()[i].to_bits(), b.regrets()[i].to_bits(), "seed {seed}: action {i}");
            }
        }
    }
    assert!(total > 0, "the trained table offers actions to prune");
}

#[test]
fn all_negative_regrets_prune_nothing() {
    let game = SmallGame::new(Kind::Kuhn, 3);
    let mut table = Table::default();
    for (hand, _) in game.deals() {
        let mut state = hand;
        while let Some(d) = state.decision() {
            let mut e = Entry::new(d, 3);
            e.regrets.iter_mut().enumerate().for_each(|(i, r)| *r = -1. - i as f64);
            table.insert(d.key, e);
            state.apply(0);
        }
    }
    for (hand, _) in game.deals() {
        let (mut deltas, mut counts) = (Deltas::default(), Counts::default());
        let mut state = hand;
        Traversal { table: &table, deltas: &mut deltas, sampler: PathSampler(3), traverser: 0, weight: 1., last_average_street: 3,
            counts: &mut counts, fork_depth: 0, prune_below: Some(0.) }.run(&mut state);
        assert_eq!(counts.pruned, 0, "regret matching plays uniformly; no action has zero probability");
    }
}

#[test]
fn pruning_is_identical_for_every_thread_count_and_resumes_exactly() {
    let game = SmallGame::new(Kind::Leduc, 3);
    let prune = Some(Prune { bb: 0.05, after: 20 });
    let one = pruned_trainer(&game, 9, 80, 1, prune);
    assert!(one.counts.pruned > 0);
    for threads in [2, 8, 16] {
        let many = pruned_trainer(&game, 9, 80, threads, prune);
        assert!(checkpoint_bytes(&one, "p1") == checkpoint_bytes(&many, "pn"), "threads {threads}");
    }
    let mut prefix = pruned_trainer(&game, 9, 40, 4, prune);
    let path = std::env::temp_dir().join(format!("multi-prune-{}.gz", std::process::id()));
    crate::multi_checkpoint::save(&prefix, &path, crate::gz::Gzip::Compatible).unwrap();
    let mut resumed = crate::multi_checkpoint::load(&path).unwrap();
    assert_eq!((resumed.prune, resumed.counts.pruned), (prune, prefix.counts.pruned));
    for _ in 0..40 {
        resumed.step_fast(&game);
        prefix.step_fast(&game);
    }
    assert!(checkpoint_bytes(&one, "a") == checkpoint_bytes(&resumed, "b"));
    assert!(checkpoint_bytes(&prefix, "c") == checkpoint_bytes(&resumed, "b"));
    // Pruning belongs to fast checkpoints.
    let text = std::io::read_to_string(flate2::read::MultiGzDecoder::new(std::fs::File::open(&path).unwrap())).unwrap();
    let production = text.replacen(r#""roots_per_seat":2,"#, "", 1).replacen(r#""sampling":"path-v1","#, "", 1);
    let bad = std::env::temp_dir().join(format!("multi-prune-bad-{}.gz", std::process::id()));
    let mut out = flate2::write::GzEncoder::new(std::fs::File::create(&bad).unwrap(), flate2::Compression::default());
    std::io::Write::write_all(&mut out, production.as_bytes()).unwrap();
    out.finish().unwrap();
    assert!(crate::multi_checkpoint::load(&bad).is_err());
    for p in [path, bad] {
        std::fs::remove_file(p).unwrap();
    }
    let mut stream = Trainer { prune, ..Trainer::new(&game, 9, 3, usize::MAX, false) };
    assert!(std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| stream.step(&game))).is_err(), "pruning needs fast mode");
}

#[test]
fn pruning_converges_like_unpruned_fast_mode() {
    const SEEDS: u64 = 8;
    for (kind, iterations, after) in [(Kind::Kuhn, 10_000, 500), (Kind::Leduc, 1_000, 100)] {
        let game = SmallGame::new(kind, 3);
        let tree = Tree::new(game, 10_000_000);
        let gain = |t: &Trainer| tree.evaluate(&tree.profile(&t.table, true)).gains.iter().fold(0f64, |m, g| m.max(*g));
        let (mut plain, mut same_iterations, mut same_nodes, mut skipped) = (0., 0., 0., 0);
        for seed in 1..=SEEDS {
            let a = pruned_trainer(&game, seed, iterations, 8, None);
            let mut b = pruned_trainer(&game, seed, iterations, 8, Some(Prune { bb: 0.05, after }));
            plain += gain(&a) / SEEDS as f64;
            same_iterations += gain(&b) / SEEDS as f64;
            assert!(b.counts.pruned > 0 && b.counts.nodes < a.counts.nodes);
            // Equal compute: pruning spends the nodes it saved on further iterations.
            while b.counts.nodes < a.counts.nodes {
                b.step_fast(&game);
            }
            same_nodes += gain(&b) / SEEDS as f64;
            skipped += b.counts.pruned;
        }
        eprintln!("{kind:?} 3 players, {iterations} iterations: mean largest gain over {SEEDS} seeds, fast {plain:.5}, pruning at equal iterations {same_iterations:.5}, pruning at equal nodes {same_nodes:.5}; {skipped} actions skipped");
        assert!(same_nodes < 1.25 * plain, "{kind:?}: pruning at equal nodes {same_nodes} against {plain}");
    }
}

#[test]
fn the_pruning_schedule_waits_for_after_and_keeps_full_iterations() {
    let prune = Prune { bb: 0.5, after: 100 };
    assert!((0..=100).all(|t| prune.limit(17, t, 1).is_none()), "nothing before `after`");
    let full: Vec<u64> = (101..=20_100).filter(|&t| prune.limit(17, t, 1).is_none()).collect();
    assert!(full.iter().all(|&t| child_path(17, t as usize) % 20 == 0));
    // About one iteration in 20 is full: 1,000 expected in 20,000, three standard deviations.
    assert!((900..=1_100).contains(&full.len()), "{} full iterations", full.len());
    // The limit is bb per root under the linear weights.
    let t = (101..).find(|&t| prune.limit(17, t, 1).is_some()).unwrap();
    let w = (t * (t + 1) / 2) as f64;
    assert_eq!(prune.limit(17, t, 1), Some(-0.5 * w));
    assert_eq!(prune.limit(17, t, 8), Some(-0.5 * 8. * w));
}

#[test]
fn the_pruned_count_is_one_per_skipped_action() {
    // Only the traverser's first decision is stored, with one action far below any limit.
    let game = SmallGame::new(Kind::Kuhn, 3);
    for fork_depth in [0, 1] {
        for (hand, _) in game.deals() {
            let d = hand.decision().unwrap();
            let mut table = Table::default();
            let mut e = Entry::new(d, 3);
            e.regrets.copy_from_slice(&[1., -100.][..d.len()]);
            table.insert(d.key, e);
            let (mut deltas, mut counts) = (Deltas::default(), Counts::default());
            let mut state = hand;
            Traversal { table: &table, deltas: &mut deltas, sampler: PathSampler(5), traverser: d.actor, weight: 1., last_average_street: 3,
                counts: &mut counts, fork_depth, prune_below: Some(0.) }.run(&mut state);
            assert_eq!(counts.pruned, 1, "fork depth {fork_depth}");
            assert_eq!(deltas[&d.key].regrets()[1].to_bits(), 0f64.to_bits(), "the pruned action gets no update");
        }
    }
}
