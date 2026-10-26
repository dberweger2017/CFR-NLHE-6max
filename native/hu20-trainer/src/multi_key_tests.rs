use super::*;

fn golden_case(n: usize, button: usize, street: u8, max: bool) -> (Hand, Vec<u8>) {
    let stacks: Vec<u64> = (0..n)
        .map(|i| {
            if max {
                crate::nplayer::MAX_CHIPS - i as u64 * 1000
            } else {
                2000 + i as u64 * 500
            }
        })
        .collect();
    let mut hand = Hand::from_deck(
        Config::new(&stacks, 50, 100).unwrap(),
        button,
        &(0..52).collect::<Vec<_>>(),
    )
    .unwrap();
    let mut first = true;
    loop {
        let actor = hand.actor().unwrap();
        let obs = hand.observe(actor).unwrap();
        if obs.street as u8 == street {
            break;
        }
        let choices = menu(&obs);
        let action = if first {
            choices
                .iter()
                .find(|(_, a)| a.kind == Kind::Raise)
                .unwrap()
                .1
        } else {
            choices
                .iter()
                .find(|(_, a)| matches!(a.kind, Kind::Call | Kind::Check))
                .unwrap()
                .1
        };
        first = false;
        hand.apply_mut(action).unwrap();
    }
    let actor = hand.actor().unwrap();
    let obs = hand.observe(actor).unwrap();
    let cards = if street == 0 {
        card_class(&obs, None)
    } else {
        vec![street, 17, 0]
    };
    (hand, cards)
}

#[test]
fn exact_key_bytes_are_versioned_for_history_live_order_and_both_hashes() {
    let expected = [
        [
            "ff90b2a12441404719308daee214ea80",
            "b507e476fe97267f10507da7f2b74b40",
            "3481de42ad9019321834f25ec36a42b7",
            "6b84f0779f3f18e818d6a84e29ded74f",
        ],
        [
            "fbd5cc62954b4e0f486321a91efc78b8",
            "72ad68092c22fc6cde55fd41e8ebbb20",
            "dad03d1c511c09fc392e3d02c85d31c5",
            "0edafe17656458523017a538ac67458b",
        ],
        [
            "8d6d25daff2b27d51d5e52233e7a7798",
            "7a0894a0750f9524cf18a15676d42415",
            "76ab2c9338380c8a396021320f477a13",
            "35c93286af0cddb95856d8761c1cc94b",
        ],
        [
            "5a3885c4112b8fc9dc775315cbdc3c23",
            "f0b88006259a91dd705d4b78d3fb737f",
            "5f301ac3df8e83fbf24081c772a824ab",
            "42036d06862e5cc38ea9c9a3586a6950",
        ],
    ];
    for ((n, button, street, max), expected) in [
        (3, 0, 0, false),
        (2, 1, 1, false),
        (6, 4, 3, false),
        (6, 5, 2, true),
    ]
    .into_iter()
    .zip(expected)
    {
        let (hand, cards) = golden_case(n, button, street, max);
        let obs = hand.observe(hand.actor().unwrap()).unwrap();
        let choices = menu(&obs);
        let keys = [KeySchema::History,KeySchema::LiveOrder,KeySchema::CompactBlake,KeySchema::CompactXxh3].map(|s| {
            crate::multi_checkpoint::key_hex(&decision_from_cards(s, &obs, &cards, &choices).key)
        });
        assert_eq!(keys, expected);
    }
    assert_eq!(
        key_encoding_binding(KeySchema::CompactBlake)["digest"],
        "a485aefbcb11673c78be58b240766be8"
    );
    assert_eq!(
        key_encoding_binding(KeySchema::CompactXxh3)["digest"],
        "53d384092437ae3f274e2ee5ef6f8eb0"
    );
}

#[test]
fn hidden_cards_and_unrevealed_runouts_never_change_compact_keys() {
    let config = Config::new(&[2000; 3], 50, 100).unwrap();
    let a: Vec<u8> = (0..52).collect();
    let mut b = a.clone();
    b.swap(0, 4);
    b.swap(20, 40); // Acting seat0 receives positions2/5; only other/future cards change.
    let one = Hand::from_deck(config, 0, &a).unwrap();
    let two = Hand::from_deck(config, 0, &b).unwrap();
    assert_eq!(one.observe(0).unwrap().hole, two.observe(0).unwrap().hole);
    for schema in KeySchema::ALL {
        let x = observation_decision_with_tables(
            schema,
            &one.observe(one.actor().unwrap()).unwrap(),
            None,
        );
        let y = observation_decision_with_tables(
            schema,
            &two.observe(two.actor().unwrap()).unwrap(),
            None,
        );
        assert_eq!(x, y);
    }
}

#[test]
fn compact_preflop_learning_matches_history_and_resumes_across_threads() {
    use crate::multi_cfr::{Sampling, Trainer};
    use std::sync::{Arc, Mutex};
    type Mapping = Arc<Mutex<std::collections::HashMap<crate::cfr::Key, crate::cfr::Key>>>;
    struct Fixture {
        schema: KeySchema,
        mapping: Mapping,
    }
    #[derive(Clone)]
    struct FixtureState {
        state: CashState,
        mapping: Mapping,
    }
    impl Game for Fixture {
        type State = FixtureState;
        fn players(&self) -> usize {
            3
        }
        fn identity(&self) -> Value {
            json!({"game":"preflop-key-fixture","players":3,"schema":self.schema.name()})
        }
        fn sample(&self, rng: &mut rand::rngs::StdRng) -> FixtureState {
            let mut deck: Vec<u8> = (0..52).collect();
            deck.shuffle(rng);
            FixtureState {
                state: CashState {
                    hand: Hand::from_deck(
                        Config::new(&[2000; 3], 50, 100).unwrap(),
                        rng.gen_range(0..3),
                        &deck,
                    )
                    .unwrap(),
                    tables: None,
                    schema: self.schema,
                },
                mapping: self.mapping.clone(),
            }
        }
    }
    impl State for FixtureState {
        type Saved = Saved;
        fn players(&self) -> usize {
            3
        }
        fn decision(&self) -> Option<Decision> {
            if !self.state.hand.board().is_empty() {
                return None;
            }
            let actor = self.state.hand.actor()?;
            let obs = self.state.hand.observe(actor).unwrap();
            let d = self.state.decision().unwrap();
            let legacy = observation_decision_with_tables(KeySchema::History, &obs, None);
            let previous = self.mapping.lock().unwrap().insert(d.key, legacy.key);
            assert!(previous.is_none_or(|p| p == legacy.key));
            Some(d)
        }
        fn payoff(&self, p: usize) -> f64 {
            if self.state.hand.finished() {
                self.state.payoff(p)
            } else {
                0.
            }
        }
        fn save(&self) -> Saved {
            self.state.save()
        }
        fn restore(&mut self, s: Saved) {
            self.state.restore(s)
        }
        fn apply(&mut self, a: usize) {
            self.state.apply(a)
        }
    }
    fn rows(
        t: &Trainer,
        map: &Mapping,
    ) -> std::collections::BTreeMap<crate::cfr::Key, (u8, u8, u16, u64, Vec<u64>, Option<Vec<u64>>)>
    {
        let m = map.lock().unwrap();
        t.table
            .iter()
            .map(|(k, e)| {
                (
                    m[&k],
                    (
                        e.actor,
                        e.street,
                        e.code,
                        e.visits,
                        e.regrets.iter().map(|v| v.to_bits()).collect(),
                        e.average
                            .as_ref()
                            .map(|a| a.iter().map(|v| v.to_bits()).collect()),
                    ),
                )
            })
            .collect()
    }
    let dir = std::env::temp_dir().join(format!("compact-training-parity-{}", std::process::id()));
    std::fs::create_dir(&dir).unwrap();
    let mut reference = None;
    for schema in KeySchema::EXACT_HISTORY {
        for threads in [1, 2, 4] {
            let pool = rayon::ThreadPoolBuilder::new()
                .num_threads(threads)
                .build()
                .unwrap();
            let game = Fixture {
                schema,
                mapping: Default::default(),
            };
            let mut trainer = Trainer::new(&game, 327, 3, usize::MAX, false);
            trainer.sampling = Sampling::Path;
            trainer.roots_per_seat = 2;
            pool.install(|| {
                for _ in 0..12 {
                    trainer.step_fast(&game);
                }
            });
            let path = dir.join(format!("{}-{threads}.gz", schema.option()));
            crate::multi_checkpoint::save(&trainer, &path, crate::gz::Gzip::Compatible).unwrap();
            let mut resumed = crate::multi_checkpoint::load(&path).unwrap();
            pool.install(|| {
                for _ in 0..12 {
                    trainer.step_fast(&game);
                    resumed.step_fast(&game);
                }
            });
            let a = rows(&trainer, &game.mapping);
            let b = rows(&resumed, &game.mapping);
            assert_eq!(a, b);
            let counts = crate::multi_checkpoint::counts_json(&trainer.counts);
            let result = (a, counts, trainer.iteration);
            if let Some(old) = &reference {
                assert_eq!(old, &result);
            } else {
                reference = Some(result);
            }
        }
    }
    std::fs::remove_dir_all(dir).unwrap();
}
