//! Frozen-policy qualification only; see docs/deep-cfr-variance-qualification.md.
use hu20_trainer::{
    cards::EquityTables,
    policy_network::PolicyNetwork,
    variance_probe::{self as probe, Critic, Sampler},
};
use rand::{rngs::StdRng, Rng, SeedableRng};
use serde_json::json;
use std::{collections::HashMap, io::Write, path::Path, time::Instant};

fn run() -> Result<(), String> {
    let start = Instant::now();
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() % 2 != 0 {
        return Err("expected --name value pairs".into());
    }
    let m: HashMap<&str, &str> = args
        .chunks(2)
        .map(|c| (c[0].as_str(), c[1].as_str()))
        .collect();
    let get = |k| m.get(k).copied().ok_or_else(|| format!("missing {k}"));
    let mode = get("--mode")?;
    if !["collect", "qualify", "evaluate"].contains(&mode) {
        return Err("mode must be collect, qualify or evaluate".into());
    }
    let out = Path::new(get("--out")?);
    std::fs::create_dir_all(out).map_err(|e| e.to_string())?;
    let net = PolicyNetwork::load(Path::new(get("--network")?), get("--sha")?)?;
    let tables = EquityTables::load(Path::new(get("--tables")?), false)?;
    let fast = net.fast();
    let mut s = Sampler::new(&fast, tables, None);
    let train = mode == "collect";
    let seed = if train {
        20261110850001
    } else {
        20261110850002
    };
    let roots = probe::roots(&mut s, seed, 4)?;
    let startup = start.elapsed().as_secs_f64();
    let critic = if let Some(p) = m.get("--critic") {
        Some(Critic::load(Path::new(p))?)
    } else {
        None
    };
    let samples: usize = m
        .get("--samples")
        .unwrap_or(&"64")
        .parse()
        .map_err(|_| "samples")?;
    if samples == 0 {
        return Err("zero samples".into());
    }
    let mut rows = 0u64;
    let mut nodes = 0u64;
    let begin = Instant::now();
    if mode == "qualify" {
        let zero = Critic::zero();
        for (i, r) in roots.iter().enumerate() {
            for repeat in 0..2 {
                let seed = 20261110850005 + i as u64 * 13 + repeat;
                let mut plain = Sampler::new(&fast, tables, None);
                let mut corrected = Sampler::new(&fast, tables, Some(&zero));
                let a = plain.advantages(&r.hand, seed)?;
                let b = corrected.advantages(&r.hand, seed)?;
                if a != b || plain.nodes != corrected.nodes {
                    return Err("zero-baseline parity failed".into());
                }
                let c = plain.advantages(&r.hand, seed)?;
                if a != c {
                    return Err("deterministic reproduction failed".into());
                }
                rows += 1;
                nodes += plain.nodes + corrected.nodes;
            }
        }
        if let Some(path) = m.get("--parity") {
            let c = critic.as_ref().ok_or("parity requires critic")?;
            let j: serde_json::Value =
                serde_json::from_slice(&std::fs::read(path).map_err(|e| e.to_string())?)
                    .map_err(|e| e.to_string())?;
            let xs = j["features"].as_array().ok_or("parity features")?;
            let ys = j["values"].as_array().ok_or("parity values")?;
            if xs.len() != 32 || ys.len() != xs.len() {
                return Err("parity shape".into());
            }
            let mut max_error = 0f64;
            for (x, y) in xs.iter().zip(ys) {
                let x: Vec<u8> = x
                    .as_array()
                    .ok_or("parity row")?
                    .iter()
                    .map(|v| {
                        v.as_u64()
                            .filter(|&x| x <= 255)
                            .map(|v| v as u8)
                            .ok_or("parity byte")
                    })
                    .collect::<Result<_, _>>()?;
                let y = y.as_array().ok_or("parity target")?;
                if x.len() != probe::INPUTS || y.len() != 6 {
                    return Err("parity width".into());
                }
                for (a, b) in c.predict(&x).iter().zip(y) {
                    let b = b.as_f64().ok_or("parity number")?;
                    let error = (a - b).abs();
                    max_error = max_error.max(error);
                    if error > 0.005 + 1e-5 * b.abs() {
                        return Err(format!("critic parity {error}"));
                    }
                }
            }
            std::fs::write(
                out.join("parity-result.json"),
                json!({"rows":32,"max_absolute_bb":max_error}).to_string(),
            )
            .map_err(|e| e.to_string())?;
        }
    } else if train {
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(out.join("train.bin"))
            .map_err(|e| e.to_string())?;
        let mut w = std::io::BufWriter::new(file);
        for i in 0..samples {
            let r = &roots[i % roots.len()];
            let mut h = r.hand.clone();
            let mut rng = StdRng::seed_from_u64(seed.wrapping_add(i as u64 * 7919));
            let mut rec = Vec::new();
            let focal = h.actor().unwrap();
            let choices = hu20_trainer::multi_holdem::menu(&h.observe(focal)?);
            let action = choices[rng.gen_range(0..choices.len())].1;
            h.apply_mut(action)?;
            let y = s.rollout(&mut h, focal, &mut rng, &mut rec)?;
            for (x, a) in rec {
                w.write_all(&x)
                    .and_then(|_| w.write_all(&[a as u8]))
                    .and_then(|_| w.write_all(&(y as f32).to_le_bytes()))
                    .map_err(|e| e.to_string())?;
                rows += 1;
            }
        }
        w.flush().map_err(|e| e.to_string())?;
        nodes = s.nodes;
    } else {
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(out.join("estimates.jsonl"))
            .map_err(|e| e.to_string())?;
        let mut w = std::io::BufWriter::new(file);
        for batch in 0..2 {
            for (index, r) in roots.iter().enumerate() {
                for rep in 0..samples {
                    let seed = seed.wrapping_add((batch * 1_000_000 + index * 1000 + rep) as u64);
                    let mut results = Vec::new();
                    for offset in 0..2 {
                        let arm = (offset + index + batch) % 2;
                        let c = if arm == 1 { critic.as_ref() } else { None };
                        let mut sampler = Sampler::new(&fast, tables, c);
                        let t = Instant::now();
                        let (v, mask) = sampler.advantages(&r.hand, seed)?;
                        let seconds = t.elapsed().as_secs_f64();
                        nodes += sampler.nodes;
                        results.push(
                            json!({"arm":arm,"advantages":v,"legal":mask,"seconds":seconds,
                        "nodes":sampler.nodes,"baseline_calls":sampler.calls}),
                        );
                    }
                    writeln!(
                        w,
                        "{}",
                        json!({"root":r.id,"batch":batch,"repeat":rep,"seed":seed,"arms":results})
                    )
                    .map_err(|e| e.to_string())?;
                    rows += 1;
                }
            }
        }
        w.flush().map_err(|e| e.to_string())?;
        if let Some(c) = critic.as_ref() {
            let root = &roots[0];
            let x = probe::critic_features(&root.hand, root.hand.actor().unwrap(), tables)?;
            std::fs::write(
                out.join("critic-parity.json"),
                json!({"features":x,"values":c.predict(&x)}).to_string(),
            )
            .map_err(|e| e.to_string())?;
        }
    }
    let summary = json!({"mode":mode,"network_sha256":net.sha256,"tables_sha256":tables.sha256,
        "policy_layout":hu20_trainer::policy_features::layout_sha256(),"seed":seed,"samples":samples,
        "roots":roots.iter().map(probe::root_receipt).collect::<Vec<_>>(),"rows":rows,"nodes":nodes,
        "startup_seconds":startup,"work_seconds":begin.elapsed().as_secs_f64(),"wall_seconds":start.elapsed().as_secs_f64()});
    std::fs::write(
        out.join("summary.json"),
        serde_json::to_vec_pretty(&summary).unwrap(),
    )
    .map_err(|e| e.to_string())?;
    println!("{summary}");
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("variance probe: {e}");
        std::process::exit(1);
    }
}
