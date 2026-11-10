//! Deep CFR traversals and the network bench (docs/neural-deep-cfr.md).
//!
//!     nplayer_deep_cfr traverse --advantage NET SHA256 --tables K50 --seed S --iteration T
//!         --traversals K --players 3,4,5,6 [--explore-per-street K] [--explore-depth D] [--threads N] --out SAMPLES
//!     nplayer_deep_cfr bench --network NET SHA256 --tables K50 [--seconds S] [--threads N]
//!
//! `traverse` writes one sample file (`NPDCF001`, a JSON header, then fixed-size records in
//! traversal order) and prints a summary. The records never depend on the thread count.
//! `bench` checks the f32 path against the f64 reference on real traversal features, then times
//! both, and times traversals per second.
use hu20_trainer::{
    cards::EquityTables,
    deep_cfr::{self, Counts, Traversal},
    policy_features as features,
    policy_network::{Output, PolicyNetwork},
};
use rayon::prelude::*;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{collections::HashMap, io::Write, path::Path, time::Instant};

const CHUNK: u64 = 2048;

fn args() -> (String, HashMap<String, Vec<String>>) {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let mut map: HashMap<String, Vec<String>> = HashMap::new();
    let mut key = None;
    for s in a.iter().skip(1) {
        if let Some(k) = s.strip_prefix("--") {
            key = Some(k.to_string());
            map.entry(k.to_string()).or_default();
        } else if let Some(k) = &key {
            map.get_mut(k).unwrap().push(s.clone());
        }
    }
    (a.first().cloned().unwrap_or_default(), map)
}

fn one<'a>(m: &'a HashMap<String, Vec<String>>, k: &str) -> Result<&'a str, String> {
    match m.get(k).map(Vec::as_slice) {
        Some([v]) => Ok(v),
        _ => Err(format!("--{k} takes one value")),
    }
}
fn number(m: &HashMap<String, Vec<String>>, k: &str) -> Result<u64, String> {
    one(m, k)?.parse().map_err(|_| format!("--{k} must be a non-negative integer"))
}
fn network(m: &HashMap<String, Vec<String>>, k: &str) -> Result<PolicyNetwork, String> {
    match m.get(k).map(Vec::as_slice) {
        Some([path, sha]) => PolicyNetwork::load(Path::new(path), sha),
        _ => Err(format!("--{k} takes PATH SHA256")),
    }
}
fn threads(m: &HashMap<String, Vec<String>>) -> Result<(), String> {
    if m.contains_key("threads") {
        rayon::ThreadPoolBuilder::new().num_threads(number(m, "threads")? as usize).build_global().map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn traverse(m: &HashMap<String, Vec<String>>) -> Result<(), String> {
    threads(m)?;
    let net = network(m, "advantage")?;
    if net.output != Output::Advantage {
        return Err("--advantage must be an advantage-6 network".into());
    }
    let tables = EquityTables::load(Path::new(one(m, "tables")?), false)?;
    let (seed, iteration, traversals) = (number(m, "seed")?, number(m, "iteration")?, number(m, "traversals")?);
    if iteration == 0 || iteration > u32::MAX as u64 || traversals == 0 {
        return Err("iteration is 1..=u32::MAX and traversals positive".into());
    }
    let players: Vec<usize> = one(m, "players")?.split(',').map(|p| p.parse().map_err(|_| "players: comma list".to_string())).collect::<Result<_, _>>()?;
    deep_cfr::root(seed, iteration, 0, &players)?;
    let limit = |k: &str| -> Result<Option<u32>, String> { if m.contains_key(k) { Ok(Some(number(m, k)? as u32)) } else { Ok(None) } };
    let (per_street, total) = (limit("explore-per-street")?, limit("explore-depth")?);
    let bound = deep_cfr::Bound { per_street: per_street.unwrap_or(u32::MAX), total: total.unwrap_or(u32::MAX) };
    let out = Path::new(one(m, "out")?);
    let fast = net.fast();
    let header = json!({"format":deep_cfr::FORMAT,"features_schema":features::SCHEMA,"layout_sha256":features::layout_sha256(),
        "feature_count":features::len(),"record_bytes":deep_cfr::record_bytes(),"record_layout":deep_cfr::record_layout(),
        "advantage_network":{"sha256":net.sha256,"header":net.header},"card_tables":tables.sha256,
        "seed":seed,"iteration":iteration,"traversals":traversals,"players":players,"stacks":"wide-depth-grid-v1"});
    let mut header = header;
    if bound != deep_cfr::Bound::NONE {
        header["explore_per_street"] = json!(per_street);
        header["explore_depth"] = json!(total);
    }
    let hb = serde_json::to_vec(&header).map_err(|e| e.to_string())?;
    let file = std::fs::OpenOptions::new().write(true).create_new(true).open(out).map_err(|e| format!("{}: {e}", out.display()))?;
    let mut w = std::io::BufWriter::with_capacity(1 << 24, file);
    w.write_all(deep_cfr::MAGIC).and_then(|_| w.write_all(&(hb.len() as u64).to_le_bytes())).and_then(|_| w.write_all(&hb))
        .map_err(|e| e.to_string())?;
    let start = Instant::now();
    let mut counts = Counts::default();
    let mut value = 0.;
    // A writer thread hashes and writes each chunk while the next one is traversed; the bytes and
    // their order are the same as writing them in place.
    let (send, receive) = std::sync::mpsc::sync_channel::<Vec<Vec<u8>>>(1);
    let writer = std::thread::spawn(move || -> Result<String, String> {
        let mut digest = Sha256::new();
        for chunk in receive {
            for bytes in chunk {
                digest.update(&bytes);
                w.write_all(&bytes).map_err(|e| e.to_string())?;
            }
        }
        w.flush().map_err(|e| e.to_string())?;
        Ok(format!("{:x}", digest.finalize()))
    });
    let mut first = 0;
    let traversed = (|| -> Result<(), String> {
        while first < traversals {
            let last = (first + CHUNK).min(traversals);
            let results: Vec<(Vec<u8>, Counts, f64)> = (first..last).into_par_iter().map(|i| {
                let mut t = Traversal::bounded(&fast, tables, iteration as u32, bound);
                let v = t.run(seed, i, &players)?;
                Ok((t.out, t.counts, v))
            }).collect::<Result<_, String>>()?;
            let mut chunk = Vec::with_capacity((last - first) as usize);
            for (bytes, c, v) in results {
                counts.add(&c);
                value += v;
                chunk.push(bytes);
            }
            send.send(chunk).map_err(|_| "the sample writer stopped".to_string())?;
            first = last;
        }
        Ok(())
    })();
    drop(send);
    let written = writer.join().map_err(|_| "the sample writer panicked".to_string())?;
    traversed?;
    let records_sha256 = written?;
    let seconds = start.elapsed().as_secs_f64();
    println!("{}", json!({"out":out,"records_sha256":records_sha256,"traversals":counts.traversals,
        "nodes":counts.nodes,"terminals":counts.terminals,"advantage_samples":counts.advantage,"strategy_samples":counts.strategy,
        "explore_per_street":per_street,"explore_depth":total,"sampled_traverser_decisions":counts.sampled,
        "advantage_by_street":counts.advantage_by_street,"sampled_by_street":counts.sampled_by_street,"max_nodes":counts.max_nodes,"mean_traverser_value_bb":value / traversals as f64,"seconds":seconds,"nodes_per_second":counts.nodes as f64 / seconds}));
    Ok(())
}

fn bench(m: &HashMap<String, Vec<String>>) -> Result<(), String> {
    threads(m)?;
    let net = network(m, "network")?;
    let tables = EquityTables::load(Path::new(one(m, "tables")?), false)?;
    let seconds = m.get("seconds").map(|_| number(m, "seconds")).transpose()?.unwrap_or(10) as f64;
    let fast = net.fast();
    // Real features: the records of a few traversals under a uniform-ish advantage network.
    let mut t = Traversal::new(&fast, tables, 1);
    let mut i = 0;
    while (t.counts.advantage + t.counts.strategy) < 2000 && i < 10_000 {
        // Advantage nets traverse as themselves; a policy net's softmax is fine for collecting inputs.
        t.run(1, i, &[3, 4, 5, 6])?;
        i += 1;
    }
    let r = deep_cfr::record_bytes();
    let inputs: Vec<&[u8]> = t.out.chunks_exact(r).map(|rec| &rec[8 + 4 * features::ACTIONS..]).take(2000).collect();
    let mut scratch = hu20_trainer::policy_network::Scratch::default();
    let mut worst = 0f64;
    for b in &inputs {
        let x: Vec<f32> = b.iter().map(|&v| v as f32 / 255.).collect();
        let reference = net.logits(&x)?;
        let got = fast.logits(b, &mut scratch);
        for a in 0..features::ACTIONS {
            worst = worst.max((reference[a] - got[a] as f64).abs() / (1. + reference[a].abs()));
        }
    }
    let time = |f: &mut dyn FnMut(&[u8])| {
        let start = Instant::now();
        let mut n = 0u64;
        while start.elapsed().as_secs_f64() < seconds / 3. {
            for b in &inputs {
                f(b);
            }
            n += inputs.len() as u64;
        }
        start.elapsed().as_secs_f64() / n as f64
    };
    let reference = time(&mut |b| {
        let x: Vec<f32> = b.iter().map(|&v| v as f32 / 255.).collect();
        std::hint::black_box(net.logits(&x).unwrap());
    });
    let f32_path = time(&mut |b| {
        std::hint::black_box(fast.logits(b, &mut scratch));
    });
    let nonzero = inputs.iter().map(|b| b.iter().filter(|&&v| v != 0).count()).sum::<usize>() as f64 / inputs.len() as f64;
    // Traversal throughput on all threads. A policy network traverses with its own strategy, which
    // gives realistic hand lengths before any advantage network is trained.
    let traversal = {
        let start = Instant::now();
        let mut done = Counts::default();
        let mut next = 0u64;
        while start.elapsed().as_secs_f64() < seconds / 3. {
            let c: Vec<Counts> = (next..next + 64).into_par_iter().map(|k| {
                let mut t = Traversal::new(&fast, tables, 1);
                t.run(2, k, &[3, 4, 5, 6]).map(|_| t.counts)
            }).collect::<Result<_, _>>()?;
            for x in &c {
                done.add(x);
            }
            next += 64;
        }
        let s = start.elapsed().as_secs_f64();
        json!({"traversals_per_second":done.traversals as f64 / s,"nodes_per_second":done.nodes as f64 / s,
               "samples_per_traversal":(done.advantage + done.strategy) as f64 / done.traversals as f64,
               "nodes_per_traversal":done.nodes as f64 / done.traversals as f64,"threads":rayon::current_num_threads()})
    };
    println!("{}", json!({"network":net.sha256,"layers":net.header["layers"],"inputs":inputs.len(),"mean_nonzero_features":nonzero,
        "worst_relative_difference":worst,"reference_seconds_per_forward":reference,"f32_seconds_per_forward":f32_path,
        "speedup":reference / f32_path,"traversal":traversal}));
    if worst > 1e-4 {
        return Err(format!("f32 path differs from the reference by {worst}"));
    }
    Ok(())
}

fn main() {
    let (command, m) = args();
    let result = match command.as_str() {
        "traverse" => traverse(&m),
        "bench" => bench(&m),
        _ => Err("usage: nplayer_deep_cfr traverse|bench ...".into()),
    };
    if let Err(e) = result {
        eprintln!("nplayer_deep_cfr: {e}");
        std::process::exit(2);
    }
}
