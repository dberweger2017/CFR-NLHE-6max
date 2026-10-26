//! Fixed three-seat mixed-opponent evaluator. Diagnostics never sample actions.
use hu20_trainer::{
    cards::EquityTables,
    export::sha256_file,
    multi_arena::{stream_seed, Bot, PERMUTATIONS},
    multi_checkpoint::key_hex,
    multi_policy::{Policy, PolicyTable},
    nplayer::{Config, Hand},
};
use rand::{seq::SliceRandom, SeedableRng};
use rayon::prelude::*;
use serde_json::{json, Value};
use std::{io::Write, path::Path, sync::Arc, time::Instant};
#[path = "support/nplayer_mass_metadata.rs"]
mod mass;
struct Model {
    table: Arc<PolicyTable>,
    mass: mass::MassMetadata,
    pin: Value,
}
enum Player {
    Model(Policy, usize),
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
type Counters = [[u64; 4]; 3];
type Lookups = [[[[u64; 3]; 2]; 4]; 3];
fn block(
    block: u64,
    root: u64,
    config: Config,
    tables: &EquityTables,
    models: &[Model; 2],
    specs: &[String; 3],
    diagnostics: bool,
) -> Result<(Vec<u8>, Counters, Counters, Lookups), String> {
    let mut bytes = Vec::new();
    let mut decisions = [[0; 4]; 3];
    let mut misses = [[0; 4]; 3];
    let mut counts = [[[[0; 3]; 2]; 4]; 3];
    let mut deck: Vec<u8> = (0..52).collect();
    deck.shuffle(&mut rand::rngs::StdRng::seed_from_u64(stream_seed(
        root, b"deck", block, 0,
    )));
    let button = block as usize % 3;
    for (permutation, ids) in PERMUTATIONS.iter().enumerate() {
        let mut players = Vec::new();
        for id in 0..3 {
            let seed = stream_seed(root, b"action", block, id as u64);
            players.push(if let Some(bot) = specs[id].strip_prefix("bot=") {
                Player::Script(Bot::new(bot, seed)?)
            } else {
                let i = if specs[id] == "baseline" {
                    0
                } else if specs[id] == "candidate" {
                    1
                } else {
                    return Err("unknown model alias".into());
                };
                Player::Model(Policy::new(models[i].table.clone(), seed), i)
            });
        }
        let mut hand = Hand::from_deck(config, button, &deck)?;
        let mut states = vec![snapshot(&hand)];
        let mut actors = Vec::new();
        let mut actions = Vec::new();
        let mut lookups = Vec::new();
        while let Some(actor) = hand.actor() {
            if actions.len() >= 10000 {
                return Err("hand action bound".into());
            }
            let o = hand.observe(actor)?;
            let id = ids[actor];
            let street = o.street as usize;
            let (action, lookup) = match &mut players[id] {
                Player::Script(bot) => (bot.choose(&o)?, json!({"status":"not_applicable"})),
                Player::Model(policy, model) => {
                    let old = policy.misses;
                    let a = policy.choose(&o, tables)?;
                    misses[id][street] += policy.misses - old;
                    let lookup = if diagnostics {
                        if models[0].table.schema != models[1].table.schema {
                            return Err("matched membership needs one key schema".into());
                        }
                        let d = models[0].table.decision(&o, tables);
                        let rows = [
                            models[0].table.rows.get(&d.key),
                            models[1].table.rows.get(&d.key),
                        ];
                        if rows[0].is_some() != rows[1].is_some() {
                            return Err("frozen membership differs on matched observation".into());
                        }
                        for row in rows.iter().flatten() {
                            if (row.owner as usize, row.street as usize, row.code)
                                != (d.owner, d.street, d.code)
                            {
                                return Err("counterfactual lookup action identity mismatch".into());
                            }
                        }
                        let labels = [
                            mass::MassMetadata::classify_row(rows[0])?,
                            mass::MassMetadata::classify_row(rows[1])?,
                        ];
                        if labels[0] == 0 && labels[1] == 1 {
                            return Err("nonnegative cumulative average mass became zero".into());
                        }
                        for i in 0..2 {
                            counts[id][street][i][labels[i]] += 1;
                        }
                        json!({"acting_model":if *model==0 {"baseline"}else{"candidate"},"key":key_hex(&d.key),
                            "statuses":[mass::LABELS[labels[0]],mass::LABELS[labels[1]]],"street":o.street.name(),
                            "seat":actor,"position":(actor+3-button)%3,"pot":o.players.iter().map(|p|p.contributed).sum::<u64>(),
                            "live_players":o.players.iter().filter(|p|!p.folded).count(),"action":[a.kind.name(),a.raise_to]})
                    } else {
                        Value::Null
                    };
                    (a, lookup)
                }
            };
            decisions[id][street] += 1;
            hand.apply_mut(action)?;
            actors.push(actor);
            actions.push(json!([action.kind.name(), action.raise_to]));
            states.push(snapshot(&hand));
            lookups.push(lookup);
        }
        let s = hand.settlement().ok_or("unsettled")?;
        if s.rewards.iter().sum::<i64>() != 0 {
            return Err("payoff accounting".into());
        }
        let history: Vec<_> = hand
            .history()
            .iter()
            .map(|e| match e {
                hu20_trainer::nplayer::Event::Board(s) => json!([s.name(), "board"]),
                hu20_trainer::nplayer::Event::Action {
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
        let mut row = json!({"hand":block*6+permutation as u64,"block":block,"permutation":permutation,"identities":ids,
            "rewards":s.rewards[..3],"stacks":config.stacks(),"button":button,"sb":50,"bb":100,"deck":deck,
            "actors":actors,"actions":actions,"states":states,"history":history,
            "settlement":{"contributions":s.contributions[..3],"refunds":s.refunds[..3],"pots":s.pots().iter().map(|p|json!([p.amount,p.eligible])).collect::<Vec<_>>()}});
        if diagnostics {
            row["lookups"] = json!(lookups);
        }
        writeln!(&mut bytes, "{row}").map_err(|e| e.to_string())?;
    }
    Ok((bytes, decisions, misses, counts))
}
fn campaign_config(m: &Value) -> Result<Config, String> {
    let bb = match m.get("stack_bb") {
        None => 100,
        Some(value) => value.as_u64().ok_or("integer stack_bb required")?,
    };
    if !matches!(bb, 100 | 200) { return Err("stack_bb must be100 or200".into()); }
    Config::new(&[bb * 100; 3], 50, 100)
}

fn run() -> Result<(), String> {
    let a: Vec<String> = std::env::args().collect();
    if a.len() != 3 || a[1] != "batch" {
        return Err("batch MANIFEST.json".into());
    }
    let m: Value = serde_json::from_slice(&std::fs::read(&a[2]).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    let threads = m["threads"].as_u64().ok_or("threads")? as usize;
    if !(1..=16).contains(&threads) {
        return Err("thread bound".into());
    }
    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global()
        .map_err(|e| e.to_string())?;
    let diagnostics = m["diagnostics"]
        .as_bool()
        .ok_or("explicit diagnostics flag required")?;
    let loading = Instant::now();
    let mut list = Vec::new();
    for alias in ["baseline", "candidate"] {
        let p = &m["models"][alias];
        let digest = p["sha256"].as_str().ok_or("policy hash")?;
        let mut table =
            PolicyTable::load(Path::new(p["path"].as_str().ok_or("policy path")?), digest)?;
        let mass = mass::MassMetadata::load(
            Path::new(p["mass"].as_str().ok_or("mass path")?),
            p["mass_sha256"].as_str().ok_or("mass hash")?,
            digest,
            &mut table,
        )?;
        let table = Arc::new(table);
        if let Some(expected) = m["keyset_sha256"].as_str() {
            if mass.keyset_sha256 != expected {
                return Err("wrong frozen keyset".into());
            }
        }
        let pin = json!({"sha256":digest,"source_checkpoint_sha256":table.source_checkpoint_sha256,"strategy":table.mode.name(),"average_scope":table.scope});
        list.push(Model { table, mass, pin });
    }
    let models: [Model; 2] = list.try_into().ok().unwrap();
    if models[0].table.identity != models[1].table.identity
        || models[0].mass.keyset_sha256 != models[1].mass.keyset_sha256
    {
        return Err("model identities or memberships differ".into());
    }
    let config = campaign_config(&m)?;
    if models.iter().any(|v| v.table.config().ok() != Some(config)) {
        return Err("model differs from declared three-player stack depth".into());
    }
    let tables = EquityTables::load(Path::new(m["tables"].as_str().ok_or("tables")?), false)?;
    let mut load_seconds = loading.elapsed().as_secs_f64();
    let mut new_tables = 2;
    for c in m["cases"].as_array().ok_or("cases")? {
        let root = c["root"].as_u64().ok_or("root")?;
        let blocks = c["blocks"].as_u64().ok_or("blocks")?;
        if !(2..=1_000_000).contains(&blocks) {
            return Err("block bound".into());
        }
        let specs: Vec<String> = c["players"]
            .as_array()
            .ok_or("players")?
            .iter()
            .map(|v| v.as_str().map(str::to_owned).ok_or("player spec"))
            .collect::<Result<_, _>>()?;
        let specs: [String; 3] = specs
            .try_into()
            .map_err(|_| "three player identities required")?;
        let mut pins = Vec::new();
        for spec in &specs {
            pins.push(if let Some(bot) = spec.strip_prefix("bot=") {
                Bot::new(bot, 0)?;
                json!({"script":bot,"version":"nplayer-scripts-v1"})
            } else if spec == "baseline" {
                models[0].pin.clone()
            } else if spec == "candidate" {
                models[1].pin.clone()
            } else {
                return Err("player alias".into());
            });
        }
        let trace = Path::new(c["trace"].as_str().ok_or("trace")?);
        let mut out = std::io::BufWriter::new(
            std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(trace)
                .map_err(|e| e.to_string())?,
        );
        let mut header = json!({"format":"nplayer-privileged-policy-replay-v1","harness":"nplayer-duplicate-v1","identity":models[0].table.identity,
            "blocks":blocks,"hands":blocks*6,"seed":root,"policies":pins,"distinct_policy_instances":3,"loaded_weight_tables":2,
            "seat_semantics":"fixed physical seats; button=block%3; permutation maps seat to identity; identity0 singleton"});
        if diagnostics {
            header["lookup_metadata"] = json!({"models":["baseline","candidate"],"statuses":mass::LABELS,
            "receipts":[models[0].mass.receipt_sha256,models[1].mass.receipt_sha256]});
        }
        writeln!(out, "{header}").map_err(|e| e.to_string())?;
        let tick = Instant::now();
        let mut decisions = [[0; 4]; 3];
        let mut misses = [[0; 4]; 3];
        let mut counts = [[[[0; 3]; 2]; 4]; 3];
        for start in (0..blocks).step_by(threads * 2) {
            if std::env::var_os("NPLAYER_STOP_FILE").is_some_and(|p| Path::new(&p).exists()) {
                return Err("owner stop".into());
            }
            let batch: Vec<_> = (start..(start + 2 * threads as u64).min(blocks))
                .into_par_iter()
                .map(|b| block(b, root, config, tables, &models, &specs, diagnostics))
                .collect();
            for value in batch {
                let (bytes, d, ms, ls) = value?;
                out.write_all(&bytes).map_err(|e| e.to_string())?;
                for id in 0..3 {
                    for st in 0..4 {
                        decisions[id][st] += d[id][st];
                        misses[id][st] += ms[id][st];
                        for model in 0..2 {
                            for label in 0..3 {
                                counts[id][st][model][label] += ls[id][st][model][label];
                            }
                        }
                    }
                }
            }
        }
        out.flush().map_err(|e| e.to_string())?;
        let result = json!({"status":"passed","blocks":blocks,"hands":blocks*6,"new_weight_tables":new_tables,"resident_weight_tables":2,
            "resident_card_table_sets":1,"load_seconds":load_seconds,"play_seconds":tick.elapsed().as_secs_f64(),
            "decisions_by_identity_street":decisions,"misses_by_identity_street":misses,"lookup_counts":counts,"trace_sha256":sha256_file(trace)});
        let mut summary = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(c["summary"].as_str().ok_or("summary")?)
            .map_err(|e| e.to_string())?;
        writeln!(summary, "{result}").map_err(|e| e.to_string())?;
        println!("{}", json!({"event":"progress","completed":c["name"]}));
        std::io::stdout().flush().map_err(|e| e.to_string())?;
        load_seconds = 0.;
        new_tables = 0;
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("nplayer_continuation_arena: {error}");
        std::process::exit(2);
    }
}

#[cfg(test)]
mod depth_tests {
    use super::*;
    #[test]
    fn explicit_depth_keeps_legacy_default_and_rejects_bad_values() {
        assert_eq!(campaign_config(&json!({})).unwrap(), Config::new(&[10000;3],50,100).unwrap());
        assert_eq!(campaign_config(&json!({"stack_bb":200})).unwrap(), Config::new(&[20000;3],50,100).unwrap());
        for value in [json!(0),json!(20),json!(201),json!(200.5),json!("200"),json!(null)] {
            assert!(campaign_config(&json!({"stack_bb":value})).is_err());
        }
    }
}
