use super::*;

fn root() -> PublicRoot {
    let config = Config::new(&[10000; 3], 50, 100).unwrap();
    let mut hand = representative(config, 0, [0, 5, 10, 15, 20]).unwrap();
    let mut actions = Vec::new();
    while hand.street() != Street::River {
        let actor = hand.actor().unwrap();
        let obs = hand.observe(actor).unwrap();
        let action = if actor == 0 && hand.street() == Street::Preflop {
            Action {
                kind: Kind::Fold,
                raise_to: 0,
            }
        } else {
            Action {
                kind: if obs.legal.unwrap().check {
                    Kind::Check
                } else {
                    Kind::Call
                },
                raise_to: 0,
            }
        };
        let before = hand.players()[actor].stack;
        let street = hand.street();
        hand.apply_mut(action).unwrap();
        actions.push(json!([
            actor,
            street as u64,
            action.kind.name(),
            action.raise_to,
            before - hand.players()[actor].stack
        ]));
    }
    let legal = hand.legal().unwrap();
    reconstruct(&json!({"format":"nplayer-live-river-v1","button":0,"board":[0,5,10,15,20],"seat":hand.actor(),"hole":[30,31],"actions":actions,
        "players":hand.players().iter().map(|p|json!([p.stack,p.street_bet,p.contributed,p.folded])).collect::<Vec<_>>(),
        "legal":{"check":legal.check,"call_amount":legal.call_amount,"raise_to":legal.raise_to},"sweeps":16}),config).unwrap()
}

#[test]
fn folded_removal_matches_enumerating_all_folded_hands() {
    let pairs = [[0, 1], [0, 2], [2, 3], [4, 5], [6, 7], [1, 7]];
    let weights = [0.1, 0.2, 0., 0.3, 0.15, 0.25];
    let f = FoldRemoval::new(&pairs, &weights);
    for &a in &pairs {
        for &b in &pairs {
            if disjoint(a, b) {
                let expected: f64 = pairs
                    .iter()
                    .zip(weights)
                    .filter(|(h, _)| disjoint(a, **h) && disjoint(b, **h))
                    .map(|(_, w)| w)
                    .sum();
                assert!((f.compatible(a, b) - expected).abs() < 1e-14);
            }
        }
    }
}

#[test]
fn projection_includes_folded_actions_and_reports_correlation_loss() {
    let pairs = [[0, 1], [2, 3], [4, 5], [6, 7], [0, 2], [4, 6]];
    let weights = [
        vec![0.1, 0.2, 0.3, 0.1, 0.1, 0.2],
        vec![1. / 6.; 6],
        vec![1. / 6.; 6],
    ];
    let (r, p) = project(&pairs, &weights, [1, 2]).unwrap();
    let mut changed = weights.clone();
    changed[0] = vec![0., 0., 1., 0., 0., 0.];
    let (other, q) = project(&pairs, &changed, [1, 2]).unwrap();
    assert!(r[0]
        .iter()
        .zip(&other[0])
        .any(|(a, b)| (a.weight - b.weight).abs() > 1e-3));
    assert!(p["projection_total_variation"].as_f64().unwrap() > 0.);
    assert!(q["projection_total_variation"].as_f64().unwrap() > 0.);
    for row in r {
        assert!((row.iter().map(|h| h.weight).sum::<f64>() - 1.).abs() < 1e-12);
    }
}

#[test]
fn likelihoods_use_every_seat_and_never_representative_holes() {
    let r = root();
    let pairs = [[21, 22], [23, 24], [25, 26], [27, 28], [29, 30], [31, 32]];
    let (weights, counts) = likelihoods(&r, &pairs, |obs| {
        assert!(pairs.contains(&obs.hole));
        let n = multi_holdem::menu(obs).len();
        Ok((vec![1. / n as f64; n], if obs.seat == 0 { 2 } else { 1 }))
    })
    .unwrap();
    assert!(counts[0].zero > 0);
    assert!(counts[1].positive > 0);
    assert!(counts[2].positive > 0);
    for row in weights {
        for w in row {
            assert!((w - 1. / 6.).abs() < 1e-12);
        }
    }
    let rejected = likelihoods(&r, &pairs, |obs| {
        Ok((vec![0.; multi_holdem::menu(obs).len()], 0))
    });
    assert!(rejected.is_err());
}

#[test]
fn complete_menu_has_explicit_support_limit_instead_of_raise_truncation() {
    let mut r = root();
    let mut tree = Tree {
        nodes: Vec::new(),
        menus: Vec::new(),
        live: r.live,
        stacks: r.live.map(|s| r.hand.players()[s].stack),
        pot: r.hand.pot(),
        bb: 100.,
    };
    let error = tree.compile(&mut r.hand).unwrap_err();
    assert!(error.contains("no menu truncation"));
}

#[test]
fn public_boundary_refuses_hidden_state_and_invalid_cards() {
    let config = Config::new(&[10000; 3], 50, 100).unwrap();
    let hidden = json!({"format":"nplayer-live-river-v1","opponent_cards":[1,2]});
    assert!(reconstruct(&hidden, config)
        .err()
        .unwrap()
        .contains("unexpected field"));
    assert!(representative(config, 0, [1, 1, 2, 3, 4]).is_err());
}

#[test]
fn all_small_full_menu_leaves_match_engine_settlement_in_both_orientations() {
    for board in [[0, 5, 10, 15, 20], [32, 36, 40, 44, 48]] {
        for button in 0..3 {
            let config = Config::new(&[301, 302, 303], 50, 100).unwrap();
            let mut hand = representative(config, button, board).unwrap();
            while hand.street() != Street::River {
                let actor = hand.actor().unwrap();
                let obs = hand.observe(actor).unwrap();
                let action = Action {
                    kind: if hand.street() == Street::Preflop && actor == button {
                        Kind::Fold
                    } else if obs.legal.unwrap().check {
                        Kind::Check
                    } else {
                        Kind::Call
                    },
                    raise_to: 0,
                };
                hand.apply_mut(action).unwrap();
            }
            let live: Vec<_> = hand
                .players()
                .iter()
                .enumerate()
                .filter_map(|(s, p)| (!p.folded).then_some(s))
                .collect();
            for live in [[live[0], live[1]], [live[1], live[0]]] {
                let mut tree = Tree {
                    nodes: Vec::new(),
                    menus: Vec::new(),
                    live,
                    stacks: live.map(|s| hand.players()[s].stack),
                    pot: hand.pot(),
                    bb: 100.,
                };
                tree.compile(&mut hand.clone()).unwrap();
                fn verify(tree: &Tree, mut h: Hand, id: usize) {
                    match &tree.nodes[id] {
                        Node::Leaf(t) => {
                            let a = h.observe(tree.live[0]).unwrap().hole;
                            let b = h.observe(tree.live[1]).unwrap().hole;
                            let board = h.board();
                            let rank = |pair: [u8; 2]| {
                                hu20_buckets::evaluate(&[
                                    pair[0], pair[1], board[0], board[1], board[2], board[3],
                                    board[4],
                                ])
                            };
                            let actual = t.base
                                + t.win0 * if rank(a) > rank(b) { 1. } else { 0. }
                                + t.tie0 * if rank(a) == rank(b) { 1. } else { 0. };
                            let expected = (h.players()[tree.live[0]].stack as f64
                                - tree.stacks[0] as f64
                                - tree.pot as f64 / 2.)
                                / tree.bb;
                            assert!((actual - expected).abs() < 1e-12);
                        }
                        Node::Decision { children, .. } => {
                            for (a, &child) in tree.menus[id].iter().zip(children) {
                                let saved = h.save();
                                h.apply_mut(*a).unwrap();
                                verify(tree, h.clone(), child);
                                h.restore(saved);
                            }
                        }
                    }
                }
                verify(&tree, hand.clone(), 0);
            }
        }
    }
}

fn short_stack_river(stack: u64) -> (Hand, [usize; 2]) {
    let config = Config::new(&[stack; 3], 50, 100).unwrap();
    let mut hand = representative(config, 0, [0, 5, 10, 15, 20]).unwrap();
    while hand.street() != Street::River {
        let actor = hand.actor().unwrap();
        let legal = hand.legal().unwrap();
        let kind = if actor == 0 && hand.street() == Street::Preflop {
            Kind::Fold
        } else if legal.check {
            Kind::Check
        } else {
            Kind::Call
        };
        hand.apply_mut(Action { kind, raise_to: 0 }).unwrap();
    }
    (hand, [1, 2])
}

#[test]
fn counted_tree_matches_the_compiled_tree_and_stops_at_its_cap() {
    for stack in [300, 600, 1000] {
        let (hand, live) = short_stack_river(stack);
        let (mut nodes, mut rows) = (0, 0);
        assert!(count_tree(&mut hand.clone(), live, 100_000, &mut nodes, &mut rows).unwrap());
        let mut tree = Tree {
            nodes: Vec::new(),
            menus: Vec::new(),
            live,
            stacks: live.map(|s| hand.players()[s].stack),
            pot: hand.pot(),
            bb: 100.,
        };
        tree.compile(&mut hand.clone()).unwrap();
        assert_eq!(nodes, tree.nodes.len());
        assert_eq!(rows, tree.menus.iter().map(Vec::len).sum::<usize>());
        let (mut capped, mut capped_rows) = (0, 0);
        assert!(!count_tree(
            &mut hand.clone(),
            live,
            nodes - 1,
            &mut capped,
            &mut capped_rows
        )
        .unwrap());
    }
}
