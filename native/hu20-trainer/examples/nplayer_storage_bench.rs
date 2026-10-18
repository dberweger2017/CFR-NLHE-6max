//! Fixed-work storage comparison. No trainer or checkpoint implementation changes.
use hu20_trainer::{
    cards::EquityTables, multi_cfr::Game, multi_checkpoint, multi_holdem::CashGame, nplayer::Config,
};
use serde_json::json;
use std::{io::Write, path::Path, time::Instant};

fn emit(value: serde_json::Value) {
    println!("{value}");
    std::io::stdout().flush().unwrap();
}

fn phase(name: &str, target: u64) {
    emit(json!({"event":"phase", "phase":name, "target":target}));
}

fn run() -> Result<(), String> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 6 {
        return Err("TABLES INPUT INPUT_SHA256 NEW_OUTPUT TARGETS_CSV".into());
    }
    let targets: Vec<u64> = args[5]
        .split(',')
        .map(|s| s.parse().map_err(|_| "invalid target".to_string()))
        .collect::<Result<_, _>>()?;
    if targets.is_empty() || targets.windows(2).any(|w| w[0] >= w[1]) {
        return Err("targets must increase".into());
    }
    let input = Path::new(&args[2]);
    let out = Path::new(&args[4]);
    std::fs::create_dir(out).map_err(|e| e.to_string())?;
    let total = Instant::now();
    phase("load", 0);
    let load = Instant::now();
    if hu20_trainer::export::sha256_file(input) != args[3] {
        return Err("input SHA256 mismatch".into());
    }
    let tables = EquityTables::load(Path::new(&args[1]), false)?;
    let game = CashGame {
        config: Config::new(&[2000; 3], 50, 100)?,
        tables,
        key_schema: Default::default(),
    };
    let mut trainer = multi_checkpoint::load(input)?;
    if trainer.identity != game.identity()
        || trainer.players != 3
        || trainer.seed != 2026101541
        || trainer.last_average_street != 3
        || trainer.max_entries != 150_000_000
        || trainer.freeze_at_cap
        || trainer.frozen_at.is_some()
        || targets[0] <= trainer.counts.nodes
    {
        return Err("unexpected checkpoint identity or target".into());
    }
    emit(
        json!({"event":"loaded", "seconds":load.elapsed().as_secs_f64(),
        "nodes":trainer.counts.nodes, "entries":trainer.table.len(),
        "iteration":trainer.iteration, "identity":trainer.identity}),
    );
    for target in targets {
        phase("train", target);
        let from = trainer.counts.nodes;
        let started = Instant::now();
        while trainer.counts.nodes < target {
            if trainer.table.len() >= trainer.max_entries {
                return Err("unexpected entry-cap stop".into());
            }
            trainer.step(&game);
            if trainer.iteration % 10000 == 0 {
                emit(json!({"event":"progress", "target":target,
                    "nodes":trainer.counts.nodes, "entries":trainer.table.len()}));
            }
        }
        let train_seconds = started.elapsed().as_secs_f64();
        emit(
            json!({"event":"trained", "target":target, "from_nodes":from,
            "nodes":trainer.counts.nodes, "entries":trainer.table.len(),
            "iteration":trainer.iteration, "seconds":train_seconds,
            "nodes_per_second":(trainer.counts.nodes-from) as f64/train_seconds}),
        );
        let checkpoint = out.join(format!("{target}.gz"));
        if checkpoint.exists() {
            return Err("checkpoint already exists".into());
        }
        phase("save", target);
        let started = Instant::now();
        multi_checkpoint::save(&trainer, &checkpoint, hu20_trainer::gz::Gzip::Compatible)?;
        let save_seconds = started.elapsed().as_secs_f64();
        let bytes = std::fs::metadata(&checkpoint)
            .map_err(|e| e.to_string())?
            .len();
        emit(
            json!({"event":"saved", "target":target, "seconds":save_seconds,
            "bytes":bytes, "checkpoint":checkpoint}),
        );
        phase("verify", target);
        let started = Instant::now();
        let sha = hu20_trainer::export::sha256_file(&checkpoint);
        emit(json!({"event":"verified", "target":target, "sha256":sha,
            "seconds":started.elapsed().as_secs_f64()}));
    }
    phase("release", 0);
    drop(trainer);
    emit(json!({"event":"complete", "seconds":total.elapsed().as_secs_f64()}));
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(2);
    }
}
