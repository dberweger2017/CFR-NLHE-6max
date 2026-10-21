//! Privileged whole-hand host; focal search receives acting Observation only.
use hu20_trainer::{
    cards::EquityTables,
    export::sha256_file,
    multi_arena::{stream_seed, Bot, PERMUTATIONS},
    multi_policy::{Policy, PolicyTable},
    nplayer::{Config, Event, Hand},
    river::live::whole_hand::WholeHandPolicy,
};
use rand::{seq::SliceRandom, SeedableRng};
use rayon::prelude::*;
use serde_json::{json, Value};
use std::{io::Write, path::Path, sync::Arc, time::Instant};
struct Model {
    table: Arc<PolicyTable>,
    pin: Value,
}
enum Player {
    Focal(WholeHandPolicy),
    Peer(Policy),
    Script(Bot),
}
fn snapshot(hand: &Hand) -> Value {
    let legal = hand
        .legal()
        .map(|l| json!({"check":l.check,"call":l.call_amount,"raise_to":l.raise_to}));
    json!({"actor":hand.actor(),"finished":hand.finished(),"board":hand.board(),
        "street":if hand.finished(){None}else{Some(hand.street().name())},"pot":hand.pot(),
        "wager":if hand.finished(){None}else{Some(hand.wager())},"min_raise":if hand.finished(){None}else{Some(hand.min_raise())},
        "players":hand.players().iter().map(|p|json!([p.stack,p.street_bet,p.contributed,p.folded])).collect::<Vec<_>>(),
        "holes":(0..3).map(|p|hand.observe(p).unwrap().hole).collect::<Vec<_>>(),"legal":legal,
        "rewards":hand.settlement().map(|s|s.rewards[..3].to_vec())})
}

fn block(
    index: u64,
    root: u64,
    tables: &EquityTables,
    models: &[Model; 2],
    opponents: &[String; 2],
    enabled: bool,
) -> Result<(Vec<u8>, Vec<u8>), String> {
    let config = Config::new(&[10000; 3], 50, 100)?;
    let mut deck: Vec<u8> = (0..52).collect();
    deck.shuffle(&mut rand::rngs::StdRng::seed_from_u64(stream_seed(
        root, b"deck", index, 0,
    )));
    let mut trace = Vec::new();
    let mut metrics = Vec::new();
    let button = index as usize % 3;
    for (permutation, ids) in PERMUTATIONS.iter().enumerate() {
        // Public ordinal only: the deal seed never enters search context.
        let hand_id = format!("hand/{index}/{permutation}");
        let mut players = vec![Player::Focal(WholeHandPolicy::new(
            models[0].table.clone(),
            models[0].pin["sha256"].as_str().unwrap(),
            stream_seed(root, b"action", index, 0),
            hand_id.clone(),
            enabled,
        )?)];
        for id in 1..3 {
            let seed = stream_seed(root, b"action", index, id as u64);
            let spec = &opponents[id - 1];
            players.push(if spec == "peer" {
                Player::Peer(Policy::new(models[1].table.clone(), seed))
            } else {
                Player::Script(Bot::new(
                    spec.strip_prefix("bot=").ok_or("opponent alias")?,
                    seed,
                )?)
            });
        }
        let mut hand = Hand::from_deck(config, button, &deck)?;
        let mut states = vec![snapshot(&hand)];
        let mut actors = Vec::new();
        let mut actions = Vec::new();
        let mut ledgers = Vec::new();
        while let Some(actor) = hand.actor() {
            if actions.len() >= 10000 {
                return Err("hand action bound".into());
            }
            let o = hand.observe(actor)?;
            let id = ids[actor];
            let (action, ledger) = match &mut players[id] {
                Player::Focal(p) => {
                    let (a, mut l, seconds) = p.choose(&o, tables)?;
                    let detail = l
                        .as_object_mut()
                        .unwrap()
                        .remove("timings")
                        .unwrap_or(Value::Null);
                    writeln!(
                        &mut metrics,
                        "{}",
                        json!({"hand":index*6+permutation as u64,"decision":actions.len(),
                        "mode":l["mode"],"seconds":seconds,"components":detail})
                    )
                    .map_err(|e| e.to_string())?;
                    (a, l)
                }
                Player::Peer(p) => (p.choose(&o, tables)?, Value::Null),
                Player::Script(p) => (p.choose(&o)?, Value::Null),
            };
            hand.apply_mut(action)?;
            actors.push(actor);
            actions.push(json!([action.kind.name(), action.raise_to]));
            states.push(snapshot(&hand));
            ledgers.push(ledger);
        }
        if let Player::Focal(p) = &mut players[0] {
            p.finish(tables)?;
        }
        let settled = hand.settlement().ok_or("unsettled")?;
        if settled.rewards.iter().sum::<i64>() != 0 {
            return Err("non-zero-sum settlement".into());
        }
        let history: Vec<_> = hand
            .history()
            .iter()
            .map(|e| match e {
                Event::Board(s) => json!([s.name(), "board"]),
                Event::Action {
                    street,
                    actor,
                    action,
                    paid,
                } => json!([
                    street.name(),
                    actor,
                    action.kind.name(),
                    action.raise_to,
                    paid
                ]),
            })
            .collect();
        writeln!(&mut trace,"{}",json!({"hand":index*6+permutation as u64,"block":index,"permutation":permutation,
            "identities":ids,"rewards":settled.rewards[..3],"stacks":config.stacks(),"button":button,"sb":50,"bb":100,
            "deck":deck,"actors":actors,"actions":actions,"states":states,"history":history,"search_ledgers":ledgers,
            "settlement":{"contributions":settled.contributions[..3],"refunds":settled.refunds[..3],
            "pots":settled.pots().iter().map(|p|json!([p.amount,p.eligible])).collect::<Vec<_>>()}})).map_err(|e|e.to_string())?;
    }
    Ok((trace, metrics))
}
fn output(path: &str) -> Result<std::io::BufWriter<std::fs::File>, String> {
    Ok(std::io::BufWriter::new(
        std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .map_err(|e| e.to_string())?,
    ))
}
fn run() -> Result<(), String> {
    let a: Vec<_> = std::env::args().collect();
    if a.len() != 2 {
        return Err("nplayer_river_arena MANIFEST.json".into());
    }
    let m: Value = serde_json::from_slice(&std::fs::read(&a[1]).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    if m["format"] != "river-whole-hand-arena-v1" {
        return Err("manifest format".into());
    }
    let threads = m["threads"].as_u64().ok_or("threads")? as usize;
    if !(1..=4).contains(&threads) {
        return Err("worker bound".into());
    }
    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global()
        .map_err(|e| e.to_string())?;
    let loading = Instant::now();
    let mut loaded = Vec::new();
    for alias in ["focal", "peer"] {
        let p = &m["models"][alias];
        let sha = p["sha256"].as_str().ok_or("model SHA")?;
        let (table, report) = PolicyTable::load_profiled(
            Path::new(p["path"].as_str().ok_or("model path")?),
            sha,
            false,
        )?;
        if table.config() != Config::new(&[10000; 3], 50, 100)? {
            return Err("requires three-player100BB".into());
        }
        loaded.push(Model{pin:json!({"sha256":sha,"source_checkpoint_sha256":table.source_checkpoint_sha256,
            "strategy":table.mode.name(),"average_scope":table.scope,"policy_load_seconds":report.total_seconds}),table:Arc::new(table)});
    }
    let models: [Model; 2] = loaded.try_into().ok().unwrap();
    let tables = EquityTables::load(Path::new(m["tables"].as_str().ok_or("K50 path")?), false)?;
    let startup = json!({"model_pins":models.iter().map(|x|x.pin.clone()).collect::<Vec<_>>(),"model_and_k50_load_seconds":loading.elapsed().as_secs_f64(),
        "resident_models":2,"shared_read_only_tables":true,"threads":threads});
    let mut startup_file = output(m["startup"].as_str().ok_or("startup output")?)?;
    writeln!(&mut startup_file, "{startup}").map_err(|e| e.to_string())?;
    startup_file.flush().map_err(|e| e.to_string())?;
    for c in m["cases"].as_array().ok_or("cases")? {
        let blocks = c["blocks"].as_u64().ok_or("blocks")?;
        if !(1..=1024).contains(&blocks) {
            return Err("block bound".into());
        }
        let root = c["root"].as_u64().ok_or("root")?;
        let enabled = c["search"].as_bool().ok_or("explicit search switch")?;
        let opponents: Vec<_> = c["opponents"]
            .as_array()
            .ok_or("opponents")?
            .iter()
            .map(|v| v.as_str().map(str::to_owned).ok_or("opponent"))
            .collect::<Result<_, _>>()?;
        let opponents: [String; 2] = opponents.try_into().map_err(|_| "two opponents")?;
        let mut pins = vec![models[0].pin.clone()];
        for spec in &opponents {
            pins.push(if spec == "peer" {
                models[1].pin.clone()
            } else {
                let name = spec.strip_prefix("bot=").ok_or("opponent")?;
                Bot::new(name, 0)?;
                json!({"script":name,"version":"nplayer-scripts-v1"})
            });
        }
        for p in &mut pins {
            p.as_object_mut().unwrap().remove("policy_load_seconds");
        }
        let trace_path = c["trace"].as_str().ok_or("trace output")?;
        let mut trace = output(trace_path)?;
        let mut metrics = output(c["metrics"].as_str().ok_or("metrics output")?)?;
        let header = json!({"format":"nplayer-privileged-policy-replay-v1","harness":"nplayer-duplicate-v1",
            "identity":models[0].table.identity,"blocks":blocks,"hands":blocks*6,"seed":root,"policies":pins,"distinct_policy_instances":3,
            "search_enabled":enabled,"search_menu":hu20_trainer::river::live::whole_hand::MENU,"loaded_weight_tables":2,
            "seat_semantics":"fixed physical seats; button=block%3; permutation maps seat to identity; identity0 singleton"});
        writeln!(&mut trace, "{header}").map_err(|e| e.to_string())?;
        let tick = Instant::now();
        for start in (0..blocks).step_by(threads) {
            let end = (start + threads as u64).min(blocks);
            let out: Vec<_> = (start..end)
                .into_par_iter()
                .map(|i| block(i, root, tables, &models, &opponents, enabled))
                .collect();
            for r in out {
                let (t, m) = r?;
                trace.write_all(&t).map_err(|e| e.to_string())?;
                metrics.write_all(&m).map_err(|e| e.to_string())?;
            }
            println!(
                "{}",
                json!({"case":c["name"],"completed_blocks":end,"total_blocks":blocks})
            );
            std::io::stdout().flush().map_err(|e| e.to_string())?;
        }
        trace.flush().map_err(|e| e.to_string())?;
        metrics.flush().map_err(|e| e.to_string())?;
        let summary = json!({"status":"complete","name":c["name"],"blocks":blocks,"hands":blocks*6,
            "play_and_write_seconds":tick.elapsed().as_secs_f64(),"trace_sha256":sha256_file(Path::new(trace_path))});
        let mut s = output(c["summary"].as_str().ok_or("summary output")?)?;
        writeln!(&mut s, "{summary}").map_err(|e| e.to_string())?;
    }
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("nplayer_river_arena: {e}");
        std::process::exit(2);
    }
}
