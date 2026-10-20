use super::*;
use crate::multi_holdem::menu;
use serde_json::json;
fn state() -> Value {
    json!({"id":"fixture","hero":1,"button":0,"hole":[0,3],"board":[],
        "actions":[[0,"raise",350]],"opponents":["tight-aggressive","hero","random"],
        "street":0,"expected_key":"0".repeat(32),"stratum":"fixture","split":"discovery"})
}
#[test]
fn private_fields_duplicates_and_invalid_public_history_refuse() {
    let valid = state();
    assert!(LegalState::parse(&valid).is_ok());
    for key in ["deck", "opponent_holes", "rewards", "future_board"] {
        let mut bad = valid.clone();
        bad[key] = json!([]);
        assert!(LegalState::parse(&bad).is_err());
    }
    let mut bad = valid.clone();
    bad["hole"] = json!([0, 0]);
    assert!(LegalState::parse(&bad).is_err());
    let mut bad = valid.clone();
    bad["actions"] = json!([[2, "raise", 350]]);
    assert!(LegalState::parse(&bad).is_err());
    let mut bad = valid;
    bad["actions"] = json!([[0, "raise", 200]]);
    assert!(Belief::new(&LegalState::parse(&bad).unwrap()).is_err());
}
#[test]
fn tag_posterior_normalizes_removes_incompatible_weak_hands_and_is_private() {
    let s = LegalState::parse(&state()).unwrap();
    let b = Belief::new(&s).unwrap();
    assert!(b.holding_count() > 0 && b.holding_count() < 1225);
    assert!((b.probabilities.iter().sum::<f64>() - 1.).abs() < 1e-12);
    assert!(!b.holdings.contains(&[1, 2]));
    assert!(b.holdings.contains(&[48, 49]));
    assert!(b.effective_holdings() > 0.);
    let mut rng = rand::rngs::StdRng::seed_from_u64(3541);
    let first = b.draw(&s, &mut rng).unwrap();
    for _ in 0..256 {
        let h = b.draw(&s, &mut rng).unwrap();
        assert_eq!(h.observe(s.hero).unwrap(), first.observe(s.hero).unwrap());
        assert!(b.holdings.contains(&h.observe(0).unwrap().hole));
    }
}
#[test]
fn random_actions_cancel_and_branches_are_legal_zero_sum_and_reproducible() {
    let mut v = state();
    v["opponents"] = json!(["random", "hero", "random"]);
    let s = LegalState::parse(&v).unwrap();
    let b = Belief::new(&s).unwrap();
    assert_eq!(b.holding_count(), 0);
    let mut left = rand::rngs::StdRng::seed_from_u64(42);
    let mut right = rand::rngs::StdRng::seed_from_u64(42);
    for i in 0..24 {
        let h = b.draw(&s, &mut left).unwrap();
        assert_eq!(h, b.draw(&s, &mut right).unwrap());
        let before = h.clone();
        for (_, a) in menu(&h.observe(s.hero).unwrap()) {
            let branch = |h: Hand| {
                let mut bot = Bot::new("check-call", i).unwrap();
                rollout(h, s.hero, a, &s.opponents, i, |o| bot.choose(o)).unwrap()
            };
            let value = branch(h.clone());
            assert_eq!(value, branch(h.clone()));
            assert!((-100. ..=200.).contains(&value));
            assert_eq!(h, before);
        }
    }
}
#[test]
fn likelihood_matches_existing_sampler_without_changing_its_stream() {
    for cheap in [false, true] {
        let seat = if cheap { 2 } else { 0 };
        let offset = (seat + 3 - 1) % 3;
        let mut deck: Vec<_> = (0..52u8).collect();
        for (position, card) in [(offset, 48), (offset + 3, 49)] {
            let old = deck.iter().position(|c| *c == card).unwrap();
            deck.swap(position, old);
        }
        let mut h = Hand::from_deck(Config::new(&[10000; 3], 50, 100).unwrap(), 0, &deck).unwrap();
        if cheap {
            h.apply_mut(Action {
                kind: Kind::Call,
                raise_to: 0,
            })
            .unwrap();
            h.apply_mut(Action {
                kind: Kind::Call,
                raise_to: 0,
            })
            .unwrap();
        }
        let o = h.observe(seat).unwrap();
        let choices = menu(&o);
        for name in ["random", "check-call", "tight-aggressive", "pot-pressure"] {
            let weights: Vec<_> = choices
                .iter()
                .map(|(_, a)| action_likelihood(name, &o, *a).unwrap())
                .collect();
            assert!((weights.iter().sum::<f64>() - 1.).abs() < 1e-12);
            let mut counts = vec![0usize; choices.len()];
            let mut bot = Bot::new(name, 17935).unwrap();
            for _ in 0..40000 {
                let a = bot.choose(&o).unwrap();
                counts[choices.iter().position(|(_, x)| *x == a).unwrap()] += 1;
            }
            for (count, p) in counts.into_iter().zip(weights) {
                assert!((count as f64 / 40000. - p).abs() < 0.015, "{name} {p}");
            }
        }
    }
}

#[test]
fn belief_showdown_share_counts_only_current_live_contenders() {
    for folded in [false, true] {
        let mut v = state();
        v["opponents"] = json!(["random", "hero", "random"]);
        v["street"] = json!(3);
        v["board"] = json!([32, 36, 40, 44, 48]);
        let mut actions = if folded {
            vec![
                json!([0, "fold", 0]),
                json!([1, "call", 0]),
                json!([2, "check", 0]),
            ]
        } else {
            vec![
                json!([0, "call", 0]),
                json!([1, "call", 0]),
                json!([2, "check", 0]),
            ]
        };
        for _ in 0..2 {
            for seat in if folded { vec![1, 2] } else { vec![1, 2, 0] } {
                actions.push(json!([seat, "check", 0]));
            }
        }
        v["actions"] = json!(actions);
        let s = LegalState::parse(&v).unwrap();
        let b = Belief::new(&s).unwrap();
        let mut rng = rand::rngs::StdRng::seed_from_u64(51);
        for _ in 0..16 {
            let (hand, equity) = b.draw_with_equity(&s, &mut rng).unwrap();
            assert_eq!(equity, if folded { 0.5 } else { 1. / 3. });
            assert_eq!(hand.observe(1).unwrap().hole, [0, 3]);
        }
    }
}
