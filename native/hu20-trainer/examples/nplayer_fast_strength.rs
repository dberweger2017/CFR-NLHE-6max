//! Fixed node/time endpoints for the PR335 study; the trainer remains unchanged.
use hu20_trainer::{
    cards::EquityTables,
    multi_cfr::{Sampling, Trainer},
    multi_checkpoint,
    multi_holdem::CashGame,
    nplayer::Config,
};
use serde_json::json;
use std::{io::Write, path::Path, time::Instant};

fn emit(v: serde_json::Value) {
    println!("{v}");
    std::io::stdout().flush().unwrap();
}
fn phase(name: &str) {
    emit(json!({"event":"phase","phase":name,"target":0}));
}
fn run() -> Result<(), String> {
    let a: Vec<String> = std::env::args().collect();
    if a.len() != 8 {
        return Err(
            "TABLES NEW_OUTPUT SEED production|fast THREADS NODE_TARGET TRAIN_SECONDS".into(),
        );
    }
    let seed: u64 = a[3].parse().map_err(|_| "invalid seed")?;
    let fast = match a[4].as_str() {
        "production" => false,
        "fast" => true,
        _ => return Err("invalid recipe".into()),
    };
    let threads: usize = a[5].parse().map_err(|_| "invalid threads")?;
    let nodes: u64 = a[6].parse().map_err(|_| "invalid nodes")?;
    let seconds: f64 = a[7].parse().map_err(|_| "invalid seconds")?;
    if threads == 0 || threads > 16 || nodes == 0 || !seconds.is_finite() || seconds <= 0. {
        return Err("invalid endpoint".into());
    }
    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global()
        .map_err(|e| e.to_string())?;
    let out = Path::new(&a[2]);
    std::fs::create_dir(out).map_err(|e| e.to_string())?;
    phase("load");
    let load = Instant::now();
    let game = CashGame {
        config: Config::new(&[2000; 3], 50, 100)?,
        tables: EquityTables::load(Path::new(&a[1]), false)?,
    };
    let mut trainer = Trainer::new(&game, seed, 3, 150_000_000, false);
    if fast {
        trainer.sampling = Sampling::Path;
        trainer.roots_per_seat = 8;
    }
    emit(
        json!({"event":"loaded","seconds":load.elapsed().as_secs_f64(),"seed":seed,"fast":fast,"threads":threads}),
    );
    let mut training = 0.;
    let (mut node_done, mut clock_done) = (!fast, false);
    while !node_done || !clock_done {
        phase("train");
        let started = Instant::now();
        loop {
            if trainer.table.len() >= trainer.max_entries {
                return Err("entry-cap stop".into());
            }
            if fast {
                trainer.step_fast(&game);
            } else {
                trainer.step(&game);
            }
            if trainer.table.len() >= trainer.max_entries {
                return Err("entry-cap stop".into());
            }
            let elapsed = training + started.elapsed().as_secs_f64();
            if trainer.iteration % 10000 == 0 {
                emit(
                    json!({"event":"progress","nodes":trainer.counts.nodes,"entries":trainer.table.len(),"training_seconds":elapsed}),
                );
            }
            if (!node_done && trainer.counts.nodes >= nodes) || (!clock_done && elapsed >= seconds)
            {
                break;
            }
        }
        training += started.elapsed().as_secs_f64();
        let due = [
            ("nodes", !node_done && trainer.counts.nodes >= nodes),
            ("clock", !clock_done && training >= seconds),
        ];
        for (label, ready) in due {
            if !ready {
                continue;
            }
            let path = out.join(format!("{label}.gz"));
            emit(
                json!({"event":"endpoint","label":label,"training_seconds":training,
                "nodes":trainer.counts.nodes,"entries":trainer.table.len(),"iteration":trainer.iteration}),
            );
            phase("save");
            let tick = Instant::now();
            multi_checkpoint::save(&trainer, &path, hu20_trainer::gz::Gzip::Compatible)?;
            let save = tick.elapsed().as_secs_f64();
            phase("verify");
            emit(
                json!({"event":"checkpoint","label":label,"checkpoint":path,"training_seconds":training,
                "save_seconds":save,"sha256":hu20_trainer::export::sha256_file(&path),
                "bytes":std::fs::metadata(&path).map_err(|e|e.to_string())?.len(),
                "nodes":trainer.counts.nodes,"entries":trainer.table.len(),"iteration":trainer.iteration}),
            );
            if label == "nodes" {
                node_done = true;
            } else {
                clock_done = true;
            }
        }
    }
    phase("release");
    drop(trainer);
    emit(json!({"event":"complete","training_seconds":training}));
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(2);
    }
}
