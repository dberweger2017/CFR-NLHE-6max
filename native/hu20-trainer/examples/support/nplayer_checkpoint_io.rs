//! Shared checkpoint/export I/O. Timing callers measure traversal separately.
use hu20_trainer::{
    gz::Gzip,
    multi_cfr::Trainer,
    multi_checkpoint,
    multi_policy::{self, Mode},
};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{io::Write, path::Path, time::Instant};

pub fn emit(value: Value) {
    println!("{value}");
    std::io::stdout().flush().unwrap();
}
pub fn keyset(t: &Trainer) -> String {
    let mut hash = Sha256::new();
    for (key, _) in t.table.sorted() {
        hash.update(key);
    }
    format!("{:x}", hash.finalize())
}
pub fn save(
    t: &Trainer,
    out: &Path,
    label: &str,
    target: u64,
    gzip: Gzip,
    export: bool,
) -> Result<String, String> {
    Ok(save_report(t, out, label, target, gzip, export)?.0)
}
pub fn save_report(
    t: &Trainer,
    out: &Path,
    label: &str,
    target: u64,
    gzip: Gzip,
    export: bool,
) -> Result<(String, String), String> {
    emit(json!({"event":"phase","phase":"save","target":target}));
    let path = out.join(format!("{label}.gz"));
    let tick = Instant::now();
    multi_checkpoint::save(t, &path, gzip)?;
    let seconds = tick.elapsed().as_secs_f64();
    emit(json!({"event":"phase","phase":"hash","target":target}));
    let digest = hu20_trainer::export::sha256_file(&path);
    let keys = keyset(t);
    emit(
        json!({"event":"checkpoint","label":label,"target":target,"nodes":t.counts.nodes,
        "iteration":t.iteration,"entries":t.table.len(),"frozen_at":t.frozen_at,
        "path":path,"sha256":digest,"keyset_sha256":keys,"save_seconds":seconds,
        "bytes":std::fs::metadata(&path).map_err(|e|e.to_string())?.len(),
        "counts":multi_checkpoint::counts_json(&t.counts)}),
    );
    if export {
        emit(json!({"event":"phase","phase":"export","target":target}));
        let output = out.join(format!("{label}-average.gz"));
        let tick = Instant::now();
        multi_policy::write_trainer(t, &digest, Mode::Average, &output, gzip)?;
        let seconds = tick.elapsed().as_secs_f64();
        emit(
            json!({"event":"exported","label":label,"nodes":t.counts.nodes,"entries":t.table.len(),
            "path":output,"sha256":hu20_trainer::export::sha256_file(&output),
            "checkpoint":path,"checkpoint_sha256":digest,"export_seconds":seconds}),
        );
    }
    Ok((keys, digest))
}

#[cfg(test)]
mod tests {
    use super::*;
    use hu20_trainer::{
        multi_cfr::{Prune, Sampling},
        small_games::{Kind, SmallGame},
    };
    #[test]
    fn shared_checkpoint_writer_preserves_the_native_bytes() {
        let game = SmallGame::new(Kind::Kuhn, 3);
        let mut trainer = Trainer {
            sampling: Sampling::Path,
            roots_per_seat: 8,
            prune: Some(Prune { bb: 0.05, after: 1 }),
            ..Trainer::new(&game, 41, 3, 100000, true)
        };
        for _ in 0..10 {
            trainer.step_fast(&game);
        }
        let folder = std::env::temp_dir().join(format!(
            "pruning-io-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&folder).unwrap();
        multi_checkpoint::save(&trainer, &folder.join("reference.gz"), Gzip::Parallel).unwrap();
        let keys = save(
            &trainer,
            &folder,
            "candidate",
            trainer.counts.nodes,
            Gzip::Parallel,
            false,
        )
        .unwrap();
        assert_eq!(keys, keyset(&trainer));
        assert_eq!(
            std::fs::read(folder.join("reference.gz")).unwrap(),
            std::fs::read(folder.join("candidate.gz")).unwrap()
        );
        std::fs::remove_dir_all(folder).unwrap();
    }
}
