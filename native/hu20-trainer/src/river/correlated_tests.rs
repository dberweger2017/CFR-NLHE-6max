use super::*;
use crate::river::{Algorithm, Node, Solver};
use rand::{seq::SliceRandom, Rng, SeedableRng};

fn mask(c: [u8; 2]) -> u64 {
    (1u64 << c[0]) | (1u64 << c[1])
}
fn nodes() -> Vec<Node> {
    vec![
        Node::Decision {
            actor: 0,
            children: vec![1, 2],
        },
        Node::Leaf(Terminal {
            base: 1.,
            win0: 0.,
            tie0: 0.,
        }),
        Node::Decision {
            actor: 1,
            children: vec![3, 4],
        },
        Node::Leaf(Terminal {
            base: -2.,
            win0: 0.,
            tie0: 0.,
        }),
        Node::Leaf(Terminal {
            base: -7.005,
            win0: 15.01,
            tie0: 7.51,
        }),
    ]
}
// Independent explicit three-holding enumeration. Does not call Removal,
// its single/pair summaries, prefix features, or its cancellation repair.
fn dense(board: [u8; 5], ranges: [Vec<Holding>; 2], folded: &[Holding]) -> Game {
    let totals: [f64; 2] = std::array::from_fn(|s| ranges[s].iter().map(|h| h.weight).sum());
    let ft: f64 = folded.iter().map(|h| h.weight).sum();
    let mut law = Vec::new();
    for a in &ranges[0] {
        for b in &ranges[1] {
            let mass = if mask(a.cards) & mask(b.cards) != 0 {
                0.
            } else {
                folded
                    .iter()
                    .filter(|f| mask(f.cards) & (mask(a.cards) | mask(b.cards)) == 0)
                    .map(|f| f.weight / ft)
                    .sum()
            };
            law.push((a.weight / totals[0]) * (b.weight / totals[1]) * mass);
        }
    }
    Game::new(board, ranges, nodes(), 2.)
        .unwrap()
        .with_joint(law)
        .unwrap()
}
fn close(a: f64, b: f64, tolerance: f64) {
    assert!(
        (a - b).abs() <= tolerance * (1. + b.abs()),
        "{a:0.17} != {b:0.17}"
    );
}
fn compare_quality(a: &mut Solver, b: &mut Solver, p: &[Vec<f64>]) {
    let qa = a.quality(p).unwrap();
    let qb = b.quality(p).unwrap();
    for key in ["profile_values_bb", "best_response_gains_bb"] {
        for (x, y) in qa[key]
            .as_array()
            .unwrap()
            .iter()
            .zip(qb[key].as_array().unwrap())
        {
            close(x.as_f64().unwrap(), y.as_f64().unwrap(), 1e-8);
        }
    }
}
fn compare(board: [u8; 5], ranges: [Vec<Holding>; 2], folded: Vec<Holding>) {
    let fast = Game::new(board, ranges.clone(), nodes(), 2.)
        .unwrap()
        .with_folded_range(folded.clone())
        .unwrap();
    let oracle = dense(board, ranges, &folded);
    for seat in 0..2 {
        for pattern in 0..4 {
            let reach: Vec<_> = (0..fast.holdings(1 - seat))
                .map(|i| match pattern {
                    0 => 1.,
                    1 => ((i * 17) % 23) as f64 / 23.,
                    2 => {
                        if i == 0 {
                            1.
                        } else {
                            0.
                        }
                    }
                    _ => 0.,
                })
                .collect();
            for t in [
                Terminal {
                    base: -7.005,
                    win0: 15.01,
                    tie0: 7.51,
                },
                Terminal {
                    base: 1.17,
                    win0: 0.,
                    tie0: 0.,
                },
            ] {
                let a = fast.leaf(t, seat, &reach).unwrap();
                let b = oracle.leaf(t, seat, &reach).unwrap();
                for (&x, &y) in a.iter().zip(&b) {
                    close(x, y, 1e-10);
                }
            }
        }
    }
    let mut a = Solver::new(fast, vec![None; 5]).unwrap();
    let mut b = Solver::new(oracle, vec![None; 5]).unwrap();
    for solver in [&mut a, &mut b] {
        solver
            .set_algorithm(Algorithm::Discounted {
                alpha: 1.5,
                beta: 0.,
                gamma: 2.,
            })
            .unwrap();
    }
    let uniform = a.average();
    compare_quality(&mut a, &mut b, &uniform);
    a.advance(64).unwrap();
    b.advance(64).unwrap();
    // Both policies are evaluated under both operators, not compared bitwise.
    let pa = a.average();
    let pb = b.average();
    compare_quality(&mut a, &mut b, &pa);
    compare_quality(&mut a, &mut b, &pb);
}
fn all(board: [u8; 5]) -> Vec<[u8; 2]> {
    let cards: Vec<_> = (0..52).filter(|c| !board.contains(c)).collect();
    (0..cards.len())
        .flat_map(|i| (i + 1..cards.len()).map(move |j| (i, j)))
        .map(|(i, j)| [cards[i], cards[j]])
        .collect()
}
#[test]
fn randomized_nonfactorizable_leaves_profiles_and_responses_match_independent_oracle() {
    let mut rng = rand::rngs::StdRng::seed_from_u64(2026102138201);
    for trial in 0..50 {
        let board = if trial % 7 == 0 {
            [32, 36, 40, 44, 48]
        } else {
            [0, 9, 22, 35, 48]
        };
        let mut cards = all(board);
        let mut range = |n: usize| {
            cards.shuffle(&mut rng);
            cards
                .iter()
                .take(n)
                .map(|&c| Holding {
                    cards: c,
                    weight: if rng.gen_range(0..7) == 0 {
                        0.
                    } else {
                        10f64.powi(-rng.gen_range(0..=9))
                    },
                })
                .collect::<Vec<_>>()
        };
        let ranges = [range(13 + trial % 5), range(17 + trial % 3)];
        let folded = range(10 + trial % 7);
        let fast = Game::new(board, ranges.clone(), nodes(), 2.)
            .unwrap()
            .with_folded_range(folded.clone());
        match fast {
            Ok(_) => compare(board, ranges, folded),
            Err(e) => {
                assert!(e.contains("conditioning floor"));
                let g = dense(board, ranges, &folded);
                assert!(g.joint.is_some());
            }
        }
    }
}
#[test]
fn sparse_folded_law_preserves_blocked_and_zero_mass_rows_and_board_ties() {
    let h = |c, w| Holding {
        cards: c,
        weight: w,
    };
    for board in [[0, 9, 22, 35, 48], [32, 36, 40, 44, 48]] {
        let r = [
            vec![h([1, 2], 1.), h([3, 4], 1.), h([5, 6], 0.)],
            vec![h([1, 7], 1.), h([3, 8], 1.), h([10, 11], 1.)],
        ];
        let f = vec![h([1, 2], 1.), h([12, 13], 1e-12)];
        compare(board, r, f);
    }
}
#[test]
fn exactly_blocked_conditional_reach_uses_scalar_repair_without_a_mass_floor() {
    let h = |c| Holding {
        cards: c,
        weight: 1.,
    };
    let g = Game::new(
        [0, 9, 22, 35, 48],
        [vec![h([1, 2]), h([3, 4])], vec![h([1, 5]), h([6, 7])]],
        nodes(),
        2.,
    )
    .unwrap()
    .with_folded_range(vec![h([10, 11])])
    .unwrap();
    let out = g
        .leaf(
            Terminal {
                base: 1.,
                win0: 0.,
                tie0: 0.,
            },
            0,
            &[1., 0.],
        )
        .unwrap();
    assert_eq!(out[0], 0.);
    assert!(out[1] > 0.);
    assert!(g.chance_stats()["scalar_rows"].as_u64().unwrap() > 0);
}
#[test]
fn invalid_or_unrepresentable_folded_laws_are_rejected() {
    let board = [0, 9, 22, 35, 48];
    let h = |c, w| Holding {
        cards: c,
        weight: w,
    };
    let make = || {
        Game::new(
            board,
            [vec![h([1, 2], 1.)], vec![h([3, 4], 1.)]],
            nodes(),
            2.,
        )
        .unwrap()
    };
    for folded in [
        vec![],
        vec![h([0, 5], 1.)],
        vec![h([5, 5], 1.)],
        vec![h([5, 6], -1.)],
        vec![h([5, 6], f64::NAN)],
        vec![h([5, 6], 0.)],
        vec![h([5, 6], 1.), h([6, 5], 1.)],
        vec![h([1, 5], 1.)],
        vec![h([1, 5], 1.), h([6, 7], 1e-6)],
    ] {
        assert!(make().with_folded_range(folded).is_err());
    }
    let g = make().with_folded_range(vec![h([5, 6], 1.)]).unwrap();
    assert!(g.with_joint(vec![1.]).is_err());
    assert!(make()
        .with_joint(vec![1.])
        .unwrap()
        .with_folded_range(vec![h([5, 6], 1.)])
        .is_err());
}
#[test]
fn hand_calculated_folded_correlation_has_correct_values_and_best_responses() {
    let h = |c| Holding {
        cards: c,
        weight: 1.,
    };
    // Explicit folded worlds leave active joint masses [2,1;1,2]/6.
    // The royal board ties, so the showdown leaf pays hero -7.005+7.51=0.505.
    let g = Game::new(
        [32, 36, 40, 44, 48],
        [vec![h([1, 2]), h([3, 4])], vec![h([5, 6]), h([7, 8])]],
        nodes(),
        2.,
    )
    .unwrap()
    .with_folded_range(vec![h([1, 5]), h([3, 7]), h([9, 10])])
    .unwrap();
    let t = Terminal {
        base: 1.,
        win0: 0.,
        tie0: 0.,
    };
    let a = g.leaf(t, 0, &[0., 1.]).unwrap();
    close(a[0], 1. / 6., 1e-12);
    close(a[1], 1. / 3., 1e-12);
    let b = g.leaf(t, 1, &[1., 0.]).unwrap();
    close(b[0], -1. / 3., 1e-12);
    close(b[1], -1. / 6., 1e-12);
    let mut s = Solver::new(g, vec![None; 5]).unwrap();
    let mut p = s.average();
    p[2] = vec![0.2, 0.8, 0.8, 0.2];
    let q = s.quality(&p).unwrap();
    close(q["profile_values_bb"][0].as_f64().unwrap(), 0.12625, 1e-12);
    close(q["profile_values_bb"][1].as_f64().unwrap(), -0.12625, 1e-12);
    close(
        q["best_response_gains_bb"][0].as_f64().unwrap(),
        0.87375,
        1e-12,
    );
    close(
        q["best_response_gains_bb"][1].as_f64().unwrap(),
        0.62625,
        1e-12,
    );
}
#[test]
fn all_1081_holdings_match_enumerated_folded_worlds() {
    for board in [[0, 9, 22, 35, 48], [32, 36, 40, 44, 48]] {
        let cards = all(board);
        let ranges = std::array::from_fn(|s| {
            cards
                .iter()
                .enumerate()
                .map(|(i, &c)| Holding {
                    cards: c,
                    weight: if (i + s) % 11 == 0 {
                        0.
                    } else {
                        1. + ((i * 17 + s) % 23) as f64
                    },
                })
                .collect::<Vec<_>>()
        });
        let folded = vec![
            Holding {
                cards: cards[17],
                weight: 1.,
            },
            Holding {
                cards: cards[74],
                weight: 3.,
            },
            Holding {
                cards: cards[102],
                weight: 0.2,
            },
        ];
        let oracle = dense(board, ranges.clone(), &folded);
        let fast = Game::new(board, ranges, nodes(), 2.)
            .unwrap()
            .with_folded_range(folded)
            .unwrap();
        for seat in 0..2 {
            let reach: Vec<_> = (0..1081).map(|i| ((i * 23) % 17) as f64 / 17.).collect();
            for t in [
                Terminal {
                    base: -7.005,
                    win0: 15.01,
                    tie0: 7.51,
                },
                Terminal {
                    base: 1.17,
                    win0: 0.,
                    tie0: 0.,
                },
            ] {
                let a = fast.leaf(t, seat, &reach).unwrap();
                let b = oracle.leaf(t, seat, &reach).unwrap();
                for (&x, &y) in a.iter().zip(&b) {
                    close(x, y, 1e-10);
                }
            }
        }
    }
}
