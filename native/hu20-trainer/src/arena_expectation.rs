//! Privileged evaluation host. Actual policies receive only their own Observation.
use crate::{
    cards::EquityTables,
    game::Kind,
    multi_arena::action_likelihood,
    multi_holdem::menu,
    multi_policy::PolicyTable,
    nplayer::{Action, Hand, Observation},
    policy_expectation::{evaluate, Evaluation, Row},
    river::live::whole_hand::EvaluationPolicy,
};
use serde_json::{json, Value};
use std::time::Instant;

fn evaluated(value: Evaluation, seconds: f64) -> Value {
    json!({"complete":value.complete,"expected_chips":value.expected_chips,
        "visited":value.visited,"terminals":value.terminals,"policy_rows":value.policy_rows,"seconds":seconds})
}

fn script(name: &str, o: &Observation<'_>) -> Result<Row, String> {
    let mut choices: Vec<_> = menu(o).into_iter().map(|(_, a)| a).collect();
    if let Some((low, high)) = o.legal.ok_or("script legal bounds")?.raise_to {
        let legal = o.legal.unwrap();
        let pot: u64 = o.players.iter().map(|p| p.contributed).sum();
        let to = (o.players[o.seat].street_bet + legal.call_amount + pot + legal.call_amount)
            .clamp(low, high);
        let action = Action {
            kind: Kind::Raise,
            raise_to: to,
        };
        if !choices.contains(&action) {
            choices.push(action);
        }
    }
    let probabilities = choices
        .iter()
        .map(|a| action_likelihood(name, o, *a))
        .collect::<Result<_, _>>()?;
    Ok(Row {
        actions: choices,
        probabilities,
        source: "script",
    })
}

/// The privileged Hand stays here and in the walker; no callback captures it.
pub fn root(
    hand: &Hand,
    identities: &[usize; 3],
    opponents: &[String; 2],
    focal: &EvaluationPolicy,
    peer: &PolicyTable,
    tables: &EquityTables,
    ordinal: u64,
) -> Result<Value, String> {
    let tick = Instant::now();
    let seat = identities
        .iter()
        .position(|id| *id == 0)
        .ok_or("focal seat")?;
    if hand.actor() != Some(seat) || !identities.contains(&1) || !identities.contains(&2) {
        return Err("expectation requires acting focal and unique identities".into());
    }
    let binding = focal.binding();
    focal.validate_root(&hand.observe(seat)?)?;
    if binding["installed"] == false {
        return Ok(
            json!({"complete_contrast":true,"method":"identical-blueprint-policy-cancellation",
            "contrast_chips":0.,"profile_sha256":binding["profile_sha256"],"on":Value::Null,"off":Value::Null,
            "solver_advances":0,"profile_reconstructions":0,"total_seconds":tick.elapsed().as_secs_f64()}),
        );
    }
    let mut results = [Value::Null, Value::Null];
    for enabled in if ordinal % 2 == 0 {
        [false, true]
    } else {
        [true, false]
    } {
        let policy = |o: &Observation<'_>| -> Result<Row, String> {
            match identities[o.seat] {
                0 => focal.row(o, tables, enabled),
                id => {
                    let spec = &opponents[id - 1];
                    if spec == "peer" {
                        let (probabilities, _) = peer.distribution(o, tables)?;
                        Ok(Row {
                            actions: menu(o).into_iter().map(|(_, a)| a).collect(),
                            probabilities,
                            source: "blueprint",
                        })
                    } else {
                        script(spec.strip_prefix("bot=").ok_or("opponent spec")?, o)
                    }
                }
            }
        };
        let start = Instant::now();
        let result = evaluate(hand, seat, 200000, &policy)?;
        results[enabled as usize] = evaluated(result, start.elapsed().as_secs_f64());
    }
    let complete = results.iter().all(|v| v["complete"] == true);
    let contrast = if complete {
        json!(
            results[1]["expected_chips"].as_f64().unwrap()
                - results[0]["expected_chips"].as_f64().unwrap()
        )
    } else {
        Value::Null
    };
    Ok(
        json!({"complete_contrast":complete,"method":"full-positive-support-enumeration",
        "contrast_chips":contrast,"profile_sha256":binding["profile_sha256"],"off":results[0],"on":results[1],
        "solver_advances":0,"profile_reconstructions":0,"total_seconds":tick.elapsed().as_secs_f64()}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::multi_arena::Bot;
    use crate::nplayer::Config;

    #[test]
    fn script_rows_match_frozen_sampling_at_check_and_facing_bet_states() {
        let mut h = Hand::from_deck(
            Config::new(&[500; 3], 50, 100).unwrap(),
            0,
            &(0..52).collect::<Vec<_>>(),
        )
        .unwrap();
        while h.street() != crate::game::Street::River {
            let legal = h.legal().unwrap();
            h.apply_mut(Action {
                kind: if legal.check { Kind::Check } else { Kind::Call },
                raise_to: 0,
            })
            .unwrap();
        }
        for facing in [false, true] {
            if facing {
                h.apply_mut(Action {
                    kind: Kind::Raise,
                    raise_to: 100,
                })
                .unwrap();
            }
            let o = h.observe(h.actor().unwrap()).unwrap();
            for name in ["random", "check-call", "tight-aggressive", "pot-pressure"] {
                let row = script(name, &o).unwrap();
                assert!((row.probabilities.iter().sum::<f64>() - 1.).abs() < 1e-12);
                let mut bot = Bot::new(name, 2026102239002).unwrap();
                let mut counts = vec![0; row.actions.len()];
                for _ in 0..25000 {
                    let a = bot.choose(&o).unwrap();
                    counts[row
                        .actions
                        .iter()
                        .position(|x| *x == a)
                        .expect("missing actual script action")] += 1;
                }
                for (count, p) in counts.into_iter().zip(row.probabilities) {
                    assert!((count as f64 / 25000. - p).abs() < 0.008, "{name}");
                }
            }
        }
    }
}
