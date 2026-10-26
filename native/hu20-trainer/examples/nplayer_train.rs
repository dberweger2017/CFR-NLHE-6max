//! Explicit experimental entry point; legacy HU commands/formats are unchanged.
use hu20_trainer::{
    cards::EquityTables,
    multi_cfr::{Game, Sampling, Trainer},
    multi_checkpoint,
    multi_holdem::{CashGame, KeySchema},
    nplayer::Config,
};
use serde_json::json;
use std::{
    collections::BTreeMap,
    io::Write,
    path::{Path, PathBuf},
};

fn train() -> Result<(), String> {
    let mut options = BTreeMap::new();
    let mut args = std::env::args().skip(1);
    let mut freeze = false;
    let mut gzip = None;
    let mut fast = false;
    let mut admission = false;
    while let Some(key) = args.next() {
        if key == "--traverser-admission" {
            if admission {
                return Err("duplicate --traverser-admission".into());
            }
            admission = true;
            continue;
        }
        if key == "--fast" {
            if fast {
                return Err("duplicate --fast".into());
            }
            fast = true;
            continue;
        }
        if key == "--freeze-at-cap" {
            if freeze {
                return Err("duplicate --freeze-at-cap".into());
            }
            freeze = true;
            continue;
        }
        if key == "--fast-gzip" {
            if gzip.replace(hu20_trainer::gz::Gzip::Parallel).is_some() {
                return Err("duplicate --fast-gzip".into());
            }
            continue;
        }
        if ![
            "--players",
            "--stack-bb",
            "--stacks",
            "--small-blind",
            "--big-blind",
            "--menu",
            "--card-buckets",
            "--seed",
            "--nodes",
            "--last-average-street",
            "--max-entries",
            "--max-seconds",
            "--out",
            "--resume",
            "--resume-sha256",
            "--telemetry",
            "--stop-file",
            "--threads",
            "--roots-per-seat",
            "--prune-bb",
            "--prune-after",
            "--opponent-pot-raise",
            "--key-schema",
        ]
        .contains(&key.as_str())
        {
            return Err(format!("unknown option {key}"));
        }
        let value = args
            .next()
            .ok_or_else(|| format!("missing value for {key}"))?;
        if options.insert(key.clone(), value).is_some() {
            return Err(format!("duplicate {key}"));
        }
    }
    let required = |key: &str| {
        options
            .get(key)
            .map(String::as_str)
            .ok_or_else(|| format!("missing {key}"))
    };
    let unsigned = |key: &str, default: &str| {
        options
            .get(key)
            .map(String::as_str)
            .unwrap_or(default)
            .parse::<u64>()
            .map_err(|_| format!("invalid {key}"))
    };
    let players = required("--players")?
        .parse::<usize>()
        .map_err(|_| "invalid --players")?;
    if !(2..=6).contains(&players) {
        return Err("--players must be 2..6".into());
    }
    let sb = unsigned("--small-blind", "50")?;
    let bb = unsigned("--big-blind", "100")?;
    if options.contains_key("--stacks") && options.contains_key("--stack-bb") {
        return Err("choose --stacks or --stack-bb".into());
    }
    let stacks = if let Some(stacks) = options.get("--stacks") {
        stacks
            .split(',')
            .map(|s| s.parse::<u64>().map_err(|_| "invalid --stacks".to_string()))
            .collect::<Result<Vec<_>, _>>()?
    } else {
        vec![
            bb.checked_mul(unsigned("--stack-bb", "20")?)
                .ok_or("stack overflow")?;
            players
        ]
    };
    if stacks.len() != players {
        return Err("--stacks count differs from --players".into());
    }
    let config = Config::new(&stacks, sb, bb)?;
    if options.get("--menu").is_some_and(|m| m != "v1") {
        return Err("this phase supports --menu v1 only".into());
    }
    let nodes = required("--nodes")?
        .parse::<u64>()
        .map_err(|_| "invalid --nodes")?;
    let max_entries = required("--max-entries")?
        .parse::<usize>()
        .map_err(|_| "invalid --max-entries")?;
    let seconds = required("--max-seconds")?
        .parse::<f64>()
        .map_err(|_| "invalid --max-seconds")?;
    let scope = unsigned("--last-average-street", "3")? as usize;
    if nodes == 0 || max_entries == 0 || !seconds.is_finite() || seconds <= 0. || scope > 3 {
        return Err("invalid node, entry, time or averaging bound".into());
    }
    let seed = unsigned("--seed", "1")?;
    let out = PathBuf::from(required("--out")?);
    if out.exists() {
        return Err("output already exists; choose a fresh path".into());
    }
    if options.contains_key("--resume") != options.contains_key("--resume-sha256") {
        return Err("resume needs both --resume and --resume-sha256".into());
    }
    if let Some(threads) = options.get("--threads") {
        let threads = threads.parse::<usize>().ok().filter(|&n| n > 0).ok_or("invalid --threads")?;
        rayon::ThreadPoolBuilder::new().num_threads(threads).build_global().map_err(|e| e.to_string())?;
    }
    let sampling = if fast { Sampling::Path } else { Sampling::Stream };
    let roots_per_seat = match options.get("--roots-per-seat") {
        None if fast => 8,
        None => 1,
        Some(_) if !fast => return Err("--roots-per-seat needs --fast".into()),
        Some(r) => r.parse::<usize>().ok().filter(|r| (1..=1024).contains(r)).ok_or("invalid --roots-per-seat")?,
    };
    let prune = match (options.get("--prune-bb"), options.get("--prune-after")) {
        (None, None) => None,
        (Some(_), Some(_)) if !fast => return Err("pruning needs --fast".into()),
        (Some(bb), Some(after)) => Some(hu20_trainer::multi_cfr::Prune {
            bb: bb.parse::<f64>().ok().filter(|b| b.is_finite() && *b > 0.).ok_or("invalid --prune-bb")?,
            after: after.parse::<u64>().map_err(|_| "invalid --prune-after")?,
        }),
        _ => return Err("--prune-bb and --prune-after go together".into()),
    };
    let pressure = match options.get("--opponent-pot-raise") {
        None => None,
        Some(_) if !fast => return Err("--opponent-pot-raise needs --fast".into()),
        Some(p) => Some(p.parse::<f64>().ok().filter(|p| *p > 0. && *p <= 1.).ok_or("invalid --opponent-pot-raise")?),
    };
    if admission && !fast {
        return Err("--traverser-admission needs --fast".into());
    }
    let tables = EquityTables::load(Path::new(required("--card-buckets")?), false)?;
    let schema = KeySchema::parse(options.get("--key-schema").map(String::as_str).unwrap_or("history"))?;
    let game = CashGame { config, tables, schema };
    let mut trainer = if let Some(path) = options.get("--resume") {
        let path = Path::new(path);
        let expected = required("--resume-sha256")?;
        if expected.len() != 64 || hu20_trainer::export::sha256_file(path) != expected {
            return Err("resume SHA256 mismatch".into());
        }
        let t = multi_checkpoint::load(path)?;
        if t.identity != game.identity()
            || t.players != players
            || t.seed != seed
            || t.last_average_street != scope
            || t.max_entries != max_entries
            || t.freeze_at_cap != freeze
            || t.sampling != sampling
            || t.roots_per_seat != roots_per_seat
            || t.prune != prune
            || t.pressure != pressure
            || t.traverser_admission != admission
        {
            return Err("resume configuration mismatch".into());
        }
        t
    } else {
        Trainer { sampling, roots_per_seat, prune, pressure, traverser_admission: admission, ..Trainer::new(&game, seed, scope, max_entries, freeze) }
    };
    if let Some(parent) = out.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
    }
    let mut telemetry = if let Some(path) = options.get("--telemetry") {
        Some(
            std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(path)
                .map_err(|e| e.to_string())?,
        )
    } else {
        None
    };
    let start = std::time::Instant::now();
    let reason = loop {
        if trainer.counts.nodes >= nodes {
            break "nodes";
        }
        if !freeze && trainer.table.len() >= max_entries {
            break "capacity";
        }
        if start.elapsed().as_secs_f64() >= seconds {
            break "time";
        }
        if options
            .get("--stop-file")
            .is_some_and(|p| Path::new(p).exists())
        {
            break "stop-file";
        }
        if fast {
            trainer.step_fast(&game);
        } else {
            trainer.step(&game);
        }
        if trainer.iteration % 100 == 0 {
            if let Some(file) = telemetry.as_mut() {
                let mut line = json!({"iteration":trainer.iteration,"entries":trainer.table.len(),
                "frozen_at":trainer.frozen_at,"elapsed_seconds":start.elapsed().as_secs_f64(),"counts":multi_checkpoint::counts_json(&trainer.counts)});
                if admission {
                    line["declined_keys"] = json!(trainer.counts.declined);
                }
                writeln!(file, "{line}").map_err(|e| e.to_string())?;
            }
        }
    };
    let save_start = std::time::Instant::now();
    multi_checkpoint::save(&trainer, &out, gzip.unwrap_or_default())?;
    let report = json!({"identity":game.identity(),"stop_reason":reason,"iteration":trainer.iteration,
        "save_seconds":save_start.elapsed().as_secs_f64(),
        "entries":trainer.table.len(),"frozen_at":trainer.frozen_at,"counts":multi_checkpoint::counts_json(&trainer.counts),
        "elapsed_seconds":start.elapsed().as_secs_f64(),"checkpoint":out,
        "sha256":hu20_trainer::export::sha256_file(&out)});
    if let Some(file) = telemetry.as_mut() {
        writeln!(file, "{report}").map_err(|e| e.to_string())?;
    }
    println!("{report}");
    if reason == "capacity" {
        std::process::exit(3);
    }
    Ok(())
}
fn main() {
    if let Err(error) = train() {
        eprintln!("nplayer_train: {error}");
        std::process::exit(2);
    }
}
