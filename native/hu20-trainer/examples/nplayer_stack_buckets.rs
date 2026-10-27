//! Fixed public-abstraction qualification and cost/support pilot; no strength arena.
#[allow(dead_code)]
#[path = "nplayer_variable_stack.rs"]
mod reference;
use hu20_trainer::{
    cards::EquityTables,
    cfr::Key,
    game::Kind,
    gz::Gzip,
    multi_binary,
    multi_cfr::Trainer,
    multi_checkpoint,
    multi_holdem::{self, KeySchema},
    multi_policy::{self, Mode, PolicyTable},
    multi_stacks::StackMixtureGame,
    nplayer::{Event, Hand, Observation},
};
use serde_json::{json, Value};
use std::{
    collections::{BTreeMap, BTreeSet},
    io::Write,
    path::Path,
    sync::Arc,
    time::Instant,
};
const ORIGINAL: u64 = 20261026441002;
const HELDOUT: u64 = 20261026443002;
const SEED: u64 = 20261026441011;
const TARGETS: [u64; 3] = [5_000_000, 25_000_000, 100_000_000];
fn write(p: &Path, v: Value) -> Result<(), String> {
    let mut f = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(p)
        .map_err(|e| e.to_string())?;
    writeln!(f, "{v}").map_err(|e| e.to_string())
}
fn read(p: &Path) -> Result<Value, String> {
    serde_json::from_slice(&std::fs::read(p).map_err(|e| e.to_string())?).map_err(|e| e.to_string())
}

/// Independent reconstruction of protected public contracts, not the key payload.
fn contract(o: &Observation<'_>) -> Value {
    let n = o.config.players();
    let seats: Vec<_> = (0..n).map(|i| (o.button + i) % n).collect();
    let rel = |s: usize| (s + n - o.button) % n;
    let mut comparisons = Vec::new();
    for i in 0..n {
        for j in i + 1..n {
            let a = o.players[seats[i]];
            let b = o.players[seats[j]];
            comparisons.push(format!(
                "{:?}/{:?}",
                a.contributed.cmp(&b.contributed),
                a.street_bet.cmp(&b.street_bet)
            ));
        }
    }
    let mut aggressors = vec![None; o.street as usize + 1];
    for event in o.history {
        if let Event::Action {
            street,
            actor,
            action,
            ..
        } = event
        {
            if action.kind == Kind::Raise {
                aggressors[*street as usize] = Some(rel(*actor));
            }
        }
    }
    let hero = o.players[o.seat];
    let legal = o.legal.unwrap();
    json!({"n":n,"actor":rel(o.seat),"street":o.street as usize,"sb":o.config.small_blind(),"bb":o.config.big_blind(),
      "initial":seats.iter().map(|&s|o.config.stacks()[s]).collect::<Vec<_>>(),
      "status":seats.iter().map(|&s|(o.players[s].folded,o.players[s].stack==0)).collect::<Vec<_>>(),
      "contribution_and_bet_topology":comparisons,"original_aggressors":aggressors,
      "call_all_in":legal.call_amount>0&&legal.call_amount==hero.stack,
      "menu":multi_holdem::menu(o).iter().map(|(l,a)|(*l,a.kind.name(),a.kind==Kind::Raise&&a.raise_to==hero.stack+hero.street_bet)).collect::<Vec<_>>()})
}
struct Group {
    protected: Value,
    count: u64,
    reference: BTreeSet<Key>,
    history: BTreeSet<Key>,
    numerical: BTreeSet<String>,
    targets: BTreeSet<String>,
    low: Vec<u64>,
    high: Vec<u64>,
}
fn audit(
    panel: &[(usize, Hand)],
    seed: u64,
    tables: &EquityTables,
    t: &Trainer,
    model: &PolicyTable,
) -> Result<Value, String> {
    let mut cells = vec![vec![vec![[0u64; 4]; 4]; 3]; 27];
    let mut groups: BTreeMap<Key, Group> = BTreeMap::new();
    let mut bits = Vec::new();
    let mut side = cells.clone();
    let mut all_in = cells.clone();
    for (tuple, h) in panel {
        let o = h.observe(h.actor().unwrap())?;
        let d = model.decision(&o, tables);
        let raw = multi_holdem::observation_decision_for(KeySchema::StackOwner, &o, tables);
        let hist = multi_holdem::observation_decision_for(KeySchema::History, &o, tables);
        let protected = contract(&o);
        let n = o.config.players();
        let amounts: Vec<u64> = (0..n)
            .flat_map(|i| {
                let p = o.players[(o.button + i) % n];
                [
                    p.stack,
                    p.street_bet,
                    p.contributed,
                    p.contributed - p.street_bet,
                ]
            })
            .collect();
        let targets = multi_holdem::menu(&o)
            .iter()
            .map(|(l, a)| (*l, a.kind.name(), a.raise_to))
            .collect::<Vec<_>>();
        let g = groups.entry(d.key).or_insert_with(|| Group {
            protected: protected.clone(),
            count: 0,
            reference: BTreeSet::new(),
            history: BTreeSet::new(),
            numerical: BTreeSet::new(),
            targets: BTreeSet::new(),
            low: amounts.clone(),
            high: amounts.clone(),
        });
        if g.protected != protected {
            return Err("same-key protected public contract differs".into());
        }
        g.count += 1;
        g.reference.insert(raw.key);
        g.history.insert(hist.key);
        g.numerical.insert(serde_json::to_string(&amounts).unwrap());
        g.targets.insert(serde_json::to_string(&targets).unwrap());
        for i in 0..amounts.len() {
            g.low[i] = g.low[i].min(amounts[i]);
            g.high[i] = g.high[i].max(amounts[i]);
        }
        let row = t.table.get(&d.key);
        let status = match row {
            None => 0,
            Some(e) if e.average.is_some_and(|v| v.iter().any(|x| *x > 0.)) => 2,
            _ => 1,
        };
        let c = &mut cells[*tuple][o.seat][o.street as usize];
        c[status] += 1;
        c[3] += 1;
        let (p, found) = model.distribution(&o, tables)?;
        if found != row.is_some() {
            return Err("checkpoint/binary found differs".into());
        }
        let expected = row
            .map(|e| e.policy(true)[..d.len()].to_vec())
            .unwrap_or_else(|| vec![1. / d.len() as f64; d.len()]);
        if p.iter()
            .map(|v| v.to_bits())
            .ne(expected.iter().map(|v| v.to_bits()))
        {
            return Err("panel checkpoint/binary float64 differs".into());
        }
        for v in p {
            bits.extend_from_slice(&v.to_bits().to_le_bytes());
        }
        let levels: BTreeSet<_> = o
            .players
            .iter()
            .map(|p| p.contributed)
            .filter(|v| *v > 0)
            .collect();
        let multi = levels
            .iter()
            .filter(|&&v| o.players.iter().filter(|p| p.contributed >= v).count() > 1)
            .count()
            > 1;
        side[*tuple][o.seat][o.street as usize][0] += u64::from(multi);
        all_in[*tuple][o.seat][o.street as usize][0] +=
            u64::from(o.players.iter().any(|p| !p.folded && p.stack == 0));
    }
    let merged:Vec<_>=groups.iter().filter(|(_,g)|g.reference.len()>1).map(|(k,g)|json!({"key":multi_checkpoint::key_hex(k),"observations":g.count,"reference_keys":g.reference.len(),"history_keys":g.history.len(),"numerical_variants":g.numerical.len(),"legal_target_variants":g.targets.len(),"protected_contract":g.protected,"amount_fields":"button-relative seats, each remaining/streetbet/total/prior contribution","amount_min":g.low,"amount_max":g.high,"observed_legal_targets":g.targets.iter().map(|s|serde_json::from_str::<Value>(s).unwrap()).collect::<Vec<_>>()})).collect();
    let all_reference: BTreeSet<_> = groups
        .values()
        .flat_map(|g| g.reference.iter().copied())
        .collect();
    Ok(
        json!({"seed":seed,"hands":if seed==0 {648}else{324},"observations":panel.len(),"schema":model.schema.name(),"cells":cells,
      "cell_axes":["tuple","physical_seat","street"],"cell_columns":["missing","zero_average_mass","positive_average_mass","observations"],
      "provisional_multi_layer":side,"all_in_exposure":all_in,"schema_keys":groups.len(),"reference_keys":all_reference.len(),
      "merged_reference_key_groups":merged,"protected_contract_violations":0,"checkpoint_binary_panel_float64_parity":true,
      "probability_bits_digest":multi_checkpoint::key_hex(&hu20_trainer::key::digest16(&bits)),
      "limits":"Fixed synthetic observations, not population coverage. Intentional history/card/amount merges are not strategic equivalence. Numerical ranges and target variants are descriptive, not quality guarantees."}),
    )
}
fn panels(tables: &EquityTables) -> Result<[Vec<(usize, Hand)>; 2], String> {
    Ok([
        reference::panel_for(tables, ORIGINAL)?,
        reference::panel_for(tables, HELDOUT)?,
    ])
}
fn audit_pair(
    out: &Path,
    tables: &EquityTables,
    t: &Trainer,
    model: &PolicyTable,
    p: &[Vec<(usize, Hand)>; 2],
) -> Result<(), String> {
    write(
        &out.join("original-panel.json"),
        audit(&p[0], ORIGINAL, tables, t, model)?,
    )?;
    write(
        &out.join("heldout-panel.json"),
        audit(&p[1], HELDOUT, tables, t, model)?,
    )?;
    let union: Vec<_> = p[0].iter().chain(p[1].iter()).cloned().collect();
    write(
        &out.join("union-panel.json"),
        audit(&union, 0, tables, t, model)?,
    )
}
fn qualify(tables: &'static EquityTables, out: &Path) -> Result<(), String> {
    reference::qualify_for(tables, out, KeySchema::StackBuckets, 20261026443001)?;
    let t = multi_checkpoint::load(&out.join("full.gz"))?;
    let model = PolicyTable::load(
        &out.join("policy.bin"),
        &reference::hash(&out.join("policy.bin"))?,
    )?;
    audit_pair(out, tables, &t, &model, &panels(tables)?)
}
fn reference_audit(m: &Value) -> Result<(), String> {
    let out = Path::new(m["out"].as_str().ok_or("output")?);
    std::fs::create_dir(out).map_err(|e| e.to_string())?;
    let tables = EquityTables::load(Path::new(m["tables"].as_str().ok_or("K50")?), false)?;
    let panel = panels(tables)?;
    let specs = m["references"].as_array().ok_or("references")?;
    if specs.len() != 3 {
        return Err("three fixed reference endpoints required".into());
    }
    let mut results = Vec::new();
    for (i, s) in specs.iter().enumerate() {
        if s["target_nodes"] != TARGETS[i] {
            return Err("reference target order differs".into());
        }
        let path = Path::new(s["checkpoint"].as_str().ok_or("checkpoint")?);
        if reference::hash(path)? != s["checkpoint_sha256"].as_str().ok_or("checkpoint pin")? {
            return Err("reference checkpoint changed".into());
        }
        let tick = Instant::now();
        let t = multi_checkpoint::load(path)?;
        if t.seed != SEED
            || t.counts.nodes < TARGETS[i]
            || t.identity["schema"] != multi_holdem::STACK_OWNER_SCHEMA
        {
            return Err("reference identity differs".into());
        }
        let model = PolicyTable::load(
            Path::new(s["binary"].as_str().ok_or("binary")?),
            s["binary_sha256"].as_str().ok_or("binary pin")?,
        )?;
        if model.source_checkpoint_sha256 != s["checkpoint_sha256"] || model.identity != t.identity
        {
            return Err("reference binary association differs".into());
        }
        let d = out.join(TARGETS[i].to_string());
        std::fs::create_dir(&d).map_err(|e| e.to_string())?;
        audit_pair(&d, tables, &t, &model, &panel)?;
        results.push(json!({"target_nodes":TARGETS[i],"actual_nodes":t.counts.nodes,"entries":t.table.len(),"wall_seconds":tick.elapsed().as_secs_f64(),"checkpoint_sha256":s["checkpoint_sha256"],"binary_sha256":s["binary_sha256"]}));
    }
    write(
        &out.join("verified.json"),
        json!({"status":"passed","no_training":true,"reference_original_mass_source":"checkpoint","endpoints":results}),
    )
}
fn pilot(m: &Value) -> Result<(), String> {
    let owner = read(Path::new(
        m["owner_admission"].as_str().ok_or("owner receipt")?,
    ))?;
    if m["mode"] != "pilot"
        || m["seed"] != SEED
        || m["targets"] != json!(TARGETS)
        || m["threads"] != 2
        || m["max_entries"] != 10_000_000
        || owner["study"] != "PR444"
        || owner["status"] != "owner-approved"
        || owner["targets"] != json!(TARGETS)
        || owner["seed"] != SEED
        || owner["allocation_seconds"] != 1200
    {
        return Err("fixed accepted pilot scope differs".into());
    }
    let out = Path::new(m["out"].as_str().ok_or("output")?);
    std::fs::create_dir(out).map_err(|e| e.to_string())?;
    let tables = EquityTables::load(Path::new(m["tables"].as_str().ok_or("K50")?), false)?;
    let panel = panels(tables)?;
    let game = StackMixtureGame::with_schema(tables, KeySchema::StackBuckets)?;
    let mut t = reference::trainer(&game, 10_000_000, SEED);
    let mut ledger = reference::Ledger::new_for(&panel[0], tables, KeySchema::StackBuckets);
    let mut endpoints = Vec::new();
    for target in TARGETS {
        let d = out.join(target.to_string());
        std::fs::create_dir(&d).map_err(|e| e.to_string())?;
        let tick = Instant::now();
        while t.counts.nodes < target {
            if out.join("STOP").exists() {
                return Err("ownerSTOP".into());
            }
            reference::train_steps(&game, &mut t, &mut ledger, 1);
            if t.iteration % 100 == 0 {
                write(
                    &d.join(format!("progress-{}.json", t.iteration)),
                    json!({"nodes":t.counts.nodes,"entries":t.table.len(),"frozen_at":t.frozen_at,"elapsed_seconds":tick.elapsed().as_secs_f64()}),
                )?;
            }
        }
        let training = tick.elapsed().as_secs_f64();
        let tick = Instant::now();
        multi_checkpoint::save(&t, &d.join("checkpoint.gz"), Gzip::Parallel)?;
        let save = tick.elapsed().as_secs_f64();
        let tick = Instant::now();
        let source = reference::hash(&d.join("checkpoint.gz"))?;
        multi_policy::write_trainer(
            &t,
            &source,
            Mode::Average,
            &d.join("average.gz"),
            Gzip::Parallel,
        )?;
        let export = tick.elapsed().as_secs_f64();
        let tick = Instant::now();
        let average = reference::hash(&d.join("average.gz"))?;
        multi_binary::convert(&d.join("average.gz"), &average, &d.join("policy.bin"), None)?;
        let conversion = tick.elapsed().as_secs_f64();
        let tick = Instant::now();
        let bin = reference::hash(&d.join("policy.bin"))?;
        let proof = multi_binary::verify(
            &d.join("average.gz"),
            &average,
            &d.join("policy.bin"),
            &bin,
            None,
        )?;
        let audit_seconds = tick.elapsed().as_secs_f64();
        let tick = Instant::now();
        let model = Arc::new(PolicyTable::load(&d.join("policy.bin"), &bin)?);
        let load = tick.elapsed().as_secs_f64();
        let tick = Instant::now();
        let initial = reference::play(&d.join("initial.jsonl"), model.clone(), &t, tables)?;
        let repeat = reference::play(&d.join("repeat.jsonl"), model.clone(), &t, tables)?;
        if initial != repeat {
            return Err("play reproduction differs".into());
        }
        write(&d.join("retained-rows.json"), reference::retained_rows(&t))?;
        write(&d.join("learning.json"), ledger.value())?;
        audit_pair(&d, tables, &t, &model, &panel)?;
        let e = json!({"target_nodes":target,"actual_nodes":t.counts.nodes,"entries":t.table.len(),"frozen_at":t.frozen_at,
          "checkpoint_sha256":source,"average_sha256":average,"binary_verification":proof,
          "training_seconds":training,"save_seconds":save,"export_seconds":export,"conversion_seconds":conversion,
          "audit_seconds":audit_seconds,"load_seconds":load,"play_repeat_panels_readout_seconds":tick.elapsed().as_secs_f64(),
          "roots_cumulative":game.counts(),"buttons_cumulative":game.buttons(),"counts":multi_checkpoint::counts_json(&t.counts),"initial_repeat":initial,"no_strength_claim":true});
        write(&d.join("endpoint.json"), e.clone())?;
        endpoints.push(e);
    }
    write(
        &out.join("native-complete.json"),
        json!({"status":"native-complete-proof-pending","endpoints":endpoints,"no_extra_training":true}),
    )
}
fn main() {
    let a: Vec<_> = std::env::args().collect();
    let r = (|| {
        rayon::ThreadPoolBuilder::new()
            .num_threads(2)
            .build_global()
            .map_err(|e| e.to_string())?;
        match a.get(1).map(String::as_str) {
            Some("qualify") if a.len() == 4 => {
                let out = Path::new(&a[3]);
                std::fs::create_dir(out).map_err(|e| e.to_string())?;
                qualify(EquityTables::load(Path::new(&a[2]), false)?, out)
            }
            Some("reference") if a.len() == 3 => reference_audit(&read(Path::new(&a[2]))?),
            Some("pilot") if a.len() == 3 => pilot(&read(Path::new(&a[2]))?),
            _ => {
                Err("qualify K50 NEW_OUTPUT | reference MANIFEST | pilot APPROVED_MANIFEST".into())
            }
        }
    })();
    if let Err(e) = r {
        eprintln!("stack-buckets: {e}");
        std::process::exit(2);
    }
}
