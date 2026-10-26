//! Research-only frozen-current-policy diagnostic; never saves a trainer.
use hu20_trainer::{
    cards::EquityTables,
    export::sha256_file,
    game::Kind,
    multi_cfr::{Game, PathSampler, Sampler, State, Table},
    multi_checkpoint,
    multi_holdem::{self, CashGame, CashState},
    nplayer::{Action, Config, Event, Hand},
};
use rand::{rngs::StdRng, SeedableRng};
use rayon::prelude::*;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs::File,
    io::{BufRead, BufReader, Write},
    path::Path,
    time::Instant,
};
#[path = "support/warm_artifacts.rs"]
mod artifacts;
#[path = "support/warm_estimator.rs"]
mod probe;
#[cfg(test)]
#[path = "support/warm_estimator_tests.rs"]
mod tests;

const WARM_SHA: &str = "2071d1e7fcbf3294942a978cc01ca8c817b4174f3bdedda072758d68c08bd2a1";
const ROOT_SEED: u64 = 2026102442501;
fn line(out: &mut impl Write, v: &Value) -> Result<(), String> {
    serde_json::to_writer(&mut *out, v).map_err(|e| e.to_string())?;
    writeln!(out).map_err(|e| e.to_string())
}
fn family(state: &CashState, owner: usize) -> String {
    let mut opponent = BTreeSet::new();
    let mut own = false;
    let mut passive = 0;
    for event in state.hand.history() {
        if let Event::Action {
            street,
            actor,
            action,
            ..
        } = event
        {
            if *street as usize == 0 {
                continue;
            }
            if action.kind == Kind::Raise {
                if *actor == owner {
                    own = true;
                } else {
                    opponent.insert(*actor);
                }
            }
            if *actor != owner && matches!(action.kind, Kind::Check | Kind::Call) {
                passive += 1;
            }
        }
    }
    if opponent.is_empty() {
        if own {
            "P1"
        } else {
            "P0"
        }
    } else if opponent.len() == 1 && passive >= 2 {
        "P2"
    } else {
        "other"
    }
    .into()
}
fn seed(domain: &[u8], batch: u64, seat: usize, root: usize) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(domain);
    h.update(ROOT_SEED.to_le_bytes());
    h.update(batch.to_le_bytes());
    h.update((seat as u64).to_le_bytes());
    h.update((root as u64).to_le_bytes());
    h.finalize().into()
}
fn parse_key(text: &str) -> Result<[u8; 16], String> {
    if text.len() != 32 || !text.is_ascii() {
        return Err("bad information key".into());
    }
    let mut key = [0; 16];
    for (i, b) in key.iter_mut().enumerate() {
        *b = u8::from_str_radix(&text[2 * i..2 * i + 2], 16).map_err(|e| e.to_string())?;
    }
    Ok(key)
}
fn integer(v: &Value) -> Result<u64, String> {
    v.as_u64().ok_or_else(|| "unsigned integer required".into())
}
fn array<'a>(v: &'a Value) -> Result<&'a Vec<Value>, String> {
    v.as_array().ok_or_else(|| "array required".into())
}

fn prefixes(
    input: &Path,
    table: &Table,
    tables: &'static EquityTables,
    config: Config,
    art: &artifacts::Artifacts,
) -> Result<BTreeMap<[u8; 16], usize>, String> {
    let out = &art.root;
    let mut rows = BufReader::new(File::open(input).map_err(|e| e.to_string())?).lines();
    let header: Value = serde_json::from_str(
        &rows
            .next()
            .ok_or("prefix header missing")?
            .map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;
    if header["format"] != "nplayer-warm-prefix-cohort-v1" || header["hands"] != 1536 {
        return Err("prefix cohort identity/count".into());
    }
    let mut output = art.fresh(&out.join("prefix-audit.jsonl"))?;
    let mut watch = BTreeMap::new();
    let mut hands = 0;
    line(
        &mut output,
        &json!({"format":"nplayer-warm-prefix-audit-v1","source_sha256":sha256_file(input)}),
    )?;
    for row in rows {
        let row: Value =
            serde_json::from_str(&row.map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
        let record = &row["record"];
        let ids = array(&record["identities"])?;
        let traverser = ids
            .iter()
            .position(|x| x == 0)
            .ok_or("focal identity missing")?;
        let deck = array(&record["deck"])?
            .iter()
            .map(|v| u8::try_from(integer(v)?).map_err(|e| e.to_string()))
            .collect::<Result<Vec<_>, _>>()?;
        let hand = Hand::from_deck(
            config,
            usize::try_from(integer(&record["button"])?).map_err(|e| e.to_string())?,
            &deck,
        )?;
        let mut state = CashState::new(hand, tables);
        let mut target = 1.;
        let mut sampling = 1.;
        let mut first_zero = None;
        let actions = array(&record["actions"])?;
        let actors = array(&record["actors"])?;
        let lookups = array(&record["lookups"])?;
        if actions.len() != actors.len() || actions.len() != lookups.len() {
            return Err("prefix decision arrays differ".into());
        }
        for (index, a) in actions.iter().enumerate() {
            let d = state
                .decision()
                .ok_or("prefix reached terminal too early")?;
            if integer(&actors[index])? as usize != d.actor {
                return Err("prefix actor mismatch".into());
            }
            let view = state.hand.observe(d.actor)?;
            let choices = multi_holdem::menu(&view);
            let kind = match a[0].as_str() {
                Some("fold") => Kind::Fold,
                Some("check") => Kind::Check,
                Some("call") => Kind::Call,
                Some("raise") => Kind::Raise,
                _ => return Err("bad saved action".into()),
            };
            let action = Action {
                kind,
                raise_to: integer(&a[1])?,
            };
            let action_index = choices
                .iter()
                .position(|(_, v)| *v == action)
                .ok_or("saved action outside declared menu")?;
            let stored = table.get(&d.key);
            if d.actor == traverser && d.street >= 2 && lookups[index]["status"] == "missing" {
                if stored.is_some()
                    || parse_key(lookups[index]["key"].as_str().ok_or("saved key missing")?)?
                        != d.key
                {
                    return Err("watched key membership/schema changed".into());
                }
                watch.insert(d.key, d.street);
                line(
                    &mut output,
                    &json!({"field":row["field"],"block":record["block"],"permutation":record["permutation"],"decision":index,
                    "key":multi_checkpoint::key_hex(&d.key),"street":d.street,"family":family(&state,d.actor),
                    "target_counterfactual_prefix":target,"proposal_counterfactual_prefix":sampling,
                    "correction":if sampling>0. {Some(target/sampling)} else {None},"first_zero_opponent_action":first_zero}),
                )?;
            }
            let sigma = probe::frozen_sigma(table, d)?;
            if d.actor != traverser {
                let q = probe::proposal(&sigma, probe::passive_index(d)?, true)?;
                if sigma[action_index] == 0. && first_zero.is_none() {
                    first_zero = Some(
                        json!({"decision":index,"actor":d.actor,"key":multi_checkpoint::key_hex(&d.key),"sigma":0.,"q":q[action_index],"action":a}),
                    );
                }
                target = probe::product(target, sigma[action_index])?;
                sampling = probe::product(sampling, q[action_index])?;
            }
            state.apply(action_index);
        }
        let settled = state
            .hand
            .settlement()
            .ok_or("saved prefix hand did not settle")?;
        let rewards = array(&record["rewards"])?;
        if rewards.len() != 4 || (0..4).any(|i| rewards[i].as_i64() != Some(settled.rewards[i])) {
            return Err("saved settlement changed".into());
        }
        hands += 1;
    }
    if hands != 1536 {
        return Err("prefix cohort hand count".into());
    }
    art.finish(output)?;
    Ok(watch)
}

fn mode(
    trainer: &hu20_trainer::multi_cfr::Trainer,
    game: &CashGame,
    watch: &BTreeMap<[u8; 16], usize>,
    art: &artifacts::Artifacts,
    biased: bool,
) -> Result<Value, String> {
    let out = &art.root;
    let name = if biased { "passive" } else { "reference" };
    let folder = out.join(name);
    std::fs::create_dir(&folder).map_err(|e| e.to_string())?;
    let mut output = art.fresh(&folder.join("roots.jsonl"))?;
    line(
        &mut output,
        &json!({"format":"nplayer-frozen-estimator-roots-v1","mode":name,"root_seed":ROOT_SEED,"batches":32,"roots_per_seat":8,"players":4,"source_checkpoint_sha256":WARM_SHA}),
    )?;
    let mut shadow = probe::Shadow::new(100000, watch)?;
    for batch in 0..32u64 {
        let roots = (0..32usize)
            .into_par_iter()
            .map(|index| {
                let seat = index / 8;
                let root = index % 8;
                let mut rng = StdRng::from_seed(seed(b"warm-probe-deal-v1", batch, seat, root));
                let mut state = game.sample(&mut rng);
                let mut sampler = PathSampler(u64::from_le_bytes(
                    seed(b"warm-probe-action-v1", batch, seat, root)[..8]
                        .try_into()
                        .unwrap(),
                ));
                let mut draw = |p: &[f64], path: u64| {
                    <PathSampler as Sampler<CashState>>::sample(&mut sampler, p, path)
                };
                probe::run(
                    &trainer.table,
                    &mut state,
                    seat,
                    biased,
                    (trainer.iteration + batch + 1) as f64,
                    &mut draw,
                    &family,
                )
                .map_err(|error| {
                    format!("{name} batch={batch} traverser={seat} root={root}: {error}")
                })
            })
            .collect::<Result<Vec<_>, _>>()?;
        for (index, r) in roots.iter().enumerate() {
            line(
                &mut output,
                &json!({"batch":batch,"traverser":index/8,"root":index%8,"linear_weight":trainer.iteration+batch+1,"result":r.value()}),
            )?;
        }
        shadow.batch(&roots)?;
    }
    art.finish(output)?;
    let mut rows = art.fresh(&folder.join("rows.jsonl"))?;
    for (key, row) in &shadow.rows {
        line(&mut rows, &row.value(key))?;
    }
    art.finish(rows)?;
    let summary = json!({"mode":name,"summary":shadow.summary(),"at_freeze":shadow.freeze_snapshot,
        "roots_sha256":art.sha(&folder.join("roots.jsonl"))?,"rows_sha256":art.sha(&folder.join("rows.jsonl"))?});
    let mut file = art.fresh(&folder.join("summary.json"))?;
    line(&mut file, &summary)?;
    art.finish(file)?;
    Ok(summary)
}
fn run() -> Result<(), String> {
    let a = std::env::args().collect::<Vec<_>>();
    if ![9, 10].contains(&a.len()) || a[1] != "run" {
        return Err("usage: nplayer_warm_estimator run CHECKPOINT CHECKPOINT_SHA K50 PREFIX_COHORT PREFIX_SHA NEW_OUT THREADS [INITIAL_REFERENCE]".into());
    }
    let checkpoint = Path::new(&a[2]);
    let table_path = Path::new(&a[4]);
    let cohort = Path::new(&a[5]);
    let out = Path::new(&a[7]);
    let threads: usize = a[8].parse().map_err(|_| "bad threads")?;
    if ![1, 2, 4, 8, 16].contains(&threads) {
        return Err("unsupported diagnostic thread count".into());
    }
    if a[3] != WARM_SHA || sha256_file(checkpoint) != WARM_SHA || sha256_file(cohort) != a[6] {
        return Err("warm checkpoint/prefix hash differs".into());
    }
    std::fs::create_dir(out).map_err(|e| e.to_string())?;
    let art = artifacts::Artifacts::new(out, a.get(9).map(Path::new));
    let start = Instant::now();
    let trainer = multi_checkpoint::load(checkpoint)?;
    let load_seconds = start.elapsed().as_secs_f64();
    if trainer.players != 4
        || trainer.seed != 2026102341001
        || trainer.counts.nodes != 10000017058
        || trainer.iteration != 566859
        || trainer.table.len() != 250003053
        || trainer.max_entries != 250000000
        || !trainer.freeze_at_cap
        || trainer.roots_per_seat != 8
        || trainer.frozen_at.is_none()
        || trainer.last_average_street != 3
        || trainer.prune.is_some()
    {
        return Err("wrong warmed recipe".into());
    }
    let tables = Box::leak(Box::new(EquityTables::load(table_path, false)?));
    let game = CashGame {
        config: Config::new(&[10000; 4], 50, 100)?,
        tables,
        schema: Default::default(),
    };
    if game.identity() != trainer.identity {
        return Err("warm game/card/menu identity differs".into());
    }
    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global()
        .map_err(|e| e.to_string())?;
    let tick = Instant::now();
    let watch = prefixes(cohort, &trainer.table, tables, game.config, &art)?;
    let prefix_seconds = tick.elapsed().as_secs_f64();
    let tick = Instant::now();
    let reference = mode(&trainer, &game, &watch, &art, false)?;
    let passive = mode(&trainer, &game, &watch, &art, true)?;
    let traversal_seconds = tick.elapsed().as_secs_f64();
    if sha256_file(checkpoint) != WARM_SHA || sha256_file(cohort) != a[6] {
        return Err("input changed during diagnostic".into());
    }
    let summary = json!({"status":"complete-diagnostic-only","input_checkpoint_sha256":WARM_SHA,"prefix_sha256":a[6],"watched_missing_keys":watch.len(),
        "prefix_audit_sha256":art.sha(&out.join("prefix-audit.jsonl"))?,"reference":reference,"passive":passive,"base_table_mutated":false,"no_training_or_strength_verdict":true});
    let mut summary_file = art.fresh(&out.join("summary.json"))?;
    line(&mut summary_file, &summary)?;
    art.finish(summary_file)?;
    std::fs::write(out.join("timing.json"),json!({"checkpoint_load_seconds":load_seconds,"prefix_audit_seconds":prefix_seconds,"root_traversal_and_write_seconds":traversal_seconds,"native_total_seconds":start.elapsed().as_secs_f64()}).to_string()).map_err(|e|e.to_string())?;
    std::fs::write(out.join("artifacts.json"), art.manifest().to_string())
        .map_err(|e| e.to_string())?;
    println!(
        "{}",
        json!({"status":"complete-diagnostic-only","summary_sha256":art.sha(&out.join("summary.json"))?})
    );
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
