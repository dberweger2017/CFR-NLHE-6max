use super::*;

pub(super) fn root() -> PublicRoot {
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
fn matched_belief_control_uses_equal_targets_and_reports_residual_identity() {
    let r = root();
    let pairs = [[21, 22], [23, 24], [25, 26], [27, 28], [29, 30], [30, 31]];
    let likelihood = [
        vec![0.1, 0.2, 0.1, 0.2, 0.1, 0.3],
        vec![1. / 6.; 6],
        vec![1. / 6.; 6],
    ];
    let out = belief_control(
        &r,
        &pairs,
        &likelihood,
        SearchMenu::RootCheckMinOpen,
        &[1],
        &[1],
        0.01,
        true,
    )
    .unwrap();
    assert_eq!(out["target_bb"], 0.01);
    assert_eq!(out["reference"]["tolerance_bb"], 0.01);
    for s in 0..2 {
        let d = &out["decomposition"];
        let expected = d["same_profile_law_shift_bb"][s].as_f64().unwrap()
            + d["solver_residual_bb"][s].as_f64().unwrap()
            - d["reference_residual_bb"][s].as_f64().unwrap();
        assert!((out["excess_gain_bb"][s].as_f64().unwrap() - expected).abs() < 1e-12);
    }
    assert_eq!(
        out["qualified"],
        out["deployed"]["target_met"] == true && out["reference"]["qualified"] == true
    );
    let mut zero = likelihood.clone();
    zero[r
        .live
        .iter()
        .position(|s| *s == r.seat)
        .map(|_| r.seat)
        .unwrap()][5] = 0.;
    assert!(belief_control(
        &r,
        &pairs,
        &zero,
        SearchMenu::RootCheckMinOpen,
        &[1],
        &[1],
        0.01,
        true
    )
    .unwrap_err()
    .contains("zero modeled root reach"));
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
    let mut tree = Tree::new(&r.hand, r.live, SearchMenu::Full, 4096);
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
                let mut tree = Tree::new(&hand, live, SearchMenu::Full, 4096);
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

pub(super) fn short_stack_river(stack: u64) -> (Hand, [usize; 2]) {
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
fn minimum_open_expansion_changes_only_the_response_to_the_first_check() {
    let (hand, live) = short_stack_river(10000);
    let base = SearchMenu::Capped(3);
    let expanded = SearchMenu::RootCheckMinOpen;
    assert_eq!(
        base.actions(&hand, true).unwrap(),
        expanded.actions(&hand, true).unwrap()
    );
    let mut tree = Tree::new(&hand, live, expanded, 4096);
    tree.compile(&mut hand.clone()).unwrap();
    let mut changed = 0;
    for (id, path) in tree.paths.iter().enumerate() {
        if tree.menus[id].is_empty() {
            continue;
        }
        let mut state = hand.clone();
        for action in path {
            state.apply_mut(*action).unwrap();
        }
        let old = base.actions(&state, id == 0).unwrap();
        let new = expanded.actions(&state, id == 0).unwrap();
        if old != new {
            changed += 1;
            assert_eq!(path.len(), 1);
            assert_eq!(path[0].kind, Kind::Check);
            assert_eq!(new.len(), old.len() + 1);
            let added: Vec<_> = new.iter().filter(|a| !old.contains(a)).collect();
            assert_eq!(added[0].kind, Kind::Raise);
            assert_eq!(
                added[0].raise_to,
                state.legal().unwrap().raise_to.unwrap().0
            );
        }
    }
    assert_eq!(changed, 1);
    assert_eq!(
        SearchMenu::parse(Some(&json!(expanded.name()))).unwrap(),
        expanded
    );
}

#[test]
fn solve_and_checkpoint_budgets_accept_the_same_declared_endpoints() {
    let endpoints = json!([64, 128, 256, 512, 1024, 2048, 4096, 8192]);
    for endpoint in sweep_list(Some(&endpoints)).unwrap() {
        assert_eq!(fixed_sweeps(&json!(endpoint)).unwrap(), endpoint);
    }
    for invalid in [0, 8193] {
        assert!(fixed_sweeps(&json!(invalid)).is_err());
        assert!(sweep_list(Some(&json!([invalid]))).is_err());
    }
}

#[test]
fn counted_tree_matches_the_compiled_tree_and_stops_at_its_cap() {
    for stack in [300, 600, 1000] {
        let (hand, live) = short_stack_river(stack);
        let (mut nodes, mut rows) = (0, 0);
        assert!(count_tree(
            &mut hand.clone(),
            live,
            SearchMenu::Full,
            100_000,
            &mut nodes,
            &mut rows
        )
        .unwrap());
        let mut tree = Tree::new(&hand, live, SearchMenu::Full, 100_000);
        tree.compile(&mut hand.clone()).unwrap();
        assert_eq!(nodes, tree.nodes.len());
        assert_eq!(rows, tree.menus.iter().map(Vec::len).sum::<usize>());
        let (mut capped, mut capped_rows) = (0, 0);
        assert!(!count_tree(
            &mut hand.clone(),
            live,
            SearchMenu::Full,
            nodes - 1,
            &mut capped,
            &mut capped_rows
        )
        .unwrap());
    }
}

#[test]
fn capped_search_menus_keep_the_root_and_cap_river_raises() {
    let r = root();
    let full_root = SearchMenu::Full.actions(&r.hand, true).unwrap();
    for cap in [2, 3] {
        let menu = SearchMenu::Capped(cap);
        assert_eq!(menu.actions(&r.hand, true).unwrap(), full_root);
        let mut tree = Tree::new(&r.hand, r.live, menu, 4096);
        tree.compile(&mut r.hand.clone()).unwrap();
        let mut full = Tree::new(&r.hand, r.live, SearchMenu::Full, 100_000);
        full.compile(&mut r.hand.clone()).unwrap();
        let full_paths: std::collections::HashSet<_> =
            full.paths.iter().map(|p| path_key(p)).collect();
        for (id, path) in tree.paths.iter().enumerate() {
            assert!(full_paths.contains(&path_key(path)));
            assert!(path.iter().filter(|a| a.kind == Kind::Raise).count() <= cap);
            if id == 0 || tree.menus[id].is_empty() {
                continue;
            }
            let mut hand = r.hand.clone();
            for a in path {
                hand.apply_mut(*a).unwrap();
            }
            let obs = hand.observe(hand.actor().unwrap()).unwrap();
            let production = multi_holdem::menu(&obs);
            for a in &tree.menus[id] {
                // Below the root, no minimum raise unless it is also the pot raise or all-in.
                let label = production.iter().find(|(_, b)| b == a).unwrap().0;
                assert!(
                    a.kind != Kind::Raise || label != 3 || {
                        let legal = obs.legal.unwrap();
                        let matched = obs.players[obs.seat].street_bet + legal.call_amount;
                        let pot: u64 = obs.players.iter().map(|p| p.contributed).sum();
                        let (low, high) = legal.raise_to.unwrap();
                        a.raise_to == (matched + pot + legal.call_amount).clamp(low, high)
                    }
                );
            }
        }
        assert!(tree.nodes.len() < full.nodes.len());
    }
}

#[test]
fn exact_modeled_backend_matches_existing_dense_oracle_on_a_legal_root() {
    let r = root();
    let pairs = [[21, 22], [23, 24], [25, 26], [27, 28], [29, 30], [30, 31]];
    let likelihood = [
        vec![0.1, 0.2, 0.1, 0.2, 0.1, 0.3],
        vec![1. / 6.; 6],
        vec![1. / 6.; 6],
    ];
    let q = exact::qualify(&r, &pairs, &likelihood, SearchMenu::RootCheckMinOpen).unwrap();
    assert_eq!(q["fixed_sweeps"], 64);
    assert!(q["max_leaf_error_bb"].as_f64().unwrap() < 1e-10);
    assert!(q["max_quality_error_bb"].as_f64().unwrap() < 1e-8);
    assert_eq!(q["law"], exact::EXACT_LAW);
    assert!(exact::Backend::parse(Some(&json!("unknown"))).is_err());
}
