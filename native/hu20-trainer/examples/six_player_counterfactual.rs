//! Conditional action values against public-only scripts. No training or arena.
use hu20_trainer::{
    cards::EquityTables,
    export::sha256_file,
    multi_arena::stream_seed,
    multi_checkpoint::key_hex,
    multi_counterfactual::{rollout, Belief, LegalState},
    multi_holdem::{self, KeySchema},
    multi_policy::{Mode, Policy, PolicyTable},
};
use rand::SeedableRng;
use rayon::prelude::*;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{BufRead, BufReader, BufWriter, Write},
    path::Path,
    sync::Arc,
    time::Instant,
};
const MODEL: &str = "f894a59f8a92424d735438726d16834901a7dcaf6d560c98b950fb72a143c9ea";
const CHECKPOINT: &str = "75245fbb0a00617ae67281e25cd7184b4a27fbf72e5aa2b175ba5a37c93771d8";
const AVERAGE: &str = "13822eb3ee8004ccf417a71274fe54a779e6bdf73a4b5b7c45201dbe1fe81dd8";
const MASS: &str = "806e7b9c92b7fbfd8f6ea2de30535d4dc7a525cc096091c458fe1e6c15000bda";
fn fresh(p: &Path) -> Result<BufWriter<File>, String> {
    Ok(BufWriter::new(
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(p)
            .map_err(|e| e.to_string())?,
    ))
}
fn emit(w: &mut impl Write, v: &Value) -> Result<(), String> {
    writeln!(w, "{v}").map_err(|e| e.to_string())
}
fn required<'a>(m: &'a Value, k: &str) -> Result<&'a str, String> {
    m[k].as_str().ok_or_else(|| format!("missing {k}"))
}
#[derive(Debug, PartialEq)]
struct World {
    q: Vec<f64>,
    lookups: [u64; 3],
}
fn seed(root: u64, id: &str, phase: &str, world: u64, kind: &str) -> u64 {
    let digest = Sha256::digest(id.as_bytes());
    stream_seed(
        root,
        format!("six-counterfactual-v1/{phase}/{kind}").as_bytes(),
        u64::from_le_bytes(digest[..8].try_into().unwrap()),
        world,
    )
}
fn worlds(
    s: &LegalState,
    b: &Belief,
    t: &EquityTables,
    model: &Arc<PolicyTable>,
    root: u64,
    phase: &str,
    count: u64,
) -> Result<Vec<World>, String> {
    (0..count)
        .into_par_iter()
        .map(|i| {
            let mut rng = rand::rngs::StdRng::seed_from_u64(seed(root, &s.id, phase, i, "deal"));
            let h = b.draw(s, &mut rng)?;
            let mut q = Vec::new();
            let mut lookups = [0; 3];
            for (_, a) in multi_holdem::menu(&h.observe(s.hero)?) {
                let stream = seed(root, &s.id, phase, i, "action");
                let mut hero = Policy::new(model.clone(), stream.wrapping_add(s.hero as u64));
                let value = rollout(h.clone(), s.hero, a, &s.opponents, stream, |o| {
                    let d = model.decision(o, t);
                    let tag = match model.rows.get(&d.key) {
                        None => 2,
                        Some(row) => match row.original_average_mass {
                            Some(true) => 0,
                            Some(false) => 1,
                            None => return Err("unclassified average mass".into()),
                        },
                    };
                    lookups[tag] += 1;
                    hero.choose(o, t)
                })?;
                if !value.is_finite() || !(-100. ..=500.).contains(&value) {
                    return Err("return outside six-player bounds".into());
                }
                q.push(value);
            }
            Ok(World { q, lookups })
        })
        .collect()
}
fn full_work(m: &Value) -> bool {
    m["mode"] == "main" || m["mode"] == "qualification-main"
}
fn admit_main(m: &Value) -> Result<(), String> {
    let path = required(m, "owner_admission")
        .map_err(|_| "main panel requires separately reviewed measured admission")?;
    let pin = required(m, "owner_admission_sha256")?;
    if sha256_file(Path::new(path)) != pin {
        return Err("owner admission changed".into());
    }
    let a: Value = serde_json::from_slice(&std::fs::read(path).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    if a["study"] != "PR438"
        || a["status"] != "owner-approved"
        || a["allocation_seconds"] != 900
        || a["discovery_worlds"] != 64
        || a["heldout_worlds"] != 2048
        || a["repetitions"] != 2
        || a["model_sha256"] != MODEL
        || a["states_sha256"] != m["states_sha256"]
    {
        return Err("frozen owner admission differs".into());
    }
    Ok(())
}
fn equal_bits(a: &[World], b: &[World]) -> bool {
    a.len() == b.len()
        && a.iter().zip(b).all(|(x, y)| {
            x.lookups == y.lookups
                && x.q.len() == y.q.len()
                && x.q
                    .iter()
                    .zip(&y.q)
                    .all(|(p, q)| p.to_bits() == q.to_bits())
        })
}
fn run(m: &Value) -> Result<(), String> {
    let phase = required(m, "mode")?;
    let qualification = phase == "qualification" || phase == "qualification-main";
    if !["qualification", "qualification-main", "calibrate", "main"].contains(&phase) {
        return Err("mode".into());
    }
    let root = m["belief_root"].as_u64().ok_or("belief_root")?;
    if !qualification
        && root
            != if phase == "calibrate" {
                20261026437002
            } else {
                20261026437001
            }
    {
        return Err("frozen belief root differs".into());
    }
    if phase == "main" {
        admit_main(m)?;
    }
    if full_work(m) && (m["discovery_worlds"] != 64 || m["heldout_worlds"] != 2048) {
        return Err("fixed discovery/heldout counts differ".into());
    }
    let threads = m["threads"].as_u64().ok_or("threads")? as usize;
    if !(1..=2).contains(&threads) {
        return Err("one or two workers required".into());
    }
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .map_err(|e| e.to_string())?;
    let output = Path::new(required(m, "out")?);
    std::fs::create_dir(output).map_err(|e| e.to_string())?;
    // Always create new evidence, including on failure; never overwrite a run.
    let result = execute(m, qualification, root, &pool, output);
    if let Err(error) = &result {
        let mut w = fresh(&output.join("failure.json"))?;
        emit(&mut w, &json!({"status":"failed","error":error}))?;
    }
    result
}
fn execute(
    m: &Value,
    qualification: bool,
    root: u64,
    pool: &rayon::ThreadPool,
    output: &Path,
) -> Result<(), String> {
    let start = Instant::now();
    let model_path = Path::new(required(m, "model")?);
    let pin = required(m, "model_sha256")?;
    if !qualification && pin != MODEL {
        return Err("PR431 binary pin differs".into());
    }
    let (mut table, load) = PolicyTable::load_profiled(model_path, pin, false)?;
    if table.players != 6
        || table.config().stacks() != [10000; 6]
        || table.scope != 3
        || table.mode != Mode::Average
        || table.schema != KeySchema::LiveOrder
    {
        return Err("frozen policy identity differs".into());
    }
    if qualification {
        table.rows.tag_all_mass(true);
    } else if table.binary_source_policy_sha256.as_deref() != Some(AVERAGE)
        || table.source_checkpoint_sha256 != CHECKPOINT
        || table
            .binary_mass_metadata
            .as_ref()
            .and_then(|v| v["receipt_sha256"].as_str())
            != Some(MASS)
    {
        return Err("checkpoint or embedded average-mass binding differs".into());
    }
    let model = Arc::new(table);
    let tables = EquityTables::load(Path::new(required(m, "tables")?), false)?;
    let load_seconds = start.elapsed().as_secs_f64();
    let input = Path::new(required(m, "states")?);
    if sha256_file(input) != required(m, "states_sha256")? {
        return Err("state inventory changed".into());
    }
    let mut states = Vec::new();
    let mut ids = std::collections::BTreeSet::new();
    for line in BufReader::new(File::open(input).map_err(|e| e.to_string())?).lines() {
        let v: Value =
            serde_json::from_str(&line.map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
        let s = LegalState::parse_six_check_call(&v)?;
        if !ids.insert(s.id.clone()) {
            return Err("duplicate state id".into());
        }
        states.push(s);
    }
    if states.is_empty() || states.len() > 36 {
        return Err("one to36 roots required".into());
    }
    let mut raw = fresh(&output.join("worlds.jsonl"))?;
    let mut repeated = fresh(&output.join("worlds.repeat.jsonl"))?;
    let mut roots = fresh(&output.join("roots.jsonl"))?;
    let mut progress = fresh(&output.join("progress.jsonl"))?;
    let solve_start = Instant::now();
    let mut costs = Vec::new();
    for s in &states {
        let timer = Instant::now();
        let belief = Belief::new(s)?;
        let hand = belief.draw(s, &mut rand::rngs::StdRng::seed_from_u64(0))?;
        let o = hand.observe(s.hero)?;
        let d = model.decision(&o, tables);
        if key_hex(&d.key) != s.expected_key {
            return Err(format!("archived live-order key differs: {}", s.id));
        }
        let (p, found) = model.distribution(&o, tables)?;
        let status = match model.rows.get(&d.key) {
            None => "missing",
            Some(r) => match r.original_average_mass {
                Some(true) => "positive_mass",
                Some(false) => "zero_mass",
                None => return Err("root mass unclassified".into()),
            },
        };
        let actions: Vec<_> = multi_holdem::menu(&o)
            .iter()
            .map(|(_, a)| json!([a.kind.name(), a.raise_to]))
            .collect();
        emit(
            &mut roots,
            &json!({"id":s.id,"hero":s.hero,"street":s.street,"stratum":s.stratum,"key":s.expected_key,"actions":actions,"probabilities":p,"found":found,"status":status}),
        )?;
        // Independent discovery/heldout domains; calibration never shares them.
        let phases: Vec<(&str, u64)> = if full_work(m) {
            vec![("discovery", 64), ("heldout", 2048)]
        } else {
            vec![(
                if qualification {
                    "fixture"
                } else {
                    "calibration"
                },
                8,
            )]
        };
        let mut hero_lookups = 0u64;
        for (domain, count) in &phases {
            let first =
                pool.install(|| worlds(s, &belief, tables, &model, root, domain, *count))?;
            let repeat =
                pool.install(|| worlds(s, &belief, tables, &model, root, domain, *count))?;
            if !equal_bits(&first, &repeat) {
                return Err(format!("float64/work reproduction differs: {}", s.id));
            }
            hero_lookups += first
                .iter()
                .map(|w| w.lookups.iter().sum::<u64>())
                .sum::<u64>();
            for (i, (x, y)) in first.iter().zip(&repeat).enumerate() {
                emit(
                    &mut raw,
                    &json!({"id":s.id,"phase":domain,"world":i,"values":x.q,"lookups":x.lookups}),
                )?;
                emit(
                    &mut repeated,
                    &json!({"id":s.id,"phase":domain,"world":i,"values":y.q,"lookups":y.lookups}),
                )?;
            }
        }
        let (repeat_p, repeat_found) = model.distribution(&hand.observe(s.hero)?, tables)?;
        if found != repeat_found
            || p.len() != repeat_p.len()
            || !p
                .iter()
                .zip(&repeat_p)
                .all(|(a, b)| a.to_bits() == b.to_bits())
        {
            return Err("root policy profile reproduction differs".into());
        }
        let seconds = timer.elapsed().as_secs_f64();
        let cost = json!({"id":s.id,"seconds_including_repeat":seconds,"worlds_per_pass":if full_work(m){2112}else{8},"actions":actions.len(),"hero_lookups":hero_lookups});
        emit(&mut progress, &cost)?;
        progress.flush().map_err(|e| e.to_string())?;
        costs.push(cost);
    }
    roots.flush().map_err(|e| e.to_string())?;
    raw.flush().map_err(|e| e.to_string())?;
    repeated.flush().map_err(|e| e.to_string())?;
    if sha256_file(&output.join("worlds.jsonl")) != sha256_file(&output.join("worlds.repeat.jsonl"))
    {
        return Err("byte reproduction differs".into());
    }
    let mut w = fresh(&output.join("verified.json"))?;
    emit(
        &mut w,
        &json!({"status":"passed","qualification_only":qualification,"calibration_only":!qualification && !full_work(m),"main_started":m["mode"]=="main","full_panel_work":full_work(m),"discovery_worlds":if full_work(m){64}else{0},"heldout_worlds":if full_work(m){2048}else{0},"root_profiles_reproduced":true,"worlds_repeat_sha256":sha256_file(&output.join("worlds.repeat.jsonl")),"roots":states.len(),"threads":pool.current_num_threads(),"model_sha256":pin,"source_checkpoint_sha256":model.source_checkpoint_sha256,"states_sha256":sha256_file(input),"worlds_sha256":sha256_file(&output.join("worlds.jsonl")),"roots_sha256":sha256_file(&output.join("roots.jsonl")),"float64_and_work_reproduced":true,"policy_load_seconds":load.total_seconds,"load_and_k50_seconds":load_seconds,"continuation_seconds_including_repeat":solve_start.elapsed().as_secs_f64(),"wall_seconds":start.elapsed().as_secs_f64(),"costs":costs}),
    )?;
    Ok(())
}
fn fixture(tables_path: &str, out: &Path) -> Result<(), String> {
    use flate2::{write::GzEncoder, Compression};
    use hu20_trainer::{
        multi_arena::Bot,
        nplayer::{Config, Hand},
    };
    std::fs::create_dir(out).map_err(|e| e.to_string())?;
    let tables = EquityTables::load(Path::new(tables_path), false)?;
    let mut states = fresh(&out.join("states.jsonl"))?;
    let mut rows = std::collections::BTreeMap::new();
    for hero in 0..6 {
        for street in 0..4 {
            let mut h = Hand::from_deck(
                Config::new(&[10000; 6], 50, 100)?,
                0,
                &(0..52).collect::<Vec<_>>(),
            )?;
            let mut actions = Vec::new();
            while h.street() as usize != street || h.actor() != Some(hero) {
                let actor = h.actor().ok_or("fixture ended")?;
                let a = Bot::new("check-call", 0)?.choose(&h.observe(actor)?)?;
                actions.push(json!([actor, a.kind.name(), a.raise_to]));
                h.apply_mut(a)?;
            }
            let o = h.observe(hero)?;
            let d = multi_holdem::observation_decision_for(KeySchema::LiveOrder, &o, tables);
            let opponents: Vec<_> = (0..6)
                .map(|s| if s == hero { "hero" } else { "check-call" })
                .collect();
            emit(
                &mut states,
                &json!({"id":format!("fixture-{hero}-{street}"),"hero":hero,"button":0,"hole":o.hole,"board":o.board,"actions":actions,"opponents":opponents,"street":street,"expected_key":key_hex(&d.key),"stratum":"fixture","split":"fixture"}),
            )?;
            rows.insert(d.key, (d.owner, d.street, d.code, d.len()));
        }
    }
    states.flush().map_err(|e| e.to_string())?;
    let model = out.join("fixture-policy.gz");
    let mut w = GzEncoder::new(fresh(&model)?, Compression::default());
    emit(
        &mut w,
        &json!({"format":"nplayer-policy-v1","identity":{"schema":multi_holdem::LIVE_ORDER_SCHEMA,"game":"nlhe-cash","players":6,"stacks":vec![10000;6],"small_blind":50,"big_blind":100,"menu":multi_holdem::MENU,"card_tables":hu20_trainer::cards::EQUITY_K50_SHA256,"utility_unit":"big-blind"},"players":6,"entries":rows.len(),"strategy":"average","last_average_street":3,"continuation":"none","missing":"uniform","source_checkpoint_sha256":"a".repeat(64)}),
    )?;
    for (k, (owner, street, code, n)) in &rows {
        emit(
            &mut w,
            &json!([key_hex(k), owner, street, code, vec![1. / *n as f64; *n]]),
        )?;
    }
    w.finish()
        .map_err(|e| e.to_string())?
        .flush()
        .map_err(|e| e.to_string())?;
    let mut manifest = fresh(&out.join("manifest.json"))?;
    emit(
        &mut manifest,
        &json!({"mode":"qualification","threads":2,"tables":tables_path,"model":model,"model_sha256":sha256_file(&model),"states":out.join("states.jsonl"),"states_sha256":sha256_file(&out.join("states.jsonl")),"belief_root":20261026437000u64,"out":out.join("run-v1")}),
    )
}
fn main() {
    let a: Vec<_> = std::env::args().collect();
    let result = if a.len() == 4 && a[1] == "fixture" {
        fixture(&a[2], Path::new(&a[3]))
    } else if a.len() == 2 {
        std::fs::read(&a[1])
            .map_err(|e| e.to_string())
            .and_then(|b| serde_json::from_slice(&b).map_err(|e| e.to_string()))
            .and_then(|m| run(&m))
    } else {
        Err("MANIFEST.json | fixture K50 NEW_DIR".into())
    };
    if let Err(e) = result {
        eprintln!("{e}");
        std::process::exit(1);
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bit_reproduction_rejects_signed_zero_and_work_changes() {
        assert!(!equal_bits(
            &[World {
                q: vec![0.],
                lookups: [0; 3]
            }],
            &[World {
                q: vec![-0.],
                lookups: [0; 3]
            }]
        ));
        assert!(!equal_bits(
            &[World {
                q: vec![1.],
                lookups: [0; 3]
            }],
            &[World {
                q: vec![1.],
                lookups: [1; 3]
            }]
        ));
    }
    #[test]
    fn domains_and_ids_do_not_share_random_streams() {
        let mut seeds = std::collections::BTreeSet::new();
        for id in ["a", "b"] {
            for p in ["discovery", "heldout", "calibration"] {
                for i in 0..8 {
                    for kind in ["deal", "action"] {
                        assert!(seeds.insert(seed(437, id, p, i, kind)));
                    }
                }
            }
        }
    }
    #[test]
    fn owner_admission_binds_budget_and_observations() {
        let path = std::env::temp_dir().join(format!(
            "pr438-admission-{}-{}.json",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let mut a = json!({"study":"PR438","status":"owner-approved","allocation_seconds":900,"discovery_worlds":64,"heldout_worlds":2048,"repetitions":2,"model_sha256":MODEL,"states_sha256":"d".repeat(64)});
        {
            let mut w = fresh(&path).unwrap();
            emit(&mut w, &a).unwrap();
        }
        let mut m = json!({"owner_admission":path,"owner_admission_sha256":sha256_file(&path),"states_sha256":"d".repeat(64)});
        assert!(admit_main(&m).is_ok());
        m["states_sha256"] = json!("e".repeat(64));
        assert!(admit_main(&m).is_err());
        a["allocation_seconds"] = json!(901);
        std::fs::write(&path, a.to_string()).unwrap();
        m["states_sha256"] = json!("d".repeat(64));
        m["owner_admission_sha256"] = json!(sha256_file(&path));
        assert!(admit_main(&m).is_err());
        std::fs::remove_file(&path).unwrap();
    }
    #[test]
    fn main_requires_reviewed_admission() {
        assert!(run(&json!({"mode":"main","belief_root":20261026437001u64}))
            .unwrap_err()
            .contains("separately reviewed"));
    }
}
