use hu20_trainer::{
    cards::EquityTables,
    export::sha256_file,
    multi_arena::{stream_seed, Bot},
    multi_checkpoint::key_hex,
    multi_holdem,
    multi_policy::{Policy, PolicyTable},
    nplayer::{Config, Event, Hand},
};
use rand::{seq::SliceRandom, SeedableRng};
use rayon::prelude::*;
use serde_json::{json, Value};
use std::{
    collections::{HashMap, HashSet},
    io::Write,
    path::{Path, PathBuf},
    sync::Arc,
    time::Instant,
};
#[path = "nplayer_mass_metadata.rs"]
mod mass;

fn number(v: &Value, key: &str) -> Result<u64, String> {
    v[key]
        .as_u64()
        .ok_or_else(|| format!("unsigned {key} required"))
}
fn text<'a>(v: &'a Value, key: &str) -> Result<&'a str, String> {
    v[key]
        .as_str()
        .ok_or_else(|| format!("string {key} required"))
}
pub fn schedule(n: usize, declared: &Value) -> Result<Vec<Vec<usize>>, String> {
    if !(4..=6).contains(&n) {
        return Err("paired arena supports four to six players".into());
    }
    let rows = if declared.is_null() {
        (0..n)
            .map(|r| (0..n).map(|s| (s + r) % n).collect())
            .collect::<Vec<Vec<usize>>>()
    } else {
        declared
            .as_array()
            .ok_or("schedule array")?
            .iter()
            .map(|r| {
                r.as_array()
                    .ok_or("schedule row")?
                    .iter()
                    .map(|x| {
                        usize::try_from(x.as_u64().ok_or("schedule integer")?)
                            .map_err(|e| e.to_string())
                    })
                    .collect::<Result<Vec<_>, String>>()
            })
            .collect::<Result<Vec<_>, String>>()?
    };
    if rows.is_empty() || rows.len() > 720 || rows.len() % n != 0 {
        return Err("schedule count must be a positive multiple of N, at most720".into());
    }
    let mut seen = HashSet::new();
    let mut counts = vec![vec![0; n]; n];
    for row in &rows {
        let mut sorted = row.clone();
        sorted.sort();
        if sorted != (0..n).collect::<Vec<_>>() || !seen.insert(row.clone()) {
            return Err("invalid/duplicate seat permutation".into());
        }
        for (seat, id) in row.iter().enumerate() {
            counts[*id][seat] += 1;
        }
    }
    if counts.iter().flatten().any(|c| *c != rows.len() / n) {
        return Err("unbalanced identity/physical-seat schedule".into());
    }
    Ok(rows)
}
struct Model {
    table: Arc<PolicyTable>,
    pin: Value,
}
enum Player {
    Model(Policy, String),
    Script(Bot),
}
struct Case {
    name: String,
    n: usize,
    config: Config,
    blocks: u64,
    root: u64,
    seating: Vec<Vec<usize>>,
    arms: [Vec<String>; 2],
    traces: [PathBuf; 2],
    summary: PathBuf,
}
impl Case {
    fn parse(v: &Value) -> Result<Self, String> {
        let n = usize::try_from(number(v, "players")?).map_err(|e| e.to_string())?;
        let seating = schedule(n, &v["schedule"])?;
        let stack = number(v, "stack_bb")?;
        let blocks = number(v, "blocks")?;
        if ![20, 100, 200].contains(&stack) || !(2..=1_000_000).contains(&blocks) {
            return Err("stack/block bounds".into());
        }
        let list = |key: &str| -> Result<Vec<String>, String> {
            v[key]
                .as_array()
                .ok_or("string list")?
                .iter()
                .map(|s| s.as_str().map(str::to_owned).ok_or("string spec".into()))
                .collect()
        };
        let focals = list("focals")?;
        let opponents = list("opponents")?;
        let traces = list("traces")?;
        if focals.len() != 2
            || opponents.len() != n - 1
            || traces.len() != 2
            || traces[0] == traces[1]
        {
            return Err("two focals/traces and N-1 fixed opponents required".into());
        }
        let arms = [&focals[0], &focals[1]].map(|f| {
            std::iter::once(f.clone())
                .chain(opponents.clone())
                .collect::<Vec<_>>()
        });
        let models: HashSet<_> = arms
            .iter()
            .flatten()
            .filter(|s| !s.starts_with("bot="))
            .collect();
        if models.len() > 2 {
            return Err("at most two distinct model aliases per case".into());
        }
        Ok(Self {
            name: text(v, "name")?.into(),
            n,
            config: Config::new(&vec![stack * 100; n], 50, 100)?,
            blocks,
            root: number(v, "root")?,
            seating,
            arms,
            traces: [PathBuf::from(&traces[0]), PathBuf::from(&traces[1])],
            summary: text(v, "summary")?.into(),
        })
    }
}
fn snapshot(hand: &Hand) -> Value {
    let n = hand.config().players();
    let legal = hand
        .legal()
        .map(|l| json!({"check":l.check,"call":l.call_amount,"raise_to":l.raise_to}));
    json!({"actor":hand.actor(),"finished":hand.finished(),"board":hand.board(),
      "street":if hand.finished(){None}else{Some(hand.street().name())},"pot":hand.pot(),
      "wager":if hand.finished(){None}else{Some(hand.wager())},"min_raise":if hand.finished(){None}else{Some(hand.min_raise())},
      "players":hand.players().iter().map(|p|json!([p.stack,p.street_bet,p.contributed,p.folded])).collect::<Vec<_>>(),
      "holes":(0..n).map(|p|hand.observe(p).unwrap().hole).collect::<Vec<_>>(),"legal":legal,
      "rewards":hand.settlement().map(|s|s.rewards[..n].to_vec())})
}
fn play(
    block: u64,
    case: &Case,
    tables: Option<&EquityTables>,
    models: &HashMap<String, Model>,
) -> Result<[Vec<u8>; 2], String> {
    let mut bytes = [Vec::new(), Vec::new()];
    let mut deck: Vec<u8> = (0..52).collect();
    deck.shuffle(&mut rand::rngs::StdRng::seed_from_u64(stream_seed(
        case.root, b"deck", block, 0,
    )));
    let button = block as usize % case.n;
    for (rotation, ids) in case.seating.iter().enumerate() {
        for (arm, specs) in case.arms.iter().enumerate() {
            let mut players = Vec::new();
            for (id, spec) in specs.iter().enumerate() {
                let seed = stream_seed(case.root, b"action", block, id as u64);
                players.push(if let Some(bot) = spec.strip_prefix("bot=") {
                    Player::Script(Bot::new(bot, seed)?)
                } else {
                    Player::Model(Policy::new(models[spec].table.clone(), seed), spec.clone())
                });
            }
            let mut hand = Hand::from_deck(case.config, button, &deck)?;
            let mut states = vec![snapshot(&hand)];
            let mut actions = Vec::new();
            let mut actors = Vec::new();
            let mut lookups = Vec::new();
            while let Some(actor) = hand.actor() {
                if actions.len() >= 10000 {
                    return Err("hand action bound".into());
                }
                // Only this acting-seat Observation crosses the player boundary.
                let view = hand.observe(actor)?;
                let id = ids[actor];
                let (action, lookup) = match &mut players[id] {
                    Player::Script(bot) => (bot.choose(&view)?, json!({"status":"not_applicable"})),
                    Player::Model(policy, alias) => {
                        let t = tables.ok_or("K50 required")?;
                        let action = policy.choose(&view, t)?;
                        let d = multi_holdem::observation_decision(&view, t);
                        let row = models[alias].table.rows.get(&d.key);
                        if row.is_some_and(|r| {
                            (r.owner as usize, r.street as usize, r.code)
                                != (d.owner, d.street, d.code)
                        }) {
                            return Err("lookup identity mismatch".into());
                        }
                        let label = mass::LABELS[mass::MassMetadata::classify_row(row)?];
                        (
                            action,
                            json!({"status":label,"key":key_hex(&d.key),"street":d.street,"identity":id,"seat":actor,"position":(actor+case.n-button)%case.n}),
                        )
                    }
                };
                hand.apply_mut(action)?;
                actors.push(actor);
                actions.push(json!([action.kind.name(), action.raise_to]));
                lookups.push(lookup);
                states.push(snapshot(&hand));
            }
            let s = hand.settlement().ok_or("unsettled hand")?;
            if s.rewards[..case.n].iter().sum::<i64>() != 0 {
                return Err("chip conservation failed".into());
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
            writeln!(&mut bytes[arm],"{}",json!({"hand":block*case.seating.len() as u64+rotation as u64,"block":block,"permutation":rotation,"identities":ids,
              "rewards":s.rewards[..case.n],"stacks":case.config.stacks(),"button":button,"sb":50,"bb":100,"deck":deck,"actors":actors,"actions":actions,"lookups":lookups,"states":states,"history":history,
              "settlement":{"contributions":s.contributions[..case.n],"refunds":s.refunds[..case.n],"pots":s.pots().iter().map(|p|json!([p.amount,p.eligible])).collect::<Vec<_>>()}})).map_err(|e|e.to_string())?;
        }
    }
    Ok(bytes)
}
fn execute(
    case: &Case,
    catalog: &Value,
    models: &mut HashMap<String, Model>,
    tables: &mut Option<&'static EquityTables>,
    table_path: &Path,
    threads: usize,
) -> Result<Value, String> {
    let tick = Instant::now();
    let used: HashSet<_> = case
        .arms
        .iter()
        .flatten()
        .filter(|s| !s.starts_with("bot="))
        .cloned()
        .collect();
    models.retain(|alias, _| used.contains(alias));
    let mut ordered: Vec<_> = used.into_iter().collect();
    ordered.sort();
    for alias in ordered {
        if models.contains_key(&alias) {
            continue;
        }
        let spec = &catalog[&alias];
        let path = Path::new(text(spec, "path")?);
        let sha = text(spec, "sha256")?;
        let mut table = PolicyTable::load(path, sha)?;
        let metadata = mass::MassMetadata::load(
            Path::new(text(spec, "mass")?),
            text(spec, "mass_sha256")?,
            sha,
            &mut table,
        )?;
        let pin = json!({"sha256":sha,"mass_sha256":metadata.receipt_sha256,"keyset_sha256":metadata.keyset_sha256,
            "strategy":table.mode.name(),"average_scope":table.scope,"source_checkpoint_sha256":table.source_checkpoint_sha256});
        models.insert(
            alias,
            Model {
                table: Arc::new(table),
                pin,
            },
        );
    }
    for spec in case.arms.iter().flatten() {
        if let Some(bot) = spec.strip_prefix("bot=") {
            Bot::new(bot, 0)?;
        } else if models[spec].table.config() != case.config {
            return Err("policy/game identity differs".into());
        }
    }
    if !models.is_empty() && tables.is_none() {
        *tables = Some(EquityTables::load(table_path, false)?);
    }
    let identity=case.arms.iter().flatten().find_map(|s|models.get(s)).map(|m|m.table.identity.clone())
        .unwrap_or_else(||json!({"players":case.n,"stacks":case.config.stacks(),"small_blind":50,"big_blind":100}));
    let mut output = Vec::new();
    for (arm, path) in case.traces.iter().enumerate() {
        let pins: Vec<_> = case.arms[arm]
            .iter()
            .map(|s| {
                if let Some(bot) = s.strip_prefix("bot=") {
                    json!({"script":bot,"version":"nplayer-scripts-v1"})
                } else {
                    models[s].pin.clone()
                }
            })
            .collect();
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .map_err(|e| e.to_string())?;
        let mut out = std::io::BufWriter::new(file);
        writeln!(out,"{}",json!({"format":"nplayer-privileged-policy-replay-v1","harness":"nplayer-paired-v1","identity":identity,"hands":case.blocks*case.seating.len() as u64,
          "blocks":case.blocks,"seed":case.root,"schedule":case.seating,"policies":pins,"distinct_policy_instances":case.n,"loaded_weight_tables":models.len(),
          "seat_semantics":"fixed physical hands; button=block%N; schedule maps seat to labeled identity; identity0 focal"})).map_err(|e|e.to_string())?;
        output.push(out);
    }
    let load_seconds = tick.elapsed().as_secs_f64();
    let playing = Instant::now();
    for start in (0..case.blocks).step_by(threads * 2) {
        if std::env::var_os("NPLAYER_STOP_FILE").is_some_and(|p| Path::new(&p).exists()) {
            return Err("ownerSTOP; partial traces retained".into());
        }
        let chunks: Vec<_> = (start..(start + 2 * threads as u64).min(case.blocks))
            .into_par_iter()
            .map(|b| play(b, case, *tables, models))
            .collect();
        for chunk in chunks {
            let chunk = chunk?;
            for arm in 0..2 {
                output[arm]
                    .write_all(&chunk[arm])
                    .map_err(|e| e.to_string())?;
            }
        }
    }
    for out in &mut output {
        out.flush().map_err(|e| e.to_string())?;
    }
    Ok(
        json!({"status":"passed","blocks":case.blocks,"hands_per_arm":case.blocks*case.seating.len() as u64,"load_seconds":load_seconds,"play_seconds":playing.elapsed().as_secs_f64(),
      "resident_weight_tables":models.len(),"trace_sha256":case.traces.iter().map(|p|sha256_file(p)).collect::<Vec<_>>()}),
    )
}
pub fn run() -> Result<(), String> {
    let a: Vec<_> = std::env::args().collect();
    if a.len() != 3 || a[1] != "batch" {
        return Err("batch MANIFEST.json".into());
    }
    let raw = std::fs::read(&a[2]).map_err(|e| e.to_string())?;
    let manifest_sha = sha256_file(Path::new(&a[2]));
    let manifest: Value = serde_json::from_slice(&raw).map_err(|e| e.to_string())?;
    if manifest["format"] != "nplayer-paired-manifest-v1" {
        return Err("paired manifest format".into());
    }
    let threads = usize::try_from(number(&manifest, "threads")?).map_err(|e| e.to_string())?;
    if !(1..=16).contains(&threads) {
        return Err("thread bound".into());
    }
    let cases = manifest["cases"]
        .as_array()
        .ok_or("cases")?
        .iter()
        .map(Case::parse)
        .collect::<Result<Vec<_>, String>>()?;
    if cases.is_empty() {
        return Err("empty cases".into());
    }
    let mut paths = HashSet::new();
    for c in &cases {
        for p in c.traces.iter().chain(std::iter::once(&c.summary)) {
            if !paths.insert(p.clone()) || p.exists() {
                return Err("output exists/duplicates; no overwrite".into());
            }
        }
    }
    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global()
        .map_err(|e| e.to_string())?;
    let mut models = HashMap::new();
    let mut tables = None;
    for case in cases {
        if sha256_file(Path::new(&a[2])) != manifest_sha {
            return Err("manifest mutated".into());
        }
        let result = execute(
            &case,
            &manifest["models"],
            &mut models,
            &mut tables,
            Path::new(text(&manifest, "tables")?),
            threads,
        )?;
        if sha256_file(Path::new(&a[2])) != manifest_sha {
            return Err("manifest mutated".into());
        }
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&case.summary)
            .map_err(|e| e.to_string())?;
        writeln!(&mut file, "{result}").map_err(|e| e.to_string())?;
        println!("{}", json!({"event":"case-complete","name":case.name}));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn cyclic_schedule_balances_every_identity_and_position() {
        for n in 4..=6 {
            let s = schedule(n, &Value::Null).unwrap();
            assert_eq!(s.len(), n);
            for id in 0..n {
                for seat in 0..n {
                    assert_eq!(s.iter().filter(|r| r[seat] == id).count(), 1);
                }
            }
        }
    }
    #[test]
    fn invalid_duplicate_and_unbalanced_schedules_refuse() {
        assert!(schedule(3, &Value::Null).is_err());
        assert!(schedule(
            4,
            &json!([[0, 1, 2, 3], [0, 1, 2, 3], [1, 2, 3, 0], [2, 3, 0, 1]])
        )
        .is_err());
        assert!(schedule(
            4,
            &json!([[0, 1, 2, 3], [0, 1, 3, 2], [0, 2, 1, 3], [0, 2, 3, 1]])
        )
        .is_err());
        assert!(schedule(4, &json!([[0, 1, 2, 99]])).is_err());
    }
    #[test]
    fn controlled_field_is_shared_by_construction() {
        let c=Case::parse(&json!({"name":"test","players":6,"stack_bb":100,"blocks":2,"root":9,
            "focals":["a","b"],"opponents":["a","bot=check-call","bot=random","bot=pot-pressure","bot=tight-aggressive"],"traces":["left","right"],"summary":"summary"})).unwrap();
        assert_eq!(c.arms[0][1..], c.arms[1][1..]);
        assert_ne!(c.arms[0][0], c.arms[1][0]);
        let rows=play(0,&Case::parse(&json!({"name":"self","players":4,"stack_bb":100,"blocks":2,"root":9,
            "focals":["bot=random","bot=random"],"opponents":["bot=check-call","bot=pot-pressure","bot=tight-aggressive"],"traces":["left","right"],"summary":"summary"})).unwrap(),None,&HashMap::new()).unwrap();
        assert_eq!(rows[0], rows[1]);
    }
}
