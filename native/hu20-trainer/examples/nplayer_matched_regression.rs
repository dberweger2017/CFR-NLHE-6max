//! Matched observations and known-script conditional action values, never training.
use hu20_trainer::{
    cards::EquityTables,
    export::sha256_file,
    multi_arena::stream_seed,
    multi_checkpoint::key_hex,
    multi_counterfactual::{rollout, Belief, LegalState},
    multi_holdem,
    multi_policy::{Policy, PolicyTable},
};
use rand::SeedableRng;
use rayon::prelude::*;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs::{File, OpenOptions},
    io::{BufRead, BufReader, BufWriter, Write},
    path::Path,
    sync::Arc,
    time::Instant,
};
#[path = "support/nplayer_mass_metadata.rs"]
mod mass;
fn fresh(path: &str) -> Result<BufWriter<File>, String> {
    Ok(BufWriter::new(
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .map_err(|e| e.to_string())?,
    ))
}
fn write(w: &mut BufWriter<File>, v: &Value) -> Result<(), String> {
    writeln!(w, "{v}").map_err(|e| e.to_string())
}
#[derive(PartialEq)]
struct Outcome {
    q: Vec<Vec<f64>>,
    equity: f64,
}
fn average(rows: &[Outcome], continuation: usize) -> Vec<f64> {
    let n = rows[0].q[continuation].len();
    (0..n)
        .map(|a| rows.iter().map(|r| r.q[continuation][a]).sum::<f64>() / rows.len() as f64)
        .collect()
}
fn worlds(
    s: &LegalState,
    belief: &Belief,
    tables: &EquityTables,
    models: &[Arc<PolicyTable>; 2],
    root: u64,
    count: u64,
    domain: &[u8],
) -> Result<Vec<Outcome>, String> {
    let digest = Sha256::digest(s.id.as_bytes());
    let id = u64::from_le_bytes(digest[..8].try_into().unwrap());
    (0..count)
        .collect::<Vec<_>>()
        .into_par_iter()
        .map(|world| {
            let mut rng = rand::rngs::StdRng::seed_from_u64(stream_seed(root, domain, id, world));
            let (hand, equity) = belief.draw_with_equity(s, &mut rng)?;
            let actions = multi_holdem::menu(&hand.observe(s.hero)?);
            let seed = stream_seed(
                root,
                b"continuation-action",
                id,
                world + if domain == b"discovery" { 0 } else { 1_000_000 },
            );
            let mut result = Vec::new();
            for model in models {
                let mut row = Vec::new();
                for (_, action) in &actions {
                    let mut hero = Policy::new(model.clone(), seed.wrapping_add(s.hero as u64));
                    row.push(rollout(
                        hand.clone(),
                        s.hero,
                        *action,
                        &s.opponents,
                        seed,
                        |o| hero.choose(o, tables),
                    )?);
                }
                result.push(row);
            }
            Ok(Outcome { q: result, equity })
        })
        .collect()
}

fn fixture(tables_path: &str, input: &str, out: &str) -> Result<(), String> {
    use flate2::{write::GzEncoder, Compression};
    let tables = EquityTables::load(Path::new(tables_path), false)?;
    let dir = Path::new(out);
    std::fs::create_dir(dir).map_err(|e| e.to_string())?;
    let states = std::fs::read_to_string(input).map_err(|e| e.to_string())?;
    let mut rows = BTreeMap::new();
    for line in states.lines() {
        let v: Value = serde_json::from_str(line).map_err(|e| e.to_string())?;
        let st = LegalState::parse(&v)?;
        let h = st.replay(&st.deck(None, &mut rand::rngs::StdRng::seed_from_u64(0))?)?;
        let o = h.observe(st.hero)?;
        let d = multi_holdem::observation_decision(&o, tables);
        if key_hex(&d.key) != st.expected_key {
            return Err("fixture source key differs".into());
        }
        let choices = multi_holdem::menu(&o);
        if choices.len() < 2 {
            return Err("fixture needs two choices".into());
        }
        let passive = choices
            .iter()
            .position(|(_, a)| {
                matches!(
                    a.kind,
                    hu20_trainer::game::Kind::Check | hu20_trainer::game::Kind::Call
                )
            })
            .unwrap_or(0);
        let different = (0..choices.len()).rev().find(|i| *i != passive).unwrap();
        rows.insert(
            d.key,
            (d.owner, d.street, d.code, choices.len(), passive, different),
        );
    }
    let mut keyset = Sha256::new();
    for k in rows.keys() {
        keyset.update(k);
    }
    let keyset = format!("{:x}", keyset.finalize());
    let mut models = json!({});
    for (i, alias) in ["baseline", "candidate"].iter().enumerate() {
        let sub = dir.join(alias);
        std::fs::create_dir(&sub).map_err(|e| e.to_string())?;
        let policy = sub.join("policy.gz");
        let h = json!({"format":"nplayer-policy-v1","identity":{"schema":multi_holdem::SCHEMA,"game":"nlhe-cash","players":3,"stacks":[10000,10000,10000],"small_blind":50,"big_blind":100,"menu":multi_holdem::MENU,"card_tables":hu20_trainer::cards::EQUITY_K50_SHA256,"utility_unit":"big-blind"},"players":3,"entries":rows.len(),"strategy":"average","last_average_street":3,"continuation":"none","missing":"uniform","source_checkpoint_sha256":"a".repeat(64)});
        let mut w = GzEncoder::new(
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&policy)
                .map_err(|e| e.to_string())?,
            Compression::default(),
        );
        writeln!(w, "{h}").map_err(|e| e.to_string())?;
        for (key, (owner, street, code, len, passive, different)) in &rows {
            let mut p = vec![0.; *len];
            p[if i == 0 { *passive } else { *different }] = 1.;
            writeln!(w, "{}", json!([key_hex(key), owner, street, code, p]))
                .map_err(|e| e.to_string())?;
        }
        w.finish().map_err(|e| e.to_string())?;
        let pin = sha256_file(&policy);
        let zero = sub.join("zero-keys.bin");
        std::fs::write(&zero, []).map_err(|e| e.to_string())?;
        let receipt = sub.join("receipt.json");
        let m = json!({"format":"nplayer-average-mass-v1","status":"passed","strategy":"average","last_average_street":3,"checkpoint_sha256":"a".repeat(64),"policy_sha256":pin,"rows":rows.len(),"average_rows":rows.len(),"current_rows":0,"zero_mass_rows":0,"positive_mass_rows":rows.len(),"keyset_sha256":keyset,"zero_keys_sha256":sha256_file(&zero)});
        std::fs::write(&receipt, m.to_string()).map_err(|e| e.to_string())?;
        models[*alias] =
            json!({"path":policy,"sha256":pin,"mass":sub,"mass_sha256":sha256_file(&receipt)});
    }
    let path = dir.join("legal-states.jsonl");
    std::fs::write(&path, states).map_err(|e| e.to_string())?;
    let m = json!({"threads":4,"models":models,"tables":tables_path,"states":path,"states_sha256":sha256_file(&path),"belief_root":20261020362901u64,"discovery_worlds":32,"heldout_worlds":512,"matched":dir.join("matched.jsonl"),"selected":dir.join("selected.jsonl"),"values":dir.join("values.jsonl"),"result":dir.join("native-result.json"),"qualification":"synthetic normalized rows and synthetic mass receipts; no trained strength result"});
    std::fs::write(dir.join("manifest.json"), m.to_string()).map_err(|e| e.to_string())?;
    println!("{}", json!({"status":"prepared","rows":rows.len()}));
    Ok(())
}
fn run() -> Result<(), String> {
    let argv: Vec<_> = std::env::args().collect();
    if argv.len() == 5 && argv[1] == "fixture" {
        return fixture(&argv[2], &argv[3], &argv[4]);
    }
    if argv.len() != 2 {
        return Err("MANIFEST.json".into());
    }
    let m: Value = serde_json::from_slice(&std::fs::read(&argv[1]).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    let threads = m["threads"].as_u64().ok_or("threads")? as usize;
    if !(1..=8).contains(&threads) || m["discovery_worlds"] != 32 || m["heldout_worlds"] != 512 {
        return Err("fixed work counts changed".into());
    }
    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global()
        .map_err(|e| e.to_string())?;
    let started = Instant::now();
    let mut list = Vec::new();
    let mut mass_pins = Vec::new();
    for alias in ["baseline", "candidate"] {
        let p = &m["models"][alias];
        let path = p["path"].as_str().ok_or("model path")?;
        let pin = p["sha256"].as_str().ok_or("model pin")?;
        let mut table = PolicyTable::load(Path::new(path), pin)?;
        let metadata = mass::MassMetadata::load(
            Path::new(p["mass"].as_str().ok_or("mass path")?),
            p["mass_sha256"].as_str().ok_or("mass pin")?,
            pin,
            &mut table,
        )?;
        if mass_pins
            .last()
            .is_some_and(|m: &Value| m["keyset_sha256"] != metadata.keyset_sha256)
        {
            return Err("membership keysets differ".into());
        }
        mass_pins.push(json!({"receipt_sha256":metadata.receipt_sha256,"keyset_sha256":metadata.keyset_sha256}));
        list.push(Arc::new(table));
    }
    let models: [Arc<PolicyTable>; 2] = list.try_into().ok().unwrap();
    if models[0].identity != models[1].identity {
        return Err("model identity differs".into());
    }
    let tables = EquityTables::load(Path::new(m["tables"].as_str().ok_or("tables")?), false)?;
    let load_seconds = started.elapsed().as_secs_f64();
    let input = m["states"].as_str().ok_or("states")?;
    if sha256_file(Path::new(input)) != m["states_sha256"].as_str().ok_or("state pin")? {
        return Err("legal states changed".into());
    }
    let root = m["belief_root"].as_u64().ok_or("belief root")?;
    let mut output = fresh(m["matched"].as_str().ok_or("matched output")?)?;
    let mut chosen: BTreeMap<String, (f64, String, Value, Value)> = BTreeMap::new();
    let mut counts = BTreeMap::<String, usize>::new();
    let mut total = 0;
    for line in BufReader::new(File::open(input).map_err(|e| e.to_string())?).lines() {
        let v: Value =
            serde_json::from_str(&line.map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
        let s = LegalState::parse(&v)?;
        let hand = s.replay(&s.deck(None, &mut rand::rngs::StdRng::seed_from_u64(0))?)?;
        let observation = hand.observe(s.hero)?;
        let d = multi_holdem::observation_decision(&observation, tables);
        if key_hex(&d.key) != s.expected_key {
            return Err("reconstructed key differs from archived matched state".into());
        }
        let p0 = models[0].distribution(&observation, tables)?;
        let p1 = models[1].distribution(&observation, tables)?;
        if p0.1 != p1.1 {
            return Err("frozen memberships differ".into());
        }
        let probabilities = [p0.0, p1.0];
        let tv = probabilities[0]
            .iter()
            .zip(&probabilities[1])
            .map(|(a, b)| (a - b).abs())
            .sum::<f64>()
            / 2.;
        let actions: Vec<_> = multi_holdem::menu(&observation)
            .iter()
            .map(|(_, a)| json!([a.kind.name(), a.raise_to]))
            .collect();
        let statuses: Vec<_> = models
            .iter()
            .map(|t| mass::MassMetadata::classify_row(t.rows.get(&d.key)).map(|i| mass::LABELS[i]))
            .collect::<Result<_, _>>()?;
        let mut visible_cards = observation.board.to_vec();
        visible_cards.extend_from_slice(&observation.hole);
        let strength = if observation.board.is_empty() {
            json!({"stage":"preflop","pair":observation.hole[0]/4==observation.hole[1]/4,"high_rank":observation.hole.iter().map(|c|c/4+2).max(),"suited":observation.hole[0]%4==observation.hole[1]%4})
        } else {
            json!({"stage":"postflop","made_category":hu20_buckets::evaluate(&visible_cards)>>20})
        };
        let record = json!({"state":v,"probabilities":probabilities,"actions":actions,"total_variation":tv,"statuses":statuses,"visible_strength":strength,
            "pot":observation.players.iter().map(|p|p.contributed).sum::<u64>(),"position":(s.hero+3-s.button)%3});
        write(&mut output, &record)?;
        *counts
            .entry(format!("{}:{}", s.stratum, s.split))
            .or_default() += 1;
        total += 1;
        if s.split == "discovery" && tv > 1e-14 {
            let replace = chosen.get(&s.stratum).map_or(true, |(old, id, _, _)| {
                tv > *old || (tv == *old && s.id < *id)
            });
            if replace {
                chosen.insert(s.stratum.clone(), (tv, s.id.clone(), v, record));
            }
        }
    }
    output.flush().map_err(|e| e.to_string())?;
    if chosen.len() > 16 {
        return Err("fixed selected panel exceeds16 states/lineage".into());
    }
    let mut values = fresh(m["values"].as_str().ok_or("values output")?)?;
    let mut selected = fresh(m["selected"].as_str().ok_or("selected output")?)?;
    let mut q_seconds = 0.;
    for (stratum, (_, _, v, record)) in &chosen {
        let tick = Instant::now();
        let s = LegalState::parse(v)?;
        let belief = Belief::new(&s)?;
        let discovery = worlds(&s, &belief, tables, &models, root, 32, b"discovery")?;
        if discovery != worlds(&s, &belief, tables, &models, root, 32, b"discovery")? {
            return Err("discovery reproduction differs".into());
        }
        let means = average(&discovery, 1);
        let best = (0..means.len())
            .max_by(|a, b| means[*a].total_cmp(&means[*b]).then_with(|| b.cmp(a)))
            .unwrap();
        let heldout = worlds(&s, &belief, tables, &models, root, 512, b"heldout")?;
        if heldout != worlds(&s, &belief, tables, &models, root, 512, b"heldout")? {
            return Err("heldout reproduction differs".into());
        }
        let diagnostics = json!({"tag_supported_holdings":if belief.holding_count()>0 {Some(belief.holding_count())}else{None},"effective_holdings":if belief.holding_count()>0 {Some(belief.effective_holdings())}else{None},
            "entropy":if belief.holding_count()>0 {Some(-belief.probabilities.iter().filter(|p|**p>0.).map(|p|p*p.ln()).sum::<f64>())}else{None},
            "model":"uniform compatible cards; exact one-TAG action likelihood enumeration; random likelihood cancels"});
        write(
            &mut selected,
            &json!({"matched":record,"selected_action_index":best,"discovery_action_means_candidate_continuation":means,
            "belief":diagnostics,"discovery_worlds":32,"heldout_worlds":512}),
        )?;
        for (world, q) in heldout.iter().enumerate() {
            write(
                &mut values,
                &json!({"state_id":s.id,"stratum":stratum,"world":world,"q":q.q,"showdown_share":q.equity}),
            )?;
        }
        q_seconds += tick.elapsed().as_secs_f64();
        println!(
            "{}",
            json!({"event":"progress","selected_state":s.id,"completed":q_seconds})
        );
        std::io::stdout().flush().map_err(|e| e.to_string())?;
    }
    values.flush().map_err(|e| e.to_string())?;
    selected.flush().map_err(|e| e.to_string())?;
    let result = json!({"status":"passed","manifest_sha256":sha256_file(Path::new(&argv[1])),"model_pins":m["models"],"states":total,"selected":chosen.len(),"strata":counts,"load_seconds":load_seconds,"mass_pins":mass_pins,
        "counterfactual_seconds":q_seconds,"wall_seconds":started.elapsed().as_secs_f64(),"worlds_per_selected_state":544,"reproduced_worlds_per_selected_state":544,
        "matched_sha256":sha256_file(Path::new(m["matched"].as_str().unwrap())),
        "selected_sha256":sha256_file(Path::new(m["selected"].as_str().unwrap())),
        "values_sha256":sha256_file(Path::new(m["values"].as_str().unwrap()))});
    let mut result_file = fresh(m["result"].as_str().ok_or("result output")?)?;
    write(&mut result_file, &result)?;
    println!("{result}");
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("nplayer_matched_regression: {e}");
        std::process::exit(2);
    }
}
