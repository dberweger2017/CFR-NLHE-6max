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
