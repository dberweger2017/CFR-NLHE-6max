//! Bounded research qualification; no production option, deployment or export entry point.
use hu20_trainer::{
    cards::EquityTables,
    cfr::Key,
    game::Kind,
    multi_cfr::{Game, State, Table},
    multi_checkpoint::{self, key_hex},
    multi_holdem,
    multi_stacks::LiveMixtureGame,
};
use rand::{rngs::StdRng, SeedableRng};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, fs::File, io::Write, path::Path, time::Instant};
#[allow(dead_code)]
#[path = "support/warm_estimator.rs"]
mod coefficients;
#[path = "support/passive_learning_ledger.rs"]
mod ledger;
#[path = "support/passive_exploration.rs"]
mod probe;
#[cfg(test)]
#[path = "support/passive_exploration_tests.rs"]
mod tests;
const SEED: u64 = 20261028456011;
const WATCH_SEED: u64 = 20261028456002;
const EPSILON: f64 = 0.02;
fn write(path: &Path, x: &Value) -> Result<(), String> {
    let mut f = std::fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(path)
        .map_err(|e| e.to_string())?;
    serde_json::to_writer(&mut f, x).map_err(|e| e.to_string())?;
    writeln!(f).map_err(|e| e.to_string())
}
fn watches(game: &LiveMixtureGame, count: usize) -> BTreeMap<Key, Value> {
    use probe::DiagnosticState;
    let mut rng = StdRng::seed_from_u64(WATCH_SEED);
    let mut all: BTreeMap<Key, Value> = BTreeMap::new();
    for hand in 0..count {
        let mut state = game.sample(&mut rng);
        let mut raised = false;
        let mut steps = 0;
        while let Some(d) = state.decision() {
            steps += 1;
            assert!(steps < 10000);
            if d.street >= 2 {
                let entry=all.entry(d.key).or_insert_with(||json!({"street":d.street,"owner":d.owner,"code":d.code,"occurrences":0,"families":[],"first_hand":hand}));
                assert_eq!(entry["street"], json!(d.street));
                assert_eq!(entry["owner"], json!(d.owner));
                assert_eq!(entry["code"], json!(d.code));
                entry["occurrences"] = json!(entry["occurrences"].as_u64().unwrap() + 1);
                let family = state.family(d.actor);
                if !entry["families"]
                    .as_array()
                    .unwrap()
                    .contains(&json!(family))
                {
                    entry["families"]
                        .as_array_mut()
                        .unwrap()
                        .push(json!(family));
                }
            }
            let o = state.hand.observe(d.actor).unwrap();
            let choices = multi_holdem::menu(&o);
            let designated = match hand % 3 {
                1 => Some(0),
                2 => Some(1),
                _ => None,
            };
            let raise = if !raised && d.street > 0 && designated == Some(d.actor) {
                hu20_trainer::multi_cfr::pressure_action(d)
            } else {
                None
            };
            let a = raise.unwrap_or_else(|| {
                choices
                    .iter()
                    .position(|(_, a)| matches!(a.kind, Kind::Check | Kind::Call))
                    .expect("passive menu")
            });
            raised |= raise.is_some();
            state.apply(a);
        }
    }
    all
}
fn row_audit(table: &Table) -> Value {
    let mut rows = vec![[0u64; 5]; 4];
    for d in table.values() {
        assert!(d.regrets.iter().all(|x| x.is_finite()));
        assert!(d
            .average
            .is_some_and(|a| a.iter().all(|x| x.is_finite() && *x >= 0.)));
        let r = &mut rows[d.street as usize];
        r[0] += 1;
        r[1] += u64::from(d.visits == 0);
        r[2] += u64::from(d.visits >= 2);
        r[3] += u64::from(ledger::zero(d));
        r[4] += u64::from(d.average.unwrap().iter().all(|x| *x == 0.));
    }
    json!({"by_street":rows,"columns":["rows","no_traverser_visit","two_or_more_visits","fully_zero","zero_average_mass"]})
}
fn fingerprint(table: &Table, head: Value, file: Option<&Path>) -> Result<Value, String> {
    let tick = Instant::now();
    let mut hash = Sha256::new();
    let mut out = match file {
        Some(p) => Some(flate2::write::GzEncoder::new(
            std::fs::OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(p)
                .map_err(|e| e.to_string())?,
            flate2::Compression::fast(),
        )),
        None => None,
    };
    let mut emit = |v: Value| -> Result<(), String> {
        let mut bytes = serde_json::to_vec(&v).map_err(|e| e.to_string())?;
        bytes.push(b'\n');
        hash.update(&bytes);
        if let Some(out) = &mut out {
            out.write_all(&bytes).map_err(|e| e.to_string())?;
        }
        Ok(())
    };
    emit(head)?;
    for (k, d) in table.sorted() {
        emit(json!([
            key_hex(&k),
            d.actor,
            d.street,
            d.code,
            d.visits,
            d.regrets,
            d.average
        ]))?;
    }
    if let Some(out) = out {
        out.finish()
            .map_err(|e| e.to_string())?
            .sync_all()
            .map_err(|e| e.to_string())?;
    }
    Ok(
        json!({"logical_rows_sha256":format!("{:x}",hash.finalize()),"rows":table.len(),"write_or_hash_seconds":tick.elapsed().as_secs_f64(),"row_copy_retained":file.is_some()}),
    )
}
fn run(config: &Value) -> Result<(), String> {
    let mode = config["mode"].as_str().ok_or("mode")?;
    if !matches!(mode, "calibrate" | "initial" | "repeat") {
        return Err("unknown fixed mode".into());
    }
    if config["review_approved"] != true {
        return Err("independent review required".into());
    }
    if mode != "calibrate" && config["owner_approved"] != true {
        return Err("main allocation not accepted".into());
    }
    let (seed, cap, targets, watch_hands) = if mode == "calibrate" {
        (20261028456021, 100000, vec![8, 16], 64)
    } else {
        (SEED, 2000000, vec![128, 512], 512)
    };
    if config["seed"] != seed
        || config["cap"] != cap
        || config["targets"] != json!(targets)
        || config["watch_hands"] != watch_hands
        || config["threads"] != 2
    {
        return Err("fixed scope changed".into());
    }
    rayon::ThreadPoolBuilder::new()
        .num_threads(2)
        .build_global()
        .map_err(|e| e.to_string())?;
    let out = Path::new(config["out"].as_str().ok_or("out")?);
    std::fs::create_dir(out).map_err(|e| e.to_string())?;
    let start = Instant::now();
    let tables = EquityTables::load(Path::new(config["tables"].as_str().ok_or("tables")?), false)?;
    let watch = watches(&LiveMixtureGame::new(tables, 3)?, watch_hands);
    let inventory: Vec<_> = watch
        .iter()
        .map(|(k, v)| json!({"key":key_hex(k),"metadata":v}))
        .collect();
    let watch_pin = format!(
        "{:x}",
        Sha256::digest(serde_json::to_vec(&inventory).unwrap())
    );
    write(
        &out.join("watch-inventory.json"),
        &json!({"seed":WATCH_SEED,"hands":watch_hands,"keys":inventory,"sha256":watch_pin}),
    )?;
    let startup = start.elapsed().as_secs_f64();
    let mut arms = Vec::new();
    for eps in [0., EPSILON] {
        let game = LiveMixtureGame::new(tables, 3)?;
        let mut trainer = probe::ResearchTrainer::new(seed, cap, eps);
        let mut observer = ledger::Ledger::new(watch.clone());
        let name = if eps == 0. { "control" } else { "exploration" };
        let d = out.join(name);
        std::fs::create_dir(&d).map_err(|e| e.to_string())?;
        let identity = json!({"format":"passive-learning-research-table-v1","study":"PR457","base_game":game.identity(),"seed":seed,
          "target_policy":{"rule":"uniform-tremble-constrained-action-v1","epsilon":eps},"average":"actual-sigma-opponent-sampled","roots_per_seat":8,"max_entries":cap,"no_deployed_consumer":true});
        let mut endpoints = Vec::new();
        for target in &targets {
            let tick = Instant::now();
            while trainer.iteration < *target {
                if out.join("STOP").exists() {
                    return Err("owner STOP".into());
                }
                trainer.step(&game, |w, t, ds, m, f| {
                    observer.observe(w, t, ds, m, f, eps)
                })?;
                observer.after_merge(&trainer.table, trainer.frozen_at.is_some());
            }
            let training = tick.elapsed().as_secs_f64();
            let tick = Instant::now();
            let l = observer.value(&trainer.table);
            let audit = row_audit(&trainer.table);
            let inventory_hash = format!(
                "{:x}",
                Sha256::digest(serde_json::to_vec(&trainer.root_inventory).unwrap())
            );
            write(
                &d.join(format!("root-inventory-{target}.json")),
                &json!({"columns":["iteration","seat","root","path_seed"],"rows":trainer.root_inventory,"sha256":inventory_hash}),
            )?;
            let row_file = d.join(format!("rows-{target}.jsonl.gz"));
            let mut head = identity.clone();
            head["iteration"] = json!(target);
            let row = fingerprint(
                &trainer.table,
                head,
                if mode == "repeat" {
                    None
                } else {
                    Some(row_file.as_path())
                },
            )?;
            let endpoint = json!({"iteration":target,"entries":trainer.table.len(),"frozen_at":trainer.frozen_at,
              "counts":multi_checkpoint::counts_json(&trainer.counts),"seat_depth_draws":game.depths(),"learning":l,
              "row_audit":audit,"row_proof":row,"root_contexts":trainer.root_inventory.len(),"root_inventory_sha256":inventory_hash,
              "added_training_seconds":training,"readout_seconds":tick.elapsed().as_secs_f64()});
            write(&d.join(format!("endpoint-{target}.json")), &endpoint)?;
            endpoints.push(endpoint);
        }
        arms.push(json!({"name":name,"identity":identity,"endpoints":endpoints}));
    }
    write(
        &out.join("native-complete.json"),
        &json!({"status":"native-complete-proof-pending","mode":mode,"watch_inventory_sha256":watch_pin,
      "arms":arms,"startup_and_watch_seconds":startup,"wall_seconds":start.elapsed().as_secs_f64(),"no_strength_claim":true,"no_automatic_extension":true}),
    )
}
fn main() {
    let r = (|| {
        let a: Vec<_> = std::env::args().collect();
        if a.len() != 2 {
            return Err("one pinned config path required".into());
        }
        let config: Value = serde_json::from_reader(File::open(&a[1]).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
        run(&config)
    })();
    if let Err(e) = r {
        eprintln!("{e}");
        std::process::exit(2);
    }
}
