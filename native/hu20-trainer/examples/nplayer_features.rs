//! Training data for neural policies (docs/neural-policy-data.md).
//!
//! Plays seeded hands with models and scripted seats and, at every decision of every seat,
//! writes the acting seat's `policy_features` encoding with each teacher model's strategy there
//! and whether the teacher has a trained row. Teachers see the table through the projected view,
//! as the Open Poker client and the paired arena do.
//!
//!     nplayer_features manifest.json
//!
//! The manifest names the K50 tables, the pinned models (binary, sha256, mass receipt), the
//! teacher aliases and the jobs. Each job writes one sample file and one summary.
#[path = "support/nplayer_mass_metadata.rs"]
mod mass;

use hu20_trainer::{
    cards::EquityTables,
    multi_arena::{stream_seed, Bot},
    multi_holdem::menu,
    multi_policy::{Policy, PolicyTable},
    multi_stacks::{live_draw, DepthGrid},
    multi_view,
    nplayer::{Action, Config, Hand, Observation},
    policy_features as features,
};
use rand::{seq::SliceRandom, SeedableRng};
use rayon::prelude::*;
use serde_json::{json, Value};
use std::{collections::BTreeMap, io::Write, path::{Path, PathBuf}, sync::Arc};

const FORMAT: &str = "nplayer-feature-samples-v1";
const MAGIC: &[u8; 8] = b"NPFEAT01";
const CHUNK: u64 = 1024;
const STATUS: [&str; 3] = mass::LABELS;
const STREETS: [&str; 4] = ["preflop", "flop", "turn", "river"];

struct Model {
    table: Arc<PolicyTable>,
    pin: Value,
}
enum Stacks {
    Fixed(Vec<u64>),
    Grid(DepthGrid),
}
struct Job {
    name: String,
    players: usize,
    stacks: Stacks,
    hands: u64,
    root: u64,
    seats: Vec<String>,
    out: PathBuf,
    spec: Value,
}
#[derive(Default, Clone)]
struct Stats {
    hands: u64,
    decisions: [u64; 4],
    by_kind: [u64; 2],
    /// [teacher][street][status]
    status: Vec<[[u64; 3]; 4]>,
    /// The first teacher lacks a positive-mass row but another teacher has one, by street.
    rescued: [u64; 4],
}
impl Stats {
    fn new(teachers: usize) -> Self {
        Self { status: vec![[[0; 3]; 4]; teachers], ..Self::default() }
    }
    fn add(&mut self, o: &Stats) {
        self.hands += o.hands;
        for s in 0..4 {
            self.decisions[s] += o.decisions[s];
            self.rescued[s] += o.rescued[s];
            for t in 0..self.status.len() {
                for k in 0..3 {
                    self.status[t][s][k] += o.status[t][s][k];
                }
            }
        }
        for k in 0..2 {
            self.by_kind[k] += o.by_kind[k];
        }
    }
}

fn text<'a>(v: &'a Value, key: &str) -> Result<&'a str, String> {
    v[key].as_str().ok_or_else(|| format!("manifest: missing {key}"))
}

/// Probabilities over the six menu labels; illegal labels get 0.
fn by_label(observation: &Observation<'_>, probabilities: &[f64]) -> [f64; features::ACTIONS] {
    let mut out = [0.; features::ACTIONS];
    for ((label, _), p) in menu(observation).iter().zip(probabilities) {
        out[*label as usize] = *p;
    }
    out
}

enum Seat {
    Model(Policy, Arc<PolicyTable>),
    Script(Bot),
}

/// One hand: its records and statistics.
fn hand(job: &Job, index: u64, models: &BTreeMap<String, Model>, teachers: &[String], tables: &'static EquityTables)
    -> Result<(Vec<u8>, Stats), String> {
    let n = job.players;
    let config = match &job.stacks {
        Stacks::Fixed(stacks) => Config::new(stacks, 50, 100)?,
        Stacks::Grid(grid) => {
            let mut rng = rand::rngs::StdRng::seed_from_u64(stream_seed(job.root, b"stacks", index, 0));
            live_draw(n, *grid, &mut rng, |_| {})
        }
    };
    let mut deck: Vec<u8> = (0..52).collect();
    deck.shuffle(&mut rand::rngs::StdRng::seed_from_u64(stream_seed(job.root, b"deck", index, 0)));
    let mut seats = Vec::with_capacity(n);
    for (seat, spec) in job.seats.iter().enumerate() {
        let seed = stream_seed(job.root, b"action", index, seat as u64);
        seats.push(match spec.strip_prefix("bot=") {
            Some(bot) => Seat::Script(Bot::new(bot, seed)?),
            None => {
                let table = models[spec].table.clone();
                Seat::Model(Policy::new(table.clone(), seed), table)
            }
        });
    }
    let mut hand = Hand::from_deck(config, (index % n as u64) as usize, &deck)?;
    let mut out = Vec::new();
    let mut stats = Stats::new(teachers.len());
    stats.hands = 1;
    let mut decision = 0u16;
    while let Some(actor) = hand.actor() {
        if decision == u16::MAX {
            return Err("hand decision bound".into());
        }
        let view = hand.observe(actor)?;
        let street = view.street as usize;
        let legal = features::legal_mask(&view);
        let labels: Vec<u8> = menu(&view).iter().map(|(l, _)| *l).collect();
        let encoded = features::quantize(&features::encode(&view, Some(tables))?);
        let mut teacher_bytes = Vec::with_capacity(teachers.len() * 13);
        let mut positive = Vec::with_capacity(teachers.len());
        for (t, alias) in teachers.iter().enumerate() {
            let table = &models[alias].table;
            let frame = multi_view::project(&view, table.projection_config()?)?;
            let seen = frame.observation();
            if menu(&seen).iter().map(|(l, _)| *l).collect::<Vec<_>>() != labels {
                return Err("projected menu differs from the table's".into());
            }
            let d = table.decision(&seen, tables);
            let row = table.rows.get(&d.key);
            if row.is_some_and(|r| (r.owner as usize, r.street as usize, r.code) != (d.owner, d.street, d.code)) {
                return Err("teacher lookup identity mismatch".into());
            }
            let status = mass::MassMetadata::classify_row(row)?;
            stats.status[t][street][status] += 1;
            positive.push(status == 0);
            teacher_bytes.push(status as u8);
            let p = match row {
                Some(r) if status == 0 => by_label(&seen, r.probabilities),
                _ => [0.; features::ACTIONS],
            };
            for v in p {
                teacher_bytes.extend_from_slice(&((v * 65535.).round() as u16).to_le_bytes());
            }
        }
        if !positive[0] && positive[1..].iter().any(|&p| p) {
            stats.rescued[street] += 1;
        }
        let (action, kind): (Action, u8) = match &mut seats[actor] {
            Seat::Script(bot) => (bot.choose(&view)?, 1),
            Seat::Model(policy, table) => {
                let frame = multi_view::project(&view, table.projection_config()?)?;
                (policy.choose(&frame.observation(), tables)?, 0)
            }
        };
        let chosen = menu(&view).iter().find(|(_, a)| *a == action).map(|(l, _)| *l).ok_or("chosen action not on the menu")?;
        stats.decisions[street] += 1;
        stats.by_kind[kind as usize] += 1;
        out.extend_from_slice(&(index as u32).to_le_bytes());
        out.extend_from_slice(&decision.to_le_bytes());
        out.extend_from_slice(&[n as u8, street as u8, features::slot(&view, actor) as u8, kind, legal, chosen]);
        out.extend_from_slice(&teacher_bytes);
        out.extend_from_slice(&encoded);
        hand.apply_mut(action)?;
        decision += 1;
    }
    Ok((out, stats))
}

fn record_bytes(teachers: usize) -> usize {
    12 + teachers * (1 + 2 * features::ACTIONS) + features::len()
}

fn run(manifest_path: &Path) -> Result<(), String> {
    let m: Value = serde_json::from_slice(&std::fs::read(manifest_path).map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
    if m["format"] != "nplayer-feature-manifest-v1" {
        return Err("manifest format".into());
    }
    if let Some(threads) = m["threads"].as_u64() {
        rayon::ThreadPoolBuilder::new().num_threads(threads as usize).build_global().map_err(|e| e.to_string())?;
    }
    let tables = EquityTables::load(Path::new(text(&m, "tables")?), false)?;
    let mut models = BTreeMap::new();
    for (alias, spec) in m["models"].as_object().ok_or("manifest: models")? {
        let sha = text(spec, "sha256")?;
        let mut table = PolicyTable::load(Path::new(text(spec, "path")?), sha)?;
        let meta = mass::MassMetadata::load(Path::new(text(spec, "mass")?), text(spec, "mass_sha256")?, sha, &mut table)?;
        if !multi_view::supports(table.schema) {
            return Err(format!("{alias}: the projected view needs a live-order model"));
        }
        let pin = json!({"sha256":sha,"mass_sha256":meta.receipt_sha256,"keyset_sha256":meta.keyset_sha256,
            "source_checkpoint_sha256":table.source_checkpoint_sha256,"identity":table.identity});
        eprintln!("{{\"loaded\":\"{alias}\",\"rows\":{}}}", table.rows.len());
        models.insert(alias.clone(), Model { table: Arc::new(table), pin });
    }
    let teachers: Vec<String> = m["teachers"].as_array().ok_or("manifest: teachers")?.iter()
        .map(|t| t.as_str().map(String::from).ok_or("teacher alias".to_string())).collect::<Result<_, _>>()?;
    if teachers.is_empty() || teachers.iter().any(|t| !models.contains_key(t)) {
        return Err("teachers must be loaded models".into());
    }
    let mut jobs = Vec::new();
    for j in m["jobs"].as_array().ok_or("manifest: jobs")? {
        let players = j["players"].as_u64().ok_or("job players")? as usize;
        if !(3..=6).contains(&players) {
            return Err("jobs need 3 to 6 players: heads-up has no projected view".into());
        }
        let stacks = match &j["stacks"] {
            Value::String(law) => Stacks::Grid(match law.as_str() {
                "live-depth-grid-v1" => DepthGrid::Live,
                "wide-depth-grid-v1" => DepthGrid::Wide,
                _ => return Err("unknown stack law".into()),
            }),
            Value::Array(bb) if bb.len() == players => Stacks::Fixed(bb.iter()
                .map(|b| b.as_u64().filter(|b| (1..=2500).contains(b)).map(|b| b * 100).ok_or("stacks are 1..=2500 BB"))
                .collect::<Result<_, _>>()?),
            _ => return Err("job stacks: a stack law or one BB stack per seat".into()),
        };
        let seats: Vec<String> = j["seats"].as_array().ok_or("job seats")?.iter()
            .map(|s| s.as_str().map(String::from).ok_or("seat".to_string())).collect::<Result<_, _>>()?;
        if seats.len() != players {
            return Err("one seat spec per player".into());
        }
        for s in &seats {
            match s.strip_prefix("bot=") {
                Some(bot) => { Bot::new(bot, 0)?; }
                None if models.contains_key(s) => {}
                None => return Err(format!("unknown seat {s}")),
            }
        }
        jobs.push(Job { name: text(j, "name")?.into(), players, stacks, hands: j["hands"].as_u64().ok_or("job hands")?,
                        root: j["root"].as_u64().ok_or("job root")?, seats, out: PathBuf::from(text(j, "out")?), spec: j.clone() });
    }
    let record = record_bytes(teachers.len());
    for job in &jobs {
        let start = std::time::Instant::now();
        let header = json!({"format":FORMAT,"schema":features::SCHEMA,"layout_sha256":features::layout_sha256(),
            "feature_names":features::names(),"feature_count":features::len(),"actions":features::ACTIONS,
            "record_bytes":record,"status":STATUS,
            "record_layout":["hand u32","decision u16","players u8","street u8","actor_slot u8","seat_kind u8 (0 model, 1 script)",
                             "legal_mask u8","chosen_label u8","per teacher: status u8, 6 probabilities u16 (x/65535)","features u8 (x/255)"],
            "teachers":teachers.iter().map(|t| json!({"alias":t,"pin":models[t].pin})).collect::<Vec<_>>(),
            "card_tables":tables.sha256,"job":job.spec});
        let header_bytes = serde_json::to_vec(&header).map_err(|e| e.to_string())?;
        let file = std::fs::OpenOptions::new().write(true).create_new(true).open(&job.out)
            .map_err(|e| format!("{}: {e}", job.out.display()))?;
        let mut w = std::io::BufWriter::with_capacity(1 << 24, file);
        w.write_all(MAGIC).and_then(|_| w.write_all(&(header_bytes.len() as u64).to_le_bytes()))
            .and_then(|_| w.write_all(&header_bytes)).map_err(|e| e.to_string())?;
        let mut stats = Stats::new(teachers.len());
        let mut samples = 0u64;
        let mut first = 0;
        while first < job.hands {
            let last = (first + CHUNK).min(job.hands);
            let results: Vec<_> = (first..last).into_par_iter().map(|i| hand(job, i, &models, &teachers, tables)).collect();
            for r in results {
                let (bytes, s) = r?;
                if bytes.len() % record != 0 {
                    return Err("record size mismatch".into());
                }
                samples += (bytes.len() / record) as u64;
                w.write_all(&bytes).map_err(|e| e.to_string())?;
                stats.add(&s);
            }
            first = last;
        }
        w.flush().map_err(|e| e.to_string())?;
        drop(w);
        let seconds = start.elapsed().as_secs_f64();
        let teacher_stats: Vec<Value> = teachers.iter().enumerate().map(|(t, alias)| {
            let by_street: BTreeMap<&str, Value> = STREETS.iter().enumerate().map(|(s, name)| {
                (*name, json!(STATUS.iter().zip(stats.status[t][s]).map(|(k, v)| (k.to_string(), v)).collect::<BTreeMap<_, _>>()))
            }).collect();
            json!({"alias":alias,"by_street":by_street})
        }).collect();
        let summary = json!({"format":"nplayer-feature-summary-v1","job":job.name,"out":job.out,
            "sha256":hu20_trainer::export::sha256_file(&job.out),"bytes":std::fs::metadata(&job.out).map_err(|e| e.to_string())?.len(),
            "hands":stats.hands,"samples":samples,"record_bytes":record,
            "decisions_by_street":STREETS.iter().zip(stats.decisions).map(|(k, v)| (k.to_string(), v)).collect::<BTreeMap<_, _>>(),
            "decisions_by_seat_kind":{"model":stats.by_kind[0],"script":stats.by_kind[1]},
            "first_teacher_missing_other_positive_by_street":STREETS.iter().zip(stats.rescued).map(|(k, v)| (k.to_string(), v)).collect::<BTreeMap<_, _>>(),
            "teachers":teacher_stats,"seconds":seconds,"samples_per_second":samples as f64 / seconds});
        let path = job.out.with_extension("summary.json");
        std::fs::OpenOptions::new().write(true).create_new(true).open(&path)
            .and_then(|mut f| f.write_all(serde_json::to_string_pretty(&summary).unwrap().as_bytes()))
            .map_err(|e| format!("{}: {e}", path.display()))?;
        println!("{}", json!({"job":job.name,"samples":samples,"seconds":seconds}));
    }
    Ok(())
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        eprintln!("usage: nplayer_features manifest.json");
        std::process::exit(2);
    }
    if let Err(e) = run(Path::new(&args[1])) {
        eprintln!("nplayer_features: {e}");
        std::process::exit(2);
    }
}
