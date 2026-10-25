use super::*;

fn table() -> PolicyTable {
    use crate::{
        multi_cfr::Trainer,
        multi_holdem, multi_policy,
        small_games::{Kind as SmallKind, SmallGame},
    };
    let mut t = Trainer::new(&SmallGame::new(SmallKind::Kuhn, 3), 1, 3, 10, false);
    t.identity = json!({"schema":multi_holdem::SCHEMA,"game":"nlhe-cash","players":3,"stacks":[10000,10000,10000],
        "small_blind":50,"big_blind":100,"menu":multi_holdem::MENU,"card_tables":crate::cards::EQUITY_K50_SHA256,"utility_unit":"big-blind"});
    let path = std::env::temp_dir().join(format!(
        "retained-{}-{}.gz",
        std::process::id(),
        std::thread::current().name().unwrap_or("test")
    ));
    multi_policy::write_trainer(
        &t,
        &"a".repeat(64),
        multi_policy::Mode::Average,
        &path,
        crate::gz::Gzip::Compatible,
    )
    .unwrap();
    let table = PolicyTable::load(&path, &crate::export::sha256_file(&path)).unwrap();
    std::fs::remove_file(path).unwrap();
    table
}
fn fixture(reverse: bool, holding: usize, installed: bool) -> (SessionStore, Arc<Captured>) {
    let mut root = super::super::tests::root();
    root.hand = super::super::tests::short_stack_river(301).0;
    if reverse {
        root.live.reverse();
    }
    root.hole = [[30, 31], [32, 33]][holding];
    let mut tree = Tree::new(
        &root.hand,
        root.live,
        SearchMenu::RootCheckMinOpen,
        SUPPORTED_NODES,
    );
    tree.compile(&mut root.hand.clone()).unwrap();
    let profile: Vec<_> = tree
        .menus
        .iter()
        .enumerate()
        .map(|(i, m)| {
            if m.is_empty() {
                return Vec::new();
            }
            (0..2)
                .flat_map(|h| {
                    let weights: Vec<_> = (0..m.len())
                        .map(|a| ((a + i + h) % m.len() + 1) as f64)
                        .collect();
                    let z: f64 = weights.iter().sum();
                    weights.into_iter().map(move |w| w / z)
                })
                .collect()
        })
        .collect();
    let original = original(&root);
    let cap = Arc::new(
        Captured::new(
            root,
            tree,
            vec![[30, 31], [32, 33]],
            profile,
            original,
            &json!({"checkpoints":[{"target_met":installed}],"algorithm":"fixture","law":{"law":LAW}}),
        )
        .unwrap(),
    );
    let mut store = SessionStore::new(&"a".repeat(64)).unwrap();
    store.active = Some(Active {
        hand_id: "public-hand".into(),
        handle: "fixture-handle".into(),
        captured: installed.then(|| cap.clone()),
        fallback_root: (!installed).then(|| cap.clone()),
        last_actions: array(&cap.original["actions"]).unwrap().clone(),
        off_tree: false,
        fallback_reason: (!installed).then(|| "nonconverged fixture".into()),
    });
    (store, cap)
}
fn request(obs: Value) -> Value {
    json!({"mode":"retained-continue","hand_id":"public-hand","handle":"fixture-handle","observation":obs})
}

#[test]
fn every_on_tree_hero_row_is_original_bits_in_both_orientations_and_holdings() {
    let table = table();
    let tables = fixture_tables();
    for reverse in [false, true] {
        for holding in 0..2 {
            let (base, cap) = fixture(reverse, holding, true);
            let mut tested = 0;
            let mut all_in = false;
            for (i, path) in cap.tree.paths.iter().enumerate() {
                if !matches!(cap.tree.nodes[i],Node::Decision{actor,..}if cap.root.live[actor]==cap.root.seat)
                {
                    continue;
                }
                let mut store = SessionStore::new(&"a".repeat(64)).unwrap();
                store.active = base.active.clone();
                let obs = observation_after(&cap, path).unwrap();
                all_in |= obs["players"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|p| p[0] == 0 && p[3] == false);
                let out = store.request(&request(obs), &table, &tables).unwrap();
                let bits: Vec<_> = out["probabilities"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|p| p.as_f64().unwrap().to_bits())
                    .collect();
                assert_eq!(
                    bits,
                    cap.row(i)
                        .unwrap()
                        .iter()
                        .map(|p| p.to_bits())
                        .collect::<Vec<_>>()
                );
                assert_eq!(out["solver_advances"], 0);
                assert_eq!(out["installed_search"], true);
                tested += 1;
            }
            assert!(tested > 3);
            assert!(all_in);
        }
    }
}

#[test]
fn replay_rejects_illegal_payments_identity_changes_rollback_and_stale_sessions() {
    let table = table();
    let tables = fixture_tables();
    let (mut store, cap) = fixture(false, 0, true);
    let path = cap
        .tree
        .paths
        .iter()
        .find(|p| {
            !p.is_empty()
                && observation_after(&cap, p)
                    .ok()
                    .is_some_and(|v| cap.replay(&v).is_ok())
        })
        .unwrap();
    let valid = observation_after(&cap, path).unwrap();
    for key in [
        "board", "button", "seat", "hole", "players", "legal", "actions",
    ] {
        let mut bad = valid.clone();
        bad[key] = Value::Null;
        assert!(
            store.request(&request(bad), &table, &tables).is_err(),
            "{key}"
        );
    }
    let mut bad = valid.clone();
    let n = bad["actions"].as_array().unwrap().len();
    bad["actions"][n - 1][4] = json!(999999);
    assert!(store.request(&request(bad), &table, &tables).is_err());
    let mut bad = valid.clone();
    bad["opponent_cards"] = json!([1, 2]);
    assert!(store.request(&request(bad), &table, &tables).is_err());
    store.request(&request(valid), &table, &tables).unwrap();
    assert!(store
        .request(
            &request(observation_after(&cap, &[]).unwrap()),
            &table,
            &tables
        )
        .is_err());
    let mut stale = request(Value::Null);
    stale["hand_id"] = json!("another");
    assert!(store.request(&stale, &table, &tables).is_err());
    let release =
        json!({"mode":"retained-release","hand_id":"public-hand","handle":"fixture-handle"});
    store.request(&release, &table, &tables).unwrap();
    assert!(store.request(&release, &table, &tables).is_err());
    let mut restarted = SessionStore::new(&"a".repeat(64)).unwrap();
    assert!(restarted.request(&release, &table, &tables).is_err());
}

#[test]
fn off_tree_and_unconverged_use_labeled_blueprint_without_solving() {
    let table = table();
    let tables = fixture_tables();
    let (mut store, cap) = fixture(false, 0, true);
    let mut path = None;
    for prefix in &cap.tree.paths {
        let mut h = cap.root.hand.clone();
        for a in prefix {
            h.apply_mut(*a).unwrap();
        }
        if h.actor().is_none() || h.actor() == Some(cap.root.seat) {
            continue;
        }
        let obs = h.observe(h.actor().unwrap()).unwrap();
        for (_, a) in multi_holdem::menu(&obs) {
            let mut next = prefix.clone();
            next.push(a);
            if cap.tree.paths.contains(&next) {
                continue;
            }
            if observation_after(&cap, &next)
                .ok()
                .is_some_and(|v| cap.replay(&v).is_ok())
            {
                path = Some(next);
                break;
            }
        }
        if path.is_some() {
            break;
        }
    }
    let obs = observation_after(&cap, &path.expect("omitted legal response")).unwrap();
    let out = store
        .request(&request(obs.clone()), &table, &tables)
        .unwrap();
    assert_eq!(out["installed_search"], false);
    assert_eq!(out["lookup_tag"], 0);
    assert_eq!(out["solver_advances"], 0);
    assert!(out["fallback_reason"]
        .as_str()
        .unwrap()
        .contains("off-tree"));
    let again = store.request(&request(obs), &table, &tables).unwrap();
    assert_eq!(out, again);
    let (mut store, cap) = fixture(false, 0, false);
    let out = store
        .request(
            &request(observation_after(&cap, &[]).unwrap()),
            &table,
            &tables,
        )
        .unwrap();
    assert_eq!(out["installed_search"], false);
    assert_eq!(out["lookup_tag"], 0);
    assert_eq!(out["solver_advances"], 0);
}

#[test]
fn evaluation_branches_share_profile_bytes_but_isolate_fallback_and_history() {
    let table = table();
    let tables = fixture_tables();
    let (base, cap) = fixture(false, 0, true);
    let mut omitted = None;
    for prefix in &cap.tree.paths {
        let mut h = cap.root.hand.clone();
        for a in prefix {
            h.apply_mut(*a).unwrap();
        }
        let Some(actor) = h.actor() else {
            continue;
        };
        if actor == cap.root.seat {
            continue;
        }
        for (_, action) in multi_holdem::menu(&h.observe(actor).unwrap()) {
            let mut path = prefix.clone();
            path.push(action);
            if !cap.tree.paths.contains(&path)
                && observation_after(&cap, &path)
                    .ok()
                    .is_some_and(|o| cap.replay(&o).is_ok())
            {
                omitted = Some(path);
                break;
            }
        }
        if omitted.is_some() {
            break;
        }
    }
    let root_request = request(observation_after(&cap, &[]).unwrap());
    let mut off = base.evaluation_fork();
    assert!(Arc::ptr_eq(
        base.active.as_ref().unwrap().captured.as_ref().unwrap(),
        off.active.as_ref().unwrap().captured.as_ref().unwrap()
    ));
    let fallback = off
        .request(
            &request(observation_after(&cap, &omitted.unwrap()).unwrap()),
            &table,
            &tables,
        )
        .unwrap();
    assert_eq!(fallback["installed_search"], false);
    assert_eq!(fallback["solver_advances"], 0);
    assert!(off.request(&root_request, &table, &tables).is_err());
    let mut sibling = base.evaluation_fork();
    let root = sibling.request(&root_request, &table, &tables).unwrap();
    assert_eq!(root["installed_search"], true);
    assert_eq!(root["solver_advances"], 0);
    assert_eq!(root["profile_sha256"], cap.metadata["profile_sha256"]);
    assert!(!base.active.as_ref().unwrap().off_tree);
    assert_eq!(
        base.active.as_ref().unwrap().last_actions,
        array(&cap.original["actions"]).unwrap().clone()
    );
}

#[test]
fn live_evaluation_view_shares_payload_and_preserves_root_after_all_queries() {
    use crate::river::live::whole_hand::EvaluationPolicy;
    let table = Arc::new(table());
    let tables = fixture_tables();
    for installed in [true, false] {
        let (base, cap) = fixture(false, 0, installed);
        let context = json!({"hand_id":"public-hand","handle":"fixture-handle"});
        let before = Arc::strong_count(&cap);
        let view = EvaluationPolicy::capture(table.clone(), &base, &context).unwrap();
        assert_eq!(Arc::strong_count(&cap), before + 1);
        assert_eq!(view.binding()["installed"], installed);
        assert_eq!(
            view.binding()["profile_sha256"],
            cap.metadata["profile_sha256"]
        );
        let root_progress = base.active.as_ref().unwrap().last_actions.clone();
        let mut count = 0;
        for path in &cap.tree.paths {
            let mut hand = cap.root.hand.clone();
            for action in path {
                hand.apply_mut(*action).unwrap();
            }
            if hand.actor() != Some(cap.root.seat) {
                continue;
            }
            let mut o = hand.observe(cap.root.seat).unwrap();
            o.hole = cap.root.hole;
            // The retained-row fixture has short-stack simulator scaffolding;
            // direct validated blueprint queries use the table's game identity.
            o.config = table.config();
            let actual = view.row(&o, &tables, true).unwrap();
            let mut independent = base.evaluation_fork();
            let expected = independent
                .request(
                    &request(observation_after(&cap, path).unwrap()),
                    &table,
                    &tables,
                )
                .unwrap();
            let p: Vec<f64> = serde_json::from_value(expected["probabilities"].clone()).unwrap();
            assert_eq!(
                actual
                    .probabilities
                    .iter()
                    .map(|p| p.to_bits())
                    .collect::<Vec<_>>(),
                p.iter().map(|p| p.to_bits()).collect::<Vec<_>>()
            );
            let off = view.row(&o, &tables, false).unwrap();
            assert_eq!(off.source, "blueprint");
            assert_eq!(
                off.probabilities,
                table.distribution(&o, &tables).unwrap().0
            );
            count += 1;
        }
        assert!(count > 1);
        if installed {
            let mut omitted = None;
            for prefix in &cap.tree.paths {
                let mut h = cap.root.hand.clone();
                for a in prefix {
                    h.apply_mut(*a).unwrap();
                }
                let Some(actor) = h.actor() else {
                    continue;
                };
                if actor == cap.root.seat {
                    continue;
                }
                for (_, action) in multi_holdem::menu(&h.observe(actor).unwrap()) {
                    let mut path = prefix.clone();
                    path.push(action);
                    if !cap.tree.paths.contains(&path)
                        && observation_after(&cap, &path)
                            .ok()
                            .is_some_and(|o| cap.replay(&o).is_ok())
                    {
                        omitted = Some(path);
                        break;
                    }
                }
                if omitted.is_some() {
                    break;
                }
            }
            let mut h = cap.root.hand.clone();
            for a in omitted.expect("omitted response") {
                h.apply_mut(a).unwrap();
            }
            let mut o = h.observe(cap.root.seat).unwrap();
            o.hole = cap.root.hole;
            o.config = table.config();
            let row = view.row(&o, &tables, true).unwrap();
            assert_eq!(row.source, "off-tree-blueprint");
            assert_eq!(
                row.probabilities,
                table.distribution(&o, &tables).unwrap().0
            );
            let mut root = cap.root.hand.observe(cap.root.seat).unwrap();
            root.hole = cap.root.hole;
            assert_eq!(view.row(&root, &tables, true).unwrap().source, "retained");
        }
        assert_eq!(base.active.as_ref().unwrap().last_actions, root_progress);
        assert!(!base.active.as_ref().unwrap().off_tree);
        assert_eq!(Arc::strong_count(&cap), before + 1);
        let mut wrong = context.clone();
        wrong["handle"] = json!("wrong");
        assert!(EvaluationPolicy::capture(table.clone(), &base, &wrong).is_err());
    }
}

#[test]
fn live_evaluation_capture_rejects_a_progressed_session() {
    use crate::river::live::whole_hand::EvaluationPolicy;
    let table = Arc::new(table());
    let tables = fixture_tables();
    let (mut base, cap) = fixture(false, 0, true);
    let context = json!({"hand_id":"public-hand","handle":"fixture-handle"});
    let path = cap
        .tree
        .paths
        .iter()
        .find(|path| {
            !path.is_empty()
                && observation_after(&cap, path)
                    .ok()
                    .is_some_and(|o| cap.replay(&o).is_ok())
        })
        .unwrap();
    base.request(
        &request(observation_after(&cap, path).unwrap()),
        &table,
        &tables,
    )
    .unwrap();
    assert!(EvaluationPolicy::capture(table, &base, &context).is_err());
}

#[test]
fn inline_expected_values_match_independent_terminal_enumeration() {
    use crate::river::live::whole_hand::{observation_request, EvaluationPolicy};
    let table = Arc::new(table());
    let tables = fixture_tables();
    for installed in [true, false] {
        let mut root = super::super::tests::root();
        root.hand =
            representative(Config::new(&[10000; 3], 50, 100).unwrap(), 0, root.board).unwrap();
        // A small remaining river stack in a genuinely100BB-identity hand.
        for (kind, raise_to) in [(Kind::Raise, 9699), (Kind::Call, 0), (Kind::Fold, 0)] {
            root.hand.apply_mut(Action { kind, raise_to }).unwrap();
        }
        while root.hand.street() != Street::River {
            root.hand
                .apply_mut(Action {
                    kind: Kind::Check,
                    raise_to: 0,
                })
                .unwrap();
        }
        root.seat = root.hand.actor().unwrap();
        root.live = root
            .hand
            .players()
            .iter()
            .enumerate()
            .filter_map(|(i, p)| (!p.folded).then_some(i))
            .collect::<Vec<_>>()
            .try_into()
            .unwrap();
        root.hole = root.hand.observe(root.seat).unwrap().hole;
        root.hole.sort_unstable();
        let mut tree = Tree::new(
            &root.hand,
            root.live,
            SearchMenu::RootCheckMinOpen,
            SUPPORTED_NODES,
        );
        tree.compile(&mut root.hand.clone()).unwrap();
        let profile = tree
            .menus
            .iter()
            .map(|m| {
                if m.is_empty() {
                    vec![]
                } else {
                    vec![1. / m.len() as f64; m.len()]
                }
            })
            .collect();
        let original = original(&root);
        let pair = root.hole;
        let cap=Arc::new(Captured::new(root,tree,vec![pair],profile,original,
            &json!({"checkpoints":[{"target_met":installed}],"algorithm":"fixture","law":{"law":LAW}})).unwrap());
        let mut base = SessionStore::new(&"a".repeat(64)).unwrap();
        base.active = Some(Active {
            hand_id: "public-hand".into(),
            handle: "fixture-handle".into(),
            captured: installed.then(|| cap.clone()),
            fallback_root: (!installed).then(|| cap.clone()),
            last_actions: array(&cap.original["actions"]).unwrap().clone(),
            off_tree: false,
            fallback_reason: (!installed).then(|| "nonconverged fixture".into()),
        });
        let context = json!({"hand_id":"public-hand","handle":"fixture-handle"});
        let view = EvaluationPolicy::capture(table.clone(), &base, &context).unwrap();
        let mut ids = [1, 2, 1];
        let mut wrong = cap.root.hand.observe(cap.root.seat).unwrap();
        wrong.hole = [30, 31];
        assert!(view.validate_root(&wrong).is_err());
        ids[cap.root.seat] = 0;
        // The folded seat's identity is arbitrary; assign a real permutation.
        let mut next = 1;
        for (seat, id) in ids.iter_mut().enumerate() {
            if seat != cap.root.seat {
                *id = next;
                next += 1;
            }
        }
        let value = crate::arena_expectation::root(
            &cap.root.hand,
            &ids,
            &["peer".into(), "peer".into()],
            &view,
            &table,
            &tables,
            0,
        )
        .unwrap();
        assert_eq!(value["complete_contrast"], true);
        assert_eq!(value["solver_advances"], 0);
        assert_eq!(value["profile_reconstructions"], 0);
        if !installed {
            assert_eq!(value["contrast_chips"], 0.);
            assert!(value["on"].is_null());
            continue;
        }
        let mut expected = [0., 0.];
        for enabled in [false, true] {
            let mut queue = std::collections::VecDeque::from([(cap.root.hand.clone(), 1.)]);
            let mut leaves = Vec::new();
            while let Some((h, mass)) = queue.pop_front() {
                if let Some(s) = h.settlement() {
                    leaves.push(mass * s.rewards[cap.root.seat] as f64);
                    continue;
                }
                let o = h.observe(h.actor().unwrap()).unwrap();
                let (actions, probabilities) = if ids[o.seat] == 0 && enabled {
                    let mut branch = base.evaluation_fork();
                    let response = branch
                        .request(&request(observation_request(&o).unwrap()), &table, &tables)
                        .unwrap();
                    let actions = array(&response["actions"])
                        .unwrap()
                        .iter()
                        .map(|v| Action {
                            kind: kind(&v[0]).unwrap(),
                            raise_to: uint(&v[1]).unwrap(),
                        })
                        .collect::<Vec<_>>();
                    (
                        actions,
                        serde_json::from_value::<Vec<f64>>(response["probabilities"].clone())
                            .unwrap(),
                    )
                } else {
                    (
                        multi_holdem::menu(&o).into_iter().map(|(_, a)| a).collect(),
                        table.distribution(&o, &tables).unwrap().0,
                    )
                };
                for (action, p) in actions.iter().zip(probabilities) {
                    if p > 0. {
                        let mut n = h.clone();
                        n.apply_mut(*action).unwrap();
                        queue.push_back((n, mass * p));
                    }
                }
                assert!(queue.len() < 100000);
            }
            expected[enabled as usize] = leaves.iter().sum();
            let arm = if enabled { "on" } else { "off" };
            assert!(
                (value[arm]["expected_chips"].as_f64().unwrap() - expected[enabled as usize]).abs()
                    < 1e-8
            );
        }
        assert!(
            (value["contrast_chips"].as_f64().unwrap() - (expected[1] - expected[0])).abs() < 1e-8
        );
        assert!(!base.active.as_ref().unwrap().off_tree);
        assert_eq!(
            base.active.as_ref().unwrap().last_actions,
            *array(&cap.original["actions"]).unwrap()
        );
    }
}

fn fixture_tables() -> EquityTables {
    let keys = std::array::from_fn(|s| {
        let board = &[0, 5, 10, 15, 20][..s + 3];
        let mut keys = std::collections::BTreeSet::new();
        for a in 0..52 {
            for b in a + 1..52 {
                if !board.contains(&a) && !board.contains(&b) {
                    keys.insert(hu20_buckets::class_key(&[a, b], board));
                }
            }
        }
        keys.into_iter().collect()
    });
    EquityTables::policy_test_fixture(keys)
}

fn original(root: &PublicRoot) -> Value {
    let mut actions = Vec::new();
    for e in root.hand.history() {
        if let Event::Action {
            street,
            actor,
            action,
            paid,
        } = e
        {
            actions.push(json!([
                actor,
                *street as u64,
                action.kind.name(),
                action.raise_to,
                paid
            ]));
        }
    }
    let legal = root.hand.legal().unwrap();
    json!({"format":"nplayer-live-river-v1","button":root.hand.button(),"board":root.board,
        "seat":root.seat,"hole":root.hole,"actions":actions,
        "players":root.hand.players().iter().map(|p|json!([p.stack,p.street_bet,p.contributed,p.folded])).collect::<Vec<_>>(),
        "legal":{"check":legal.check,"call_amount":legal.call_amount,"raise_to":legal.raise_to},"sweeps":1})
}

#[test]
fn begin_nonconvergence_and_zero_reach_fallback_keep_real_blueprint_semantics() {
    let mut table = table();
    let tables = fixture_tables();
    let root = super::super::tests::root();
    let mut obs = original(&root);
    obs["algorithm"] = json!("dcfr-1.5-0-2");
    obs["search_menu"] = json!("pot-jam-cap3-root-check-min-v1");
    obs["target"] = json!({"pot_fraction":1e-15,"cap_bb":1e-15});
    let begin = json!({"mode":"retained-begin","hand_id":"public","observation":obs});
    let mut store = SessionStore::new(&"a".repeat(64)).unwrap();
    let out = store.request(&begin, &table, &tables).unwrap();
    assert_eq!(out["session"]["installed_search"], false);
    assert!(out["session"]["fallback_reason"]
        .as_str()
        .unwrap()
        .contains("quality"));
    assert_eq!(out["lookup_tag"], 0);
    let release =
        json!({"mode":"retained-release","hand_id":"public","handle":out["session"]["handle"]});
    store.request(&release, &table, &tables).unwrap();
    let (prior, action) = root
        .prior
        .iter()
        .find(|(h, _)| h.actor() == Some(root.seat))
        .unwrap();
    let mut view = prior.observe(root.seat).unwrap();
    view.hole = root.hole;
    let d = multi_holdem::observation_decision(&view, &tables);
    let menu = multi_holdem::menu(&view);
    let chosen = menu.iter().position(|(_, a)| a == action).unwrap();
    let mut p = vec![1. / (menu.len() - 1) as f64; menu.len()];
    p[chosen] = 0.;
    if let crate::multi_policy::Rows::Json(rows) = &mut table.rows {
        rows.insert(
            d.key,
            crate::multi_policy::Row {
                owner: d.owner as u8,
                street: d.street as u8,
                code: d.code,
                probabilities: p.into_boxed_slice(),
                original_average_mass: Some(true),
            },
        );
    } else {
        panic!("fixture representation");
    }
    let out = store.request(&begin, &table, &tables).unwrap();
    assert_eq!(out["session"]["installed_search"], false);
    assert_eq!(
        out["session"]["fallback_reason"],
        "own holding has zero modeled root reach"
    );
    assert!(out["session"]["binding"]["profile_sha256"].is_null());
    assert_eq!(out["lookup_tag"], 0);
}

#[test]
fn offline_full_menu_audit_keeps_the_captured_profile_and_fallback_policy_separate() {
    let table = table();
    let tables = fixture_tables();
    // A nonconverged root must audit the actual blueprint fallback, while
    // preserving the produced unconverged strategy as a separate diagnostic.
    let mut store = SessionStore::new(&"a".repeat(64)).unwrap();
    // Expand the fixture's likelihood support to all legal holdings to match
    // the live loader; the two-holding synthetic session is not a real solve.
    let r = super::super::tests::root();
    let obs = original(&r);
    let mut observation = obs.clone();
    observation["mode"] = json!("solve");
    observation["sweeps"] = json!(1);
    observation["algorithm"] = json!("dcfr-1.5-0-2");
    observation["stop_at_target"] = json!(true);
    observation["target"] = json!({"pot_fraction":1e-12,"cap_bb":1e-12});
    observation["search_menu"] = json!("pot-jam-cap3-root-check-min-v1");
    store.active = None;
    let begin = store
        .request(
            &json!({"mode":"retained-begin","hand_id":"audit-fixture","observation":observation}),
            &table,
            &tables,
        )
        .unwrap();
    let ctx = &begin["session"];
    let digest = ctx["binding"]["profile_sha256"].clone();
    let audit=store.request(&json!({"mode":"retained-full-menu-audit","hand_id":"audit-fixture","handle":ctx["handle"]}),&table,&tables).unwrap();
    assert_eq!(audit["profile_sha256"], digest);
    assert_eq!(audit["solver_advances"], 0);
    assert_eq!(audit["profile_unchanged"], true);
    assert_eq!(audit["installed_search"], false);
    for law in ["projected", "exact_modeled"] {
        assert_eq!(
            audit["laws"][law]["actual_deployed_policy"]["quality"],
            audit["laws"][law]["blueprint_quality"]
        );
        assert_eq!(
            audit["laws"][law]["actual_deployed_policy"]["hero_worst_case_change_bb"],
            0.
        );
    }
    assert!(
        audit["capped_exact_oracle"]["max_error_bb"]
            .as_f64()
            .unwrap()
            < 1e-8
    );
    assert_eq!(
        store
            .active
            .as_ref()
            .unwrap()
            .fallback_root
            .as_ref()
            .unwrap()
            .metadata["profile_sha256"],
        digest
    );
}

#[test]
fn exact_backend_installs_its_own_law_and_retains_original_rows_without_resolving() {
    let table = table();
    let tables = fixture_tables();
    let root = super::super::tests::root();
    let mut observation = original(&root);
    observation["mode"] = json!("solve");
    observation["belief_backend"] = json!("exact-folded-prefix-v1");
    observation["algorithm"] = json!("dcfr-1.5-0-2");
    observation["sweeps"] = json!(1);
    observation["stop_at_target"] = json!(true);
    // Deliberately loose fixture target installs a known one-sweep profile.
    observation["target"] = json!({"pot_fraction":1000.,"cap_bb":1000.});
    observation["search_menu"] = json!("pot-jam-cap3-root-check-min-v1");
    let mut store = SessionStore::new(&"a".repeat(64)).unwrap();
    let begin = store
        .request(
            &json!({"mode":"retained-begin","hand_id":"exact-fixture","observation":observation}),
            &table,
            &tables,
        )
        .unwrap();
    let ctx = &begin["session"];
    assert_eq!(ctx["installed_search"], true);
    assert_eq!(ctx["binding"]["belief_law"], exact::EXACT_LAW);
    assert_eq!(begin["law"]["projection_applied"], false);
    let audit = store
        .request(
            &json!({"mode":"retained-audit","hand_id":"exact-fixture","handle":ctx["handle"]}),
            &table,
            &tables,
        )
        .unwrap();
    assert_eq!(audit["solver_advances"], 0);
    assert!(audit["checked_rows"].as_u64().unwrap() > 1);
    assert_eq!(audit["profile_sha256"], ctx["binding"]["profile_sha256"]);
}

#[test]
fn snapshot_roundtrip_checks_bits_model_root_work_and_quality_bindings() {
    let table = table();
    let tables = fixture_tables();
    let root = super::super::tests::root();
    let mut original = original(&root);
    original["mode"] = json!("solve");
    original["algorithm"] = json!("dcfr-1.5-0-2");
    original["search_menu"] = json!("pot-jam-cap3-root-check-min-v1");
    original["checkpoints"] = json!([1]);
    original["target"] = json!({"pot_fraction":1e-15,"cap_bb":1e-15});
    let mut store = SessionStore::new(&"a".repeat(64)).unwrap();
    let begin = store
        .request(
            &json!({"mode":"retained-begin","hand_id":"snapshot","observation":original}),
            &table,
            &tables,
        )
        .unwrap();
    let export=store.request(&json!({"mode":"retained-export-profile","hand_id":"snapshot","handle":begin["session"]["handle"]}),&table,&tables).unwrap();
    let bytes = serde_json::to_vec(&export).unwrap();
    let parsed: Value = serde_json::from_slice(&bytes).unwrap();
    let cap = Captured::restore(&parsed, &"a".repeat(64), &table, &tables).unwrap();
    assert_eq!(
        cap.metadata["profile_sha256"],
        export["binding"]["profile_sha256"]
    );
    assert_eq!(cap.snapshot(&"a".repeat(64)), export);
    assert!(Captured::restore(&parsed, &"b".repeat(64), &table, &tables).is_err());
    let mut bad = parsed.clone();
    bad["installed_search"] = json!(!cap.installed);
    assert!(Captured::restore(&bad, &"a".repeat(64), &table, &tables).is_err());
    let mut bad = parsed.clone();
    bad["binding"]["root_sha256"] = json!("changed");
    assert!(Captured::restore(&bad, &"a".repeat(64), &table, &tables).is_err());
    let mut bad = parsed.clone();
    bad["binding"]["work"]["sweeps"] = json!(2);
    assert!(Captured::restore(&bad, &"a".repeat(64), &table, &tables).is_err());
    let mut bad = parsed;
    bad["profile"][0][0] = json!(0.1234);
    assert!(Captured::restore(&bad, &"a".repeat(64), &table, &tables).is_err());
}

#[test]
fn exact_response_audit_preserves_profile_and_actual_blueprint_fallback() {
    let table = table();
    let tables = fixture_tables();
    let root = super::super::tests::root();
    let pairs = vec![[21, 22], [23, 24], [25, 26], [27, 28], [29, 30], [30, 31]];
    let mut tree = Tree::new(
        &root.hand,
        root.live,
        SearchMenu::RootCheckMinOpen,
        SUPPORTED_NODES,
    );
    tree.compile(&mut root.hand.clone()).unwrap();
    let profile: Vec<_> = tree
        .menus
        .iter()
        .map(|m| {
            if m.is_empty() {
                vec![]
            } else {
                (0..pairs.len())
                    .flat_map(|_| (0..m.len()).map(|j| if j == 0 { 1. } else { 0. }))
                    .collect()
            }
        })
        .collect();
    let before = profile_digest(&profile);
    let out = harms::diagnose(&root, &pairs, &tree, &profile, false, &table, &tables).unwrap();
    assert_eq!(before, profile_digest(&profile));
    assert_eq!(out["solver_advances"], 0);
    assert_eq!(out["actual"]["metrics"], out["blueprint"]);
    assert!(!out["actual"]["responses"].as_array().unwrap().is_empty());
    for r in out["actual"]["responses"].as_array().unwrap() {
        assert_eq!(r["hero_blueprint_after_entry_changed_rows"], 0);
        assert!(r["leave_one_out_wc_improvement_bb"].as_f64().unwrap() >= -1e-8);
    }
}

const CHECK: Action = Action { kind: Kind::Check, raise_to: 0 };
const BET: Action = Action { kind: Kind::Raise, raise_to: 100 };

/// A deployed-style solve request at the hero's first river decision after `taken`.
fn second_to_act(taken: Action, target: f64, sweeps: u64) -> Value {
    let (mut obs, _) = super::super::tests::river_request(&[taken]);
    obs["mode"] = json!("solve");
    obs["algorithm"] = json!("dcfr-1.5-0-2");
    obs["search_menu"] = json!("pot-jam-cap3-root-min-responses-v1");
    obs["sweeps"] = json!(sweeps);
    obs["checkpoints"] = json!([sweeps]);
    obs["stop_at_target"] = json!(true);
    obs["target"] = json!({"pot_fraction":target,"cap_bb":target});
    obs
}

fn begin(store: &mut SessionStore, obs: &Value, table: &PolicyTable, tables: &EquityTables) -> Value {
    store
        .request(&json!({"mode":"retained-begin","hand_id":"h","observation":obs}), table, tables)
        .unwrap()
}

#[test]
fn second_to_act_root_fixes_the_opponent_and_plays_the_taken_child() {
    let (table, tables) = (table(), fixture_tables());
    for (taken, first) in [(CHECK, "check"), (BET, "fold")] {
        let mut obs = second_to_act(taken, 1e6, 8);
        obs["debug"] = json!(true);
        let out = request_impl(&obs, &table, &tables, None).unwrap();
        // The fixture blueprint has no river rows, so the opponent's fixed root is uniform.
        let k = out["prepared_game"]["nodes"][0]["children"].as_array().unwrap().len();
        let root = out["average"][0].as_array().unwrap();
        assert!(root.iter().all(|p| (p.as_f64().unwrap() - 1. / k as f64).abs() < 1e-15),
            "the opponent's first action is fixed to its blueprint row");
        assert_eq!(out["actions"][0][0], first, "the hero row comes from the child of the taken action");
        let installed = begin(&mut SessionStore::new(&"a".repeat(64)).unwrap(), &second_to_act(taken, 1e6, 8), &table, &tables);
        assert_eq!(installed["session"]["installed_search"], true);
        assert_eq!(installed["actions"][0][0], first);
    }
}

#[test]
fn an_unconverged_second_to_act_root_falls_back_at_the_hero_decision() {
    let (table, tables) = (table(), fixture_tables());
    for (taken, first) in [(CHECK, "check"), (BET, "fold")] {
        let mut store = SessionStore::new(&"a".repeat(64)).unwrap();
        let out = begin(&mut store, &second_to_act(taken, 1e-15, 1), &table, &tables);
        assert_eq!(out["session"]["installed_search"], false);
        assert_eq!(out["actions"][0][0], first, "blueprint row at the hero's decision, not the river start");
        let p: f64 = out["probabilities"].as_array().unwrap().iter().map(|x| x.as_f64().unwrap()).sum();
        assert!((p - 1.).abs() < 1e-12);
    }
}

#[test]
fn second_to_act_continuation_replays_the_opponent_action() {
    let (table, tables) = (table(), fixture_tables());
    let mut store = SessionStore::new(&"a".repeat(64)).unwrap();
    let out = begin(&mut store, &second_to_act(CHECK, 1e6, 8), &table, &tables);
    assert_eq!(out["session"]["installed_search"], true);
    // Hero bets, the opponent raises: the hero's next decision must replay check, bet, raise.
    let r = super::super::tests::root();
    let mut hand = r.hand.clone();
    hand.apply_mut(CHECK).unwrap();
    let bet = Action { kind: Kind::Raise, raise_to: hand.pot() };
    hand.apply_mut(bet).unwrap();
    let obs = hand.observe(hand.actor().unwrap()).unwrap();
    let raise = multi_holdem::menu(&obs).into_iter().map(|(_, a)| a).find(|a| a.kind == Kind::Raise).unwrap();
    let (mut later, _) = super::super::tests::river_request(&[CHECK, bet, raise]);
    for key in ["mode", "algorithm", "search_menu", "sweeps", "checkpoints", "stop_at_target", "target"] {
        later.as_object_mut().unwrap().remove(key);
    }
    let next = store
        .request(&json!({"mode":"retained-continue","hand_id":"h","handle":out["session"]["handle"],"observation":later}), &table, &tables)
        .unwrap();
    assert_eq!(next["solver_advances"], 0);
    assert_eq!(next["actions"][0][0], "fold", "the hero faces the opponent's raise");
}

#[test]
fn the_played_subtree_alone_sets_quality_and_the_scaled_target() {
    let (table, tables) = (table(), fixture_tables());
    for taken in [CHECK, BET] {
        let mut obs = second_to_act(taken, 1e6, 8);
        obs["debug"] = json!(true);
        obs["stop_at_target"] = json!(false);
        let out = request_impl(&obs, &table, &tables, None).unwrap();
        // Rebuild the prepared game and recompute quality with and without settling.
        let g = &out["prepared_game"];
        let f = |v: &Value| v.as_f64().unwrap();
        let ranges: [Vec<Holding>; 2] = std::array::from_fn(|s| {
            g["ranges"][s].as_array().unwrap().iter()
                .map(|h| Holding { cards: [h[0].as_u64().unwrap() as u8, h[1].as_u64().unwrap() as u8], weight: f(&h[2]) })
                .collect()
        });
        let nodes: Vec<Node> = g["nodes"].as_array().unwrap().iter().map(|n| match n.get("terminal") {
            Some(t) => Node::Leaf(Terminal { base: f(&t[0]), win0: f(&t[1]), tie0: f(&t[2]) }),
            None => Node::Decision {
                actor: n["actor"].as_u64().unwrap() as usize,
                children: n["children"].as_array().unwrap().iter().map(|c| c.as_u64().unwrap() as usize).collect(),
            },
        }).collect();
        let board: Vec<u8> = g["board"].as_array().unwrap().iter().map(|c| c.as_u64().unwrap() as u8).collect();
        let average: Vec<Vec<f64>> = serde_json::from_value(out["average"].clone()).unwrap();
        let Node::Decision { actor, children } = nodes[0].clone() else { panic!() };
        let k = children.len();
        let r = super::super::tests::root();
        let a = multi_holdem::menu(&r.hand.observe(r.hand.actor().unwrap()).unwrap())
            .iter()
            .position(|(_, x)| *x == taken)
            .unwrap();
        let child = children[a];
        let game = || Game::new(board.clone().try_into().unwrap(), ranges.clone(), nodes.clone(), f(&g["root_pot_bb"])).unwrap();
        let mut fixed = vec![None; nodes.len()];
        fixed[0] = Some(average[0].clone());
        // Expected settled set, by walking parents: every decision node not below the hero's child.
        let mut parent = vec![usize::MAX; nodes.len()];
        for (id, n) in nodes.iter().enumerate() {
            if let Node::Decision { children, .. } = n {
                for &c in children {
                    parent[c] = id;
                }
            }
        }
        let played = |mut id: usize| loop {
            if id == child {
                break true;
            }
            if id == 0 {
                break false;
            }
            id = parent[id];
        };
        let decision = |id: usize| matches!(nodes[id], Node::Decision { .. });
        let expected: Vec<bool> = (0..nodes.len()).map(|id| decision(id) && !played(id)).collect();
        assert!(expected[0] && !expected[child]);
        assert!(expected[1..].iter().any(|&s| s), "an unplayed branch has decision nodes to settle");
        assert!((0..nodes.len()).any(|id| id != child && decision(id) && played(id)), "the played subtree goes past the hero");
        let mut settled = Solver::new(game(), fixed.clone()).unwrap();
        settled.set_settled(expected).unwrap();
        let mut unsettled = Solver::new(game(), fixed).unwrap();
        let (q, r) = (settled.quality(&average).unwrap(), unsettled.quality(&average).unwrap());
        assert_eq!(out["quality"], q, "in-solve quality judges the played subtree only");
        assert_ne!(q["best_response_gains_bb"], r["best_response_gains_bb"], "settling changes the gains here");
        // The target scales with the opponent's modeled share of the taken action.
        let (mut mass, mut observed_mass) = (0., 0.);
        for h in &ranges[1 - actor] {
            for (i, o) in ranges[actor].iter().enumerate() {
                if h.cards.iter().all(|c| !o.cards.contains(c)) {
                    let pair_mass = h.weight * o.weight;
                    mass += pair_mass;
                    observed_mass += pair_mass * average[0][i * k + a];
                }
            }
        }
        let share = observed_mass / mass;
        let base = quality_target(obs.get("target"), f(&g["root_pot_bb"])).unwrap();
        assert!(share < 1.);
        assert!((f(&out["target_bb"]) - base * share).abs() <= 1e-12 * base, "target scales with the share");
    }
}

#[test]
fn an_opponent_action_the_blueprint_never_takes_falls_back() {
    let mut table = table();
    let tables = fixture_tables();
    let r = super::super::tests::root();
    let mut view = r.hand.observe(r.hand.actor().unwrap()).unwrap();
    let menu = multi_holdem::menu(&view);
    let bet = menu.iter().position(|(_, a)| *a == BET).unwrap();
    let mut p = vec![1. / (menu.len() - 1) as f64; menu.len()];
    p[bet] = 0.;
    let crate::multi_policy::Rows::Json(rows) = &mut table.rows else { panic!("fixture representation") };
    for a in (0..52u8).filter(|c| !r.board.contains(c)) {
        for b in (a + 1..52).filter(|c| !r.board.contains(c)) {
            view.hole = [a, b];
            let d = multi_holdem::observation_decision(&view, &tables);
            rows.insert(
                d.key,
                crate::multi_policy::Row {
                    owner: d.owner as u8,
                    street: d.street as u8,
                    code: d.code,
                    probabilities: p.clone().into_boxed_slice(),
                    original_average_mass: Some(true),
                },
            );
        }
    }
    let mut store = SessionStore::new(&"a".repeat(64)).unwrap();
    let out = begin(&mut store, &second_to_act(BET, 1e6, 8), &table, &tables);
    assert_eq!(out["session"]["installed_search"], false);
    assert_eq!(out["session"]["fallback_reason"], "observed opponent river action has zero modeled likelihood");
    assert!(out["session"]["binding"]["profile_sha256"].is_null());
}

#[test]
fn only_declared_solve_failures_fall_back() {
    assert!(falls_back("observed opponent river action has zero modeled likelihood"));
    assert!(falls_back("own holding has zero modeled root reach"));
    assert!(falls_back("own holding has zero modeled reach after opponent river action"));
    assert!(falls_back("unsupported river tree"));
    assert!(!falls_back("invalid fixed profile"));
    assert!(!falls_back(FIRST_TO_ACT_ONLY));
}

#[test]
fn audits_exports_and_omitted_evaluation_refuse_second_to_act_roots() {
    let (table, tables) = (table(), fixture_tables());
    let mut store = SessionStore::new(&"a".repeat(64)).unwrap();
    let out = begin(&mut store, &second_to_act(BET, 1e6, 8), &table, &tables);
    for mode in ["retained-audit", "retained-export-profile", "retained-harm-diagnosis", "retained-full-menu-audit"] {
        let r = store.request(&json!({"mode":mode,"hand_id":"h","handle":out["session"]["handle"]}), &table, &tables);
        assert_eq!(r, Err(FIRST_TO_ACT_ONLY.to_string()), "{mode}");
    }
    let mut omitted = second_to_act(BET, 1e6, 8);
    omitted["omitted"] = json!(true);
    assert!(request_impl(&omitted, &table, &tables, None).unwrap_err().contains("first-to-act"));
}

#[test]
fn an_opponent_action_blocked_by_the_actual_hero_falls_back() {
    let mut table = table();
    let r = super::super::tests::root();
    let mut obs = second_to_act(BET, 0.01, 128);
    obs["target"] = json!({"pot_fraction":0.01,"cap_bb":0.1});
    obs["checkpoints"] = json!([8, 16, 32, 64, 128]);
    let hero = [32, 33];
    obs["hole"] = json!(hero);
    let dir = std::env::temp_dir().join(format!("pr429-blocker-fixture-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    for (s, name) in ["flop", "turn", "river"].iter().enumerate() {
        let board = &r.board[..s + 3];
        let mut mapping = std::collections::BTreeMap::new();
        for a in 0..52u8 {
            for b in a + 1..52 {
                if board.contains(&a) || board.contains(&b) {
                    continue;
                }
                let value = if s == 2 && (hero.contains(&a) || hero.contains(&b)) {
                    1
                } else {
                    0
                };
                let prior = mapping.insert(hu20_buckets::class_key(&[a, b], board), value);
                assert!(prior.is_none_or(|p| p == value), "fixture class collision");
            }
        }
        let keys: Vec<_> = mapping.keys().copied().collect();
        let assignments: Vec<_> = mapping.values().copied().collect();
        hu20_buckets::BucketTable::new(s as u32 + 1, 50, &keys, &assignments)
            .write(&dir.join(format!("{name}-k50.bin")))
            .unwrap();
    }
    let tables = EquityTables::load(&dir, true).unwrap();
    std::fs::remove_dir_all(&dir).unwrap();
    let opponent = r.hand.actor().unwrap();
    let mut view = r.hand.observe(opponent).unwrap();
    let menu = multi_holdem::menu(&view);
    let bet = menu.iter().position(|(_, a)| *a == BET).unwrap();
    let check = menu.iter().position(|(_, a)| *a == CHECK).unwrap();
    let crate::multi_policy::Rows::Json(rows) = &mut table.rows else {
        panic!()
    };
    for a in 0..52u8 {
        for b in a + 1..52 {
            if r.board.contains(&a) || r.board.contains(&b) {
                continue;
            }
            view.hole = [a, b];
            let d = multi_holdem::observation_decision(&view, tables);
            let mut p = vec![0.; menu.len()];
            p[if hero.contains(&a) || hero.contains(&b) {
                bet
            } else {
                check
            }] = 1.;
            rows.insert(
                d.key,
                crate::multi_policy::Row {
                    owner: d.owner as u8,
                    street: d.street as u8,
                    code: d.code,
                    probabilities: p.into_boxed_slice(),
                    original_average_mass: Some(true),
                },
            );
        }
    }
    // Every opponent hand compatible with [32,33] checks. Only blocked hands bet.
    for a in 0..52u8 {
        for b in a + 1..52 {
            if r.board.contains(&a)
                || r.board.contains(&b)
                || hero.contains(&a)
                || hero.contains(&b)
            {
                continue;
            }
            view.hole = [a, b];
            assert_eq!(blueprint_row(&view, &table, tables).unwrap().0[bet], 0.);
        }
    }
    let decision = reconstruct(&obs, table.config())
        .unwrap()
        .decision()
        .unwrap();
    let mut hero_obs = decision.observe(decision.actor().unwrap()).unwrap();
    hero_obs.hole = hero;
    let blueprint = blueprint_row(&hero_obs, &table, tables).unwrap().0;
    let out = begin(
        &mut SessionStore::new(&"a".repeat(64)).unwrap(),
        &obs,
        &table,
        tables,
    );
    assert_eq!(
        out["session"]["installed_search"], false,
        "zero conditional likelihood for actual hero must fall back"
    );
    assert_eq!(
        out["session"]["fallback_reason"],
        "own holding has zero modeled reach after opponent river action"
    );
    assert_eq!(out["probabilities"], json!(blueprint));
    assert!(out["session"]["binding"]["profile_sha256"].is_null());
}
