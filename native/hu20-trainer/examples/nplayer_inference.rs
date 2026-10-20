//! Explicit conversion, complete row audit and load profiling. Never launches training.
use hu20_trainer::{multi_binary, multi_policy::PolicyTable};
use serde_json::json;
use std::path::Path;

fn mass_arg<'a>(a: &'a [String], flag: usize) -> Option<(&'a Path, &'a str)> {
    (a.len() == flag + 3).then(|| (Path::new(&a[flag + 1]), a[flag + 2].as_str()))
}
fn probe(a: &[String]) -> Result<serde_json::Value, String> {
    let (table, load) = PolicyTable::load_profiled(Path::new(&a[2]), &a[3], false)?;
    let text = std::fs::read(&a[4]).map_err(|e| e.to_string())?;
    let keys: Vec<String> = serde_json::from_slice(&text).map_err(|e| e.to_string())?;
    let rounds: u64 = a[5].parse().map_err(|_| "invalid rounds")?;
    if keys.is_empty() || keys.len() > 65536 || !(1..=10000).contains(&rounds) {
        return Err("probe bound".into());
    }
    let keys = keys
        .into_iter()
        .map(|s| {
            if s.len() != 32 || !s.is_ascii() {
                return Err("invalid probe key".to_string());
            }
            let mut key = [0; 16];
            for (i, k) in key.iter_mut().enumerate() {
                *k = u8::from_str_radix(&s[2 * i..2 * i + 2], 16).map_err(|e| e.to_string())?;
            }
            Ok(key)
        })
        .collect::<Result<Vec<_>, String>>()?;
    use sha2::{Digest, Sha256};
    let started = std::time::Instant::now();
    let mut hash = Sha256::new();
    let mut found = 0u64;
    for _ in 0..rounds {
        for key in &keys {
            if let Some(row) = table.rows.get(key) {
                found += 1;
                hash.update([row.owner, row.street]);
                hash.update(row.code.to_le_bytes());
                for p in row.probabilities {
                    hash.update(p.to_bits().to_le_bytes());
                }
            } else {
                hash.update(b"missing");
            }
        }
    }
    Ok(
        json!({"status":"passed","rows":table.rows.len(),"format":load.format,
        "load_seconds":load.total_seconds,"probe_seconds":started.elapsed().as_secs_f64(),
        "probes":rounds*keys.len() as u64,"found":found,"probe_sha256":format!("{:x}",hash.finalize())}),
    )
}
fn run() -> Result<(), String> {
    let a: Vec<String> = std::env::args().collect();
    let result = match a.get(1).map(String::as_str) {
        Some("convert") if a.len() == 5 || (a.len() == 8 && a[5] == "--mass") => {
            multi_binary::convert(Path::new(&a[2]), &a[3], Path::new(&a[4]), mass_arg(&a, 5))?
        }
        Some("verify") if a.len() == 6 || (a.len() == 9 && a[6] == "--mass") => {
            multi_binary::verify(
                Path::new(&a[2]),
                &a[3],
                Path::new(&a[4]),
                &a[5],
                mass_arg(&a, 6),
            )?
        }
        Some("load") if a.len() == 4 || (a.len() == 5 && a[4] == "--profile") => {
            let (table, r) = PolicyTable::load_profiled(Path::new(&a[2]), &a[3], a.len() == 5)?;
            json!({"status":"passed","format":r.format,"rows":r.rows,"total_seconds":r.total_seconds,
                "verify_file_seconds":r.verify_seconds,"stream_decode_seconds":r.stream_seconds,
                "parse_validate_allocate_seconds":r.parse_validate_seconds,"index_insert_seconds":r.insert_seconds,
                "fine_profile":a.len()==5,"identity":table.identity,"strategy":table.mode.name(),"average_scope":table.scope,
                "source_checkpoint_sha256":table.source_checkpoint_sha256,"binary_source_policy_sha256":table.binary_source_policy_sha256})
        }
        Some("probe") if a.len() == 6 => probe(&a)?,
        Some("first-action") if a.len() == 5 => {
            let started = std::time::Instant::now();
            let (table, load) = PolicyTable::load_profiled(Path::new(&a[3]), &a[4], false)?;
            let tables = hu20_trainer::cards::EquityTables::load(Path::new(&a[2]), false)?;
            let hand = hu20_trainer::nplayer::Hand::from_deck(
                table.config(),
                0,
                &(0..52).collect::<Vec<_>>(),
            )?;
            let observation = hand.observe(hand.actor().ok_or("no first actor")?)?;
            let mut policy =
                hu20_trainer::multi_policy::Policy::new(std::sync::Arc::new(table), 20261020359);
            let action = policy.choose(&observation, tables)?;
            let seconds = started.elapsed().as_secs_f64();
            json!({"status":"passed","format":load.format,"policy_load_seconds":load.total_seconds,
                "first_action_seconds":seconds,"action":[action.kind.name(),action.raise_to],
                "misses":policy.misses,"fixture":"fixed deck 0..51, button0, action seed20261020359"})
        }
        _ => {
            return Err(concat!(
                "convert SOURCE SHA NEW_BINARY [--mass RECEIPT SHA] | ",
                "verify SOURCE SHA BINARY SHA [--mass RECEIPT SHA] | ",
                "load POLICY SHA [--profile] | probe POLICY SHA KEYS_JSON ROUNDS | ",
                "first-action K50 POLICY SHA"
            )
            .into())
        }
    };
    println!("{result}");
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("nplayer_inference: {e}");
        std::process::exit(2);
    }
}
