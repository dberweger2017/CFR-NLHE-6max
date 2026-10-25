use super::*;

fn sample(full: bool, royal: bool) -> Game {
    let board = if royal {
        [32, 36, 40, 44, 48]
    } else {
        [0, 9, 22, 35, 48]
    };
    let rest: Vec<_> = (0..52).filter(|c| !board.contains(c)).collect();
    let mut ranges: [Vec<Holding>; 2] = [Vec::new(), Vec::new()];
    for (seat, range) in ranges.iter_mut().enumerate() {
        for i in 0..rest.len() {
            for j in i + 1..rest.len() {
                if full || range.len() < 7 {
                    range.push(Holding {
                        cards: [rest[i], rest[j]],
                        weight: if (i + 3 * j + seat) % 11 == 0 {
                            0.
                        } else {
                            1. + ((i * 3 + j + seat) % 7) as f64
                        },
                    });
                }
            }
        }
    }
    // The small ranges above deliberately overlap a lot; append a disjoint pair.
    if !full {
        for r in &mut ranges {
            r.push(Holding {
                cards: [rest[20], rest[30]],
                weight: 2.,
            });
        }
    }
    Game::new(
        board,
        ranges,
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
        ],
        2.,
    )
    .unwrap()
}
fn scalar(g: &Game, t: Terminal, seat: usize, reach: &[f64]) -> Vec<f64> {
    g.hands[seat]
        .iter()
        .map(|h| {
            g.hands[1 - seat]
                .iter()
                .zip(reach)
                .filter(|(o, _)| h.mask & o.mask == 0)
                .map(|(o, &r)| {
                    let (a, b) = if seat == 0 { (h, o) } else { (o, h) };
                    let u = t.base
                        + t.win0 * (if a.rank > b.rank { 1. } else { 0. })
                        + t.tie0 * (if a.rank == b.rank { 1. } else { 0. });
                    u * h.weight * o.weight * r / g.z * if seat == 0 { 1. } else { -1. }
                })
                .sum()
        })
        .collect()
}
#[test]
fn sorted_leaves_match_dense_scalar_with_blockers_ties_and_zero_mass() {
    for full in [false, true] {
        for royal in [false, true] {
            let g = sample(full, royal);
            for seat in 0..2 {
                for pattern in 0..3 {
                    let reach: Vec<_> = (0..g.holdings(1 - seat))
                        .map(|i| match pattern {
                            0 => 1.,
                            1 => ((i * 17) % 23) as f64 / 23.,
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
                        let linear = g.leaf(t, seat, &reach).unwrap();
                        let expected = scalar(&g, t, seat, &reach);
                        for (x, y) in linear.iter().zip(expected) {
                            assert!((x - y).abs() < 1e-11, "{x} != {y}");
                        }
                    }
                }
            }
        }
    }
}
#[test]
fn values_are_zero_sum_in_both_orientations() {
    let g = sample(true, false);
    let t = Terminal {
        base: -7.005,
        win0: 15.01,
        tie0: 7.51,
    };
    let a: f64 = g.leaf(t, 0, &vec![1.; g.holdings(1)]).unwrap().iter().sum();
    let b: f64 = g.leaf(t, 1, &vec![1.; g.holdings(0)]).unwrap().iter().sum();
    assert!((a + b).abs() < 1e-11);
}
#[test]
fn fixed_work_is_exactly_repeatable_and_incremental() {
    let make = || {
        let g = sample(false, false);
        let f = vec![None; g.nodes.len()];
        Solver::new(g, f).unwrap()
    };
    let mut a = make();
    let mut b = make();
    a.advance(50).unwrap();
    b.advance(20).unwrap();
    b.advance(30).unwrap();
    assert_eq!(a.regrets, b.regrets);
    assert_eq!(a.numer, b.numer);
    assert_eq!(a.denom, b.denom);
    assert_eq!(a.average(), b.average());
    let q = a.quality(&a.average()).unwrap();
    assert!(q["zero_sum_error_bb"].as_f64().unwrap() < 1e-12);
}
#[test]
fn quality_does_not_deviate_at_fixed_nodes() {
    // Seat 0's root is fixed (an action already taken); its best response may only deviate
    // below it, while seat 1's best response is unchanged.
    let row: Vec<f64> = (0..sample(false, false).holdings(0)).flat_map(|_| [0., 1.]).collect();
    let mut fixed = vec![None; sample(false, false).nodes.len()];
    fixed[0] = Some(row.clone());
    let mut with_fixed = Solver::new(sample(false, false), fixed.clone()).unwrap();
    with_fixed.set_taken(0).unwrap();
    with_fixed.advance(20).unwrap();
    let profile = with_fixed.average();
    let q = with_fixed.quality(&profile).unwrap();
    let mut free = Solver::new(sample(false, false), vec![None; profile.len()]).unwrap();
    let r = free.quality(&profile).unwrap();
    let gain = |v: &Value, s: usize| v["best_response_gains_bb"][s].as_f64().unwrap();
    assert_eq!(gain(&q, 0), 0., "the played root is the only seat-0 decision");
    assert!(gain(&r, 0) > 0., "without the played flag the same profile is exploitable at the root");
    assert_eq!(gain(&q, 1), gain(&r, 1));
    assert_eq!(q["profile_values_bb"], r["profile_values_bb"]);
    // Fixed but not played (prepared-request constraints): quality is unchanged.
    let mut constrained = Solver::new(sample(false, false), fixed).unwrap();
    assert_eq!(constrained.quality(&profile).unwrap(), r);
    let mut free = Solver::new(sample(false, false), vec![None; profile.len()]).unwrap();
    assert!(free.set_taken(0).is_err(), "only fixed nodes can be played");
}
#[test]
fn fixed_policy_is_kept_even_on_unreached_rows() {
    let g = sample(false, false);
    let mut fixed = vec![None; g.nodes.len()];
    fixed[0] = Some((0..g.holdings(0)).flat_map(|_| [1., 0.]).collect());
    fixed[2] = Some((0..g.holdings(1)).flat_map(|_| [0.25, 0.75]).collect());
    let mut s = Solver::new(g, fixed.clone()).unwrap();
    s.advance(5).unwrap();
    assert_eq!(s.average()[0], *fixed[0].as_ref().unwrap());
    assert_eq!(s.average()[2], *fixed[2].as_ref().unwrap());
    assert!(s.regrets.iter().flatten().all(|&v| v == 0.));
    assert!(s.denom[2].iter().all(|&v| v == 5. * 6. / 2.));
}
#[test]
fn malformed_cards_ranges_tree_and_requests_are_refused() {
    let board = [0, 1, 2, 3, 4];
    let h = Holding {
        cards: [5, 6],
        weight: 1.,
    };
    let leaf = Node::Leaf(Terminal {
        base: 0.,
        win0: 1.,
        tie0: 0.5,
    });
    assert!(Game::new(
        board,
        [vec![h.clone()], vec![h.clone()]],
        vec![leaf.clone()],
        1.
    )
    .is_err());
    let other = Holding {
        cards: [7, 8],
        weight: 1.,
    };
    assert!(Game::new(
        [0, 0, 2, 3, 4],
        [vec![h.clone()], vec![other.clone()]],
        vec![leaf.clone()],
        1.
    )
    .is_err());
    assert!(Game::new(
        board,
        [vec![h.clone(), h.clone()], vec![other.clone()]],
        vec![leaf.clone()],
        1.
    )
    .is_err());
    assert!(Game::new(
        board,
        [vec![h.clone()], vec![other.clone()]],
        vec![Node::Decision {
            actor: 0,
            children: vec![0]
        }],
        1.
    )
    .is_err());
    assert!(Game::new(board, [vec![h], vec![other]], vec![leaf.clone(), leaf], 1.).is_err());
    let g = sample(false, false);
    assert!(g
        .leaf(
            Terminal {
                base: 0.,
                win0: 1.,
                tie0: 0.5
            },
            2,
            &[]
        )
        .is_err());
    assert!(request(&json!({"format":"river-prepared-v1","hidden_cards":[5,6]})).is_err());
}

#[test]
fn numerical_failure_does_not_publish_a_partial_sweep() {
    let mut g = sample(false, false);
    for node in &mut g.nodes {
        if let Node::Leaf(t) = node {
            t.base = f64::MAX;
            t.win0 = f64::MAX;
            t.tie0 = f64::MAX;
        }
    }
    let mut solver = Solver::new(g, vec![None; 5]).unwrap();
    assert!(solver.advance(1).is_err());
    assert_eq!(solver.sweeps, 0);
    assert!(solver.regrets.iter().flatten().all(|&x| x == 0.));
    assert!(solver.numer.iter().flatten().all(|&x| x == 0.));
    assert!(solver.denom.iter().flatten().all(|&x| x == 0.));
    assert!(solver.quality(&[]).is_err());
}

#[test]
fn nearly_blocked_chance_law_uses_stable_explicit_scalar_fallback() {
    let e = 1e-12;
    let g = Game::new(
        [0, 9, 22, 35, 48],
        [
            vec![
                Holding {
                    cards: [1, 2],
                    weight: 1.,
                },
                Holding {
                    cards: [5, 6],
                    weight: e,
                },
            ],
            vec![
                Holding {
                    cards: [1, 3],
                    weight: 1.,
                },
                Holding {
                    cards: [7, 8],
                    weight: e,
                },
            ],
        ],
        vec![Node::Leaf(Terminal {
            base: 1.,
            win0: 0.,
            tie0: 0.,
        })],
        1.,
    )
    .unwrap();
    assert!(g.z < 1e-4);
    for seat in 0..2 {
        let t = Terminal {
            base: 1.,
            win0: 2.,
            tie0: 1.,
        };
        let actual = g.leaf(t, seat, &[1., 1.]).unwrap();
        let expected = scalar(&g, t, seat, &[1., 1.]);
        for (a, b) in actual.iter().zip(expected) {
            assert!((a - b).abs() < 1e-13);
        }
    }
}

#[test]
fn dcfr_discounts_its_first_sweep_and_converges() {
    let solve = |algorithm: Algorithm, sweeps: u64| {
        let g = sample(true, false);
        let n = g.node_count();
        let mut s = Solver::new(g, vec![None; n]).unwrap();
        s.set_algorithm(algorithm).unwrap();
        s.advance(sweeps).unwrap();
        s
    };
    // At t = 1 both regret factors are 1/2 and the average is only rescaled.
    let (linear, discounted) = (solve(Algorithm::Linear, 1), solve(DCFR, 1));
    for (a, b) in linear
        .regrets
        .iter()
        .flatten()
        .zip(discounted.regrets.iter().flatten())
    {
        assert_eq!(*b, 0.5 * *a);
    }
    assert_eq!(linear.average(), discounted.average());
    let mut last = f64::INFINITY;
    for sweeps in [16, 64, 256] {
        let mut s = solve(DCFR, sweeps);
        let average = s.average();
        let e = s.quality(&average).unwrap()["exploitability_bb"]
            .as_f64()
            .unwrap();
        assert!(e < last, "{sweeps}: {e} >= {last}");
        last = e;
    }
    let mut s = solve(DCFR, 1);
    assert!(s.set_algorithm(Algorithm::Linear).is_err());
}

#[test]
fn product_joint_law_matches_product_leaves_and_refuses_blocked_mass() {
    for full in [false, true] {
        let product = sample(full, false);
        let (n0, n1) = (product.holdings(0), product.holdings(1));
        let mut joint = vec![0.; n0 * n1];
        for (i, a) in product.hands[0].iter().enumerate() {
            for (j, b) in product.hands[1].iter().enumerate() {
                if a.mask & b.mask == 0 {
                    joint[i * n1 + j] = a.weight * b.weight;
                }
            }
        }
        let exact = sample(full, false).with_joint(joint.clone()).unwrap();
        for seat in 0..2 {
            let reach: Vec<_> = (0..product.holdings(1 - seat))
                .map(|i| ((i * 17) % 23) as f64 / 23.)
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
                let a = product.leaf(t, seat, &reach).unwrap();
                let b = exact.leaf(t, seat, &reach).unwrap();
                for (x, y) in a.iter().zip(&b) {
                    assert!((x - y).abs() < 1e-12, "{x} != {y}");
                }
            }
        }
        let blocked = (0..n0)
            .flat_map(|i| (0..n1).map(move |j| (i, j)))
            .find(|&(i, j)| product.hands[0][i].mask & product.hands[1][j].mask != 0)
            .unwrap();
        let mut bad = joint;
        bad[blocked.0 * n1 + blocked.1] = 1.;
        assert!(sample(full, false).with_joint(bad).is_err());
    }
}

#[test]
fn correlated_joint_law_matches_hand_calculated_values_and_best_responses() {
    // Public royal flush: every compatible holding ties, independently of the
    // evaluator. The nonfactorizable law has determinant .10, not zero.
    let board = [32, 36, 40, 44, 48];
    let ranges = [
        vec![
            Holding {
                cards: [0, 1],
                weight: 1.,
            },
            Holding {
                cards: [2, 3],
                weight: 1.,
            },
            Holding {
                cards: [4, 5],
                weight: 0.,
            },
        ],
        vec![
            Holding {
                cards: [4, 5],
                weight: 1.,
            },
            Holding {
                cards: [6, 7],
                weight: 1.,
            },
        ],
    ];
    let nodes = vec![
        Node::Decision {
            actor: 0,
            children: vec![1, 2],
        },
        Node::Leaf(Terminal {
            base: 0.,
            win0: 0.,
            tie0: 0.,
        }),
        Node::Decision {
            actor: 1,
            children: vec![3, 4],
        },
        Node::Leaf(Terminal {
            base: 1.,
            win0: 0.,
            tie0: 0.,
        }),
        Node::Leaf(Terminal {
            base: -1.,
            win0: 0.,
            tie0: 0.,
        }),
    ];
    let game = Game::new(board, ranges, nodes, 2.)
        .unwrap()
        .with_joint(vec![0.4, 0.1, 0.2, 0.3, 0., 0.])
        .unwrap();
    let terminal = Terminal {
        base: 2.,
        win0: 17.,
        tie0: 0.75,
    };
    // Own rows use the joint; player 1 uses its transpose. Product marginals
    // would give different answers, so product-only bugs cannot pass this.
    let a = game.leaf(terminal, 0, &[0.2, 0.9]).unwrap();
    let b = game.leaf(terminal, 1, &[0.2, 0.9, 0.7]).unwrap();
    for (actual, expected) in a.iter().zip([0.4675, 0.8525, 0.]) {
        assert!((actual - expected).abs() < 1e-14);
    }
    for (actual, expected) in b.iter().zip([-0.715, -0.7975]) {
        assert!((actual - expected).abs() < 1e-14);
    }
    // Hero mixes fold/play 50:50. Opponent chooses +1 with its first holding
    // and -1 with its second. EV=.5*(.4-.1+.2-.3)=.1. Hero BR plays only its
    // first holding for EV=.3; opponent BR always chooses -1 for EV=.5.
    let mut solver = Solver::new(game, vec![None; 5]).unwrap();
    let profile = vec![vec![0.5; 6], vec![], vec![1., 0., 0., 1.], vec![], vec![]];
    let quality = solver.quality(&profile).unwrap();
    for (actual, expected) in quality["profile_values_bb"]
        .as_array()
        .unwrap()
        .iter()
        .zip([0.1, -0.1])
    {
        assert!((actual.as_f64().unwrap() - expected).abs() < 1e-14);
    }
    for (actual, expected) in quality["best_response_gains_bb"]
        .as_array()
        .unwrap()
        .iter()
        .zip([0.2, 0.6])
    {
        assert!((actual.as_f64().unwrap() - expected).abs() < 1e-14);
    }
}

#[test]
fn masked_best_responses_agree_with_quality_and_only_restrict() {
    let g = sample(true, false);
    let n = g.node_count();
    let mut s = Solver::new(g, vec![None; n]).unwrap();
    s.set_algorithm(DCFR).unwrap();
    s.advance(8).unwrap();
    let profile = s.average();
    let quality = s.quality(&profile).unwrap();
    for seat in 0..2 {
        let value = s.value(&profile, seat, false, None).unwrap();
        let best = s.value(&profile, seat, true, None).unwrap();
        let gain = quality["best_response_gains_bb"][seat].as_f64().unwrap();
        assert!(((best - value).max(0.) - gain).abs() < 1e-12);
        let all: Vec<Vec<bool>> = (0..n)
            .map(|id| match s.node(id) {
                Node::Decision { children, .. } => vec![true; children.len()],
                Node::Leaf(_) => Vec::new(),
            })
            .collect();
        assert_eq!(
            s.value(&profile, seat, true, Some(all.clone())).unwrap(),
            best
        );
        // Allowing only the first action at the responder's own nodes cannot help it.
        let first: Vec<Vec<bool>> = (0..n)
            .map(|id| match s.node(id) {
                Node::Decision { actor, children } if *actor == seat => {
                    (0..children.len()).map(|a| a == 0).collect()
                }
                _ => Vec::new(),
            })
            .collect();
        let restricted = s.value(&profile, seat, true, Some(first)).unwrap();
        assert!(restricted <= best + 1e-12);
    }
}
