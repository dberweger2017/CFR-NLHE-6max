//! Offline privileged evaluator. Player callbacks receive only Observation.
use hu20_trainer::{
    cards::EquityTables,
    export::sha256_file,
    game::Kind,
    multi_arena::action_likelihood,
    multi_holdem::menu,
    multi_policy::PolicyTable,
    nplayer::{Action, Config, Hand, Observation},
    policy_expectation::{evaluate, Evaluation, Row},
    river::live::{
        whole_hand::{observation_request, MENU},
        SessionStore,
    },
};
use serde_json::{json, Value};
use std::{fs::OpenOptions, io::Write, path::Path, time::Instant};

fn actions(v: &Value) -> Result<Vec<Action>, String> {
    v.as_array()
        .ok_or("actions array")?
        .iter()
        .map(|a| {
            Ok(Action {
                kind: match a[0].as_str() {
                    Some("fold") => Kind::Fold,
                    Some("check") => Kind::Check,
                    Some("call") => Kind::Call,
                    Some("raise") => Kind::Raise,
                    _ => return Err("action kind".into()),
                },
                raise_to: a[1].as_u64().ok_or("action amount")?,
            })
        })
        .collect()
}
fn write(path: &Path, v: &Value) -> Result<(), String> {
    let mut f = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|e| e.to_string())?;
    writeln!(f, "{v}").map_err(|e| e.to_string())
}
fn evaluated(v: Evaluation, seconds: f64) -> Value {
    json!({"complete":v.complete,"expected_chips":v.expected_chips,"visited":v.visited,
        "terminals":v.terminals,"policy_rows":v.policy_rows,"seconds":seconds})
}
fn script(name: &str, o: &Observation<'_>) -> Result<Row, String> {
    let mut choices: Vec<_> = menu(o).into_iter().map(|(_, a)| a).collect();
    // Scripts can emit a legal matched-pot action even if a menu omits it.
    if let Some((low, high)) = o.legal.ok_or("script legal bounds")?.raise_to {
        let legal = o.legal.unwrap();
        let pot: u64 = o.players.iter().map(|p| p.contributed).sum();
        let to = (o.players[o.seat].street_bet + legal.call_amount + pot + legal.call_amount)
            .clamp(low, high);
        let a = Action {
            kind: Kind::Raise,
            raise_to: to,
        };
        if !choices.contains(&a) {
            choices.push(a);
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
fn blueprint(
    table: &PolicyTable,
    o: &Observation<'_>,
    tables: &EquityTables,
) -> Result<Row, String> {
    let (probabilities, _) = table.distribution(o, tables)?;
    Ok(Row {
        actions: menu(o).into_iter().map(|(_, a)| a).collect(),
        probabilities,
        source: "blueprint",
    })
}

fn root(
    input: &Value,
    focal: &PolicyTable,
    peer: &PolicyTable,
    tables: &EquityTables,
    model: &str,
) -> Result<Value, String> {
    let tick = Instant::now();
    let deck: Vec<u8> = serde_json::from_value(input["deck"].clone()).map_err(|e| e.to_string())?;
    let mut hand = Hand::from_deck(
        Config::new(&[10000; 3], 50, 100)?,
        input["button"].as_u64().ok_or("button")? as usize,
        &deck,
    )?;
    for a in actions(&input["prefix_actions"])? {
        hand.apply_mut(a)?;
    }
    let identities: Vec<usize> =
        serde_json::from_value(input["identities"].clone()).map_err(|e| e.to_string())?;
    if identities.len() != 3 || (0..3).any(|i| !identities.contains(&i)) {
        return Err("seat identities".into());
    }
    let seat = identities.iter().position(|x| *x == 0).unwrap();
    if hand.actor() != Some(seat) {
        return Err("focal root actor differs".into());
    }
    let o = hand.observe(seat)?;
    if hu20_trainer::river::live::whole_hand::eligibility(&o) != "eligible" {
        return Err("saved root not eligible".into());
    }
    let mut request = observation_request(&o)?;
    request["mode"] = json!("solve");
    request["search_menu"] = json!(MENU);
    request["algorithm"] = json!("dcfr-1.5-0-2");
    request["sweeps"] = json!(2048);
    request["checkpoints"] = json!([8, 16, 32, 64, 128, 256, 512, 1024, 2048]);
    request["stop_at_target"] = json!(true);
    request["omitted"] = json!(false);
    request["target"] = json!({"pot_fraction":0.01,"cap_bb":0.1});
    let mut store = SessionStore::new(model)?;
    let hand_id = format!(
        "hand/{}/{}",
        input["block"].as_u64().ok_or("block")?,
        input["permutation"].as_u64().ok_or("permutation")?
    );
    let begin = store.request(
        &json!({"mode":"retained-begin","hand_id":hand_id,"observation":request}),
        focal,
        tables,
    )?;
    let expected = &input["expected"];
    if begin["session"]["binding"]["profile_sha256"] != expected["profile_sha256"]
        || begin["session"]["installed_search"] != expected["installed"]
        || begin["session"]["fallback_reason"] != expected["fallback_reason"]
        || begin["actions"] != expected["actions"]
        || begin["probabilities"] != expected["probabilities"]
        || begin["sweeps"] != expected["sweeps"]
        || begin["nodes"] != expected["nodes"]
    {
        return Err("original root/profile/work/distribution differs".into());
    }
    let prepare_seconds = tick.elapsed().as_secs_f64();
    if begin["session"]["installed_search"] == false {
        // A failed installation latches actual blueprint for the entire river.
        // Both policies are identical, so their contrast cancels symbolically.
        return Ok(
            json!({"id":input["id"],"identity_verified":true,"complete_contrast":true,
            "method":"identical-blueprint-policy-cancellation","contrast_chips":0.,
            "profile_sha256":expected["profile_sha256"],"prepare_seconds":prepare_seconds,
            "on":Value::Null,"off":Value::Null,"total_seconds":tick.elapsed().as_secs_f64()}),
        );
    }
    let opponents: Vec<String> =
        serde_json::from_value(input["opponents"].clone()).map_err(|e| e.to_string())?;
    if opponents.len() != 2 {
        return Err("two opponents required".into());
    }
    let handle = begin["session"]["handle"].clone();
    let mut results = [Value::Null, Value::Null];
    let order = if input["ordinal"].as_u64().ok_or("ordinal")? % 2 == 0 {
        [false, true]
    } else {
        [true, false]
    };
    for enabled in order {
        let policy = |observation: &Observation<'_>| -> Result<Row, String> {
            match identities[observation.seat] {
                0 if enabled => {
                    let mut branch = store.evaluation_fork();
                    let response = branch.request(
                        &json!({"mode":"retained-continue","hand_id":hand_id,
                        "handle":handle,"observation":observation_request(observation)?}),
                        focal,
                        tables,
                    )?;
                    if response["solver_advances"] != 0 {
                        return Err("evaluation advanced solver".into());
                    }
                    Ok(Row {
                        actions: actions(&response["actions"])?,
                        probabilities: serde_json::from_value(response["probabilities"].clone())
                            .map_err(|e| e.to_string())?,
                        source: if response["installed_search"] == true {
                            "retained"
                        } else {
                            "off-tree-blueprint"
                        },
                    })
                }
                0 => blueprint(focal, observation, tables),
                identity => {
                    let spec = &opponents[identity - 1];
                    if spec == "peer" {
                        blueprint(peer, observation, tables)
                    } else {
                        script(
                            spec.strip_prefix("bot=").ok_or("opponent spec")?,
                            observation,
                        )
                    }
                }
            }
        };
        let start = Instant::now();
        let value = evaluate(&hand, seat, 200000, &policy)?;
        results[enabled as usize] = evaluated(value, start.elapsed().as_secs_f64());
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
    store.request(
        &json!({"mode":"retained-release","hand_id":hand_id,"handle":handle}),
        focal,
        tables,
    )?;
    Ok(
        json!({"id":input["id"],"identity_verified":true,"complete_contrast":complete,
        "method":"full-positive-support-enumeration","contrast_chips":contrast,
        "profile_sha256":expected["profile_sha256"],"prepare_seconds":prepare_seconds,
        "off":results[0],"on":results[1],"total_seconds":tick.elapsed().as_secs_f64()}),
    )
}

fn run() -> Result<(), String> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 2 {
        return Err("nplayer_river_expectation MANIFEST.json".into());
    }
    let manifest: Value =
        serde_json::from_slice(&std::fs::read(&args[1]).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
    if manifest["format"] != "river-conditional-evaluation-v1"
        || manifest["max_nodes_per_arm"] != 200000
    {
        return Err("manifest format/work limit".into());
    }
    let loading = Instant::now();
    let mut loaded = Vec::new();
    let mut pins = Vec::new();
    for alias in ["focal", "peer"] {
        let m = &manifest["models"][alias];
        let p = Path::new(m["path"].as_str().ok_or("model path")?);
        let digest = m["sha256"].as_str().ok_or("model SHA")?;
        let (table, report) = PolicyTable::load_profiled(p, digest, false)?;
        if table.config() != Config::new(&[10000; 3], 50, 100)? {
            return Err("requires three-player100BB".into());
        }
        pins.push(json!({"alias":alias,"sha256":digest,"load_seconds":report.total_seconds}));
        loaded.push(table);
    }
    let tables = EquityTables::load(
        Path::new(manifest["k50"].as_str().ok_or("K50 path")?),
        false,
    )?;
    write(
        Path::new(manifest["startup"].as_str().ok_or("startup path")?),
        &json!({"model_pins":pins,
        "model_and_k50_seconds":loading.elapsed().as_secs_f64(),"binary_sha256":sha256_file(Path::new(&args[0]))}),
    )?;
    let mut output = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(manifest["output"].as_str().ok_or("output path")?)
        .map_err(|e| e.to_string())?;
    let cases = manifest["roots"].as_array().ok_or("roots")?;
    for (i, c) in cases.iter().enumerate() {
        let v = root(
            c,
            &loaded[0],
            &loaded[1],
            &tables,
            manifest["models"]["focal"]["sha256"].as_str().unwrap(),
        )?;
        writeln!(output, "{v}").map_err(|e| e.to_string())?;
        output.flush().map_err(|e| e.to_string())?;
        println!(
            "{}",
            json!({"completed":i+1,"total":cases.len(),"id":c["id"],"complete_contrast":v["complete_contrast"],"seconds":v["total_seconds"]})
        );
    }
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use hu20_trainer::multi_arena::Bot;

    #[test]
    fn script_rows_match_frozen_sampling_at_check_and_facing_bet_states() {
        let mut h = Hand::from_deck(
            Config::new(&[500; 3], 50, 100).unwrap(),
            0,
            &(0..52).collect::<Vec<_>>(),
        )
        .unwrap();
        while h.street() != hu20_trainer::game::Street::River {
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
