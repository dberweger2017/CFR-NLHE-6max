//! One fresh node endpoint, then the remaining traversal clock; never times I/O.
use hu20_trainer::{
    cards::EquityTables,
    gz::Gzip,
    multi_cfr::{Game, Prune, Sampling, Trainer},
    multi_checkpoint,
    multi_holdem::CashGame,
    nplayer::Config,
};
use serde_json::{json, Value};
use std::{path::Path, time::Instant};
#[path = "support/nplayer_checkpoint_io.rs"]
mod checkpoint_io;
use checkpoint_io::{emit, keyset, save_report};

#[derive(Clone, Copy, Debug)]
struct Clock {
    prior: f64,
    segment: f64,
    target: f64,
    last_iteration: f64,
}
impl Clock {
    fn new(prior: f64, target: f64) -> Result<Self, String> {
        if !prior.is_finite()
            || prior < 0.
            || !target.is_finite()
            || target <= 0.
            || prior >= target
        {
            return Err("invalid or exhausted training clock".into());
        }
        Ok(Self {
            prior,
            segment: 0.,
            target,
            last_iteration: 0.,
        })
    }
    fn total(self) -> f64 {
        self.prior + self.segment
    }
    fn reached(self) -> bool {
        self.total() >= self.target
    }
    fn add(&mut self, seconds: f64) {
        self.segment += seconds;
        self.last_iteration = seconds;
    }
}
fn prune(c: &Value) -> Result<Option<Prune>, String> {
    if c["pruning"].is_null() {
        return Ok(None);
    }
    let bb = c["pruning"]["bb"]
        .as_f64()
        .filter(|v| v.is_finite() && *v > 0.)
        .ok_or("invalid pruning bb")?;
    let after = c["pruning"]["after"]
        .as_u64()
        .ok_or("invalid pruning after")?;
    Ok(Some(Prune { bb, after }))
}
fn restored_clock(
    prior: &Value,
    digest: &str,
    nodes: u64,
    iteration: u64,
    pruned: u64,
    target: f64,
    minimum_nodes: u64,
) -> Result<Clock, String> {
    if prior["checkpoint_sha256"] != digest
        || prior["nodes"] != nodes
        || prior["iteration"] != iteration
        || prior["pruned_actions"] != pruned
        || prior["target_seconds"].as_f64() != Some(target)
        || nodes < minimum_nodes
    {
        return Err("clock receipt lineage differs".into());
    }
    Clock::new(
        prior["active_seconds"]
            .as_f64()
            .ok_or("prior active seconds")?,
        target,
    )
}

fn endpoint(t: &Trainer, out: &Path, label: &str, nodes: u64, clock: Clock) -> Result<(), String> {
    let (_, digest) = save_report(t, out, label, nodes, Gzip::Parallel, true)?;
    // Bind cumulative time to immutable trainer bytes. An export/evaluation or
    // process restart never adds time to the active traversal budget.
    let path = out.join(format!("{label}.gz"));
    let receipt = json!({"checkpoint":path,"checkpoint_sha256":digest,
        "active_seconds":clock.total(),"segment_active_seconds":clock.segment,
        "target_seconds":clock.target,"last_iteration_seconds":clock.last_iteration,"nodes":t.counts.nodes,"iteration":t.iteration,
        "pruned_actions":t.counts.pruned});
    let sidecar = out.join(format!("{label}-clock.json"));
    let mut f = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&sidecar)
        .map_err(|e| e.to_string())?;
    use std::io::Write;
    serde_json::to_writer(&mut f, &receipt).map_err(|e| e.to_string())?;
    f.write_all(b"\n").map_err(|e| e.to_string())?;
    f.sync_all().map_err(|e| e.to_string())?;
    emit(
        json!({"event":"endpoint","label":label,"active_seconds":clock.total(),
        "segment_active_seconds":clock.segment,"last_iteration_seconds":clock.last_iteration,"nodes":t.counts.nodes,"iteration":t.iteration,
        "pruned_actions":t.counts.pruned,"clock_path":sidecar,
        "clock_sha256":hu20_trainer::export::sha256_file(&sidecar)}),
    );
    Ok(())
}
fn run(c: &Value) -> Result<(), String> {
    let mode = c["mode"].as_str().ok_or("mode")?;
    if mode != "nodes" && mode != "continue-clock" {
        return Err("unknown training stage".into());
    }
    let seed = c["seed"].as_u64().ok_or("seed")?;
    let threads = c["threads"]
        .as_u64()
        .filter(|v| (1..=16).contains(v))
        .ok_or("threads")?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(threads as usize)
        .build_global()
        .map_err(|e| e.to_string())?;
    let cap = c["max_entries"]
        .as_u64()
        .filter(|v| *v > 0 && *v <= 250_000_000)
        .ok_or("entry ceiling")? as usize;
    let target = c["node_target"]
        .as_u64()
        .filter(|v| *v > 0)
        .ok_or("node target")?;
    let clock_target = c["active_seconds_target"].as_f64().ok_or("clock target")?;
    let expected_prune = prune(c)?;
    let config = Config::new(&[10000; 3], 50, 100)?;
    let table_tick = Instant::now();
    let tables = EquityTables::load(Path::new(c["tables"].as_str().ok_or("tables")?), false)?;
    emit(json!({"event":"tables-loaded","seconds":table_tick.elapsed().as_secs_f64()}));
    let game = CashGame { config, tables };
    let mut clock = Clock::new(0., clock_target)?;
    let mut t = if mode == "nodes" {
        if !c["input"].is_null() || !c["input_sha256"].is_null() || !c["input_clock"].is_null() {
            return Err("node stage must start fresh".into());
        }
        Trainer {
            sampling: Sampling::Path,
            roots_per_seat: 8,
            prune: expected_prune,
            ..Trainer::new(&game, seed, 3, cap, true)
        }
    } else {
        let input = Path::new(c["input"].as_str().ok_or("input")?);
        let digest = hu20_trainer::export::sha256_file(input);
        if Some(digest.as_str()) != c["input_sha256"].as_str() {
            return Err("input SHA mismatch".into());
        }
        let path = Path::new(c["input_clock"].as_str().ok_or("input clock")?);
        if Some(hu20_trainer::export::sha256_file(path).as_str())
            != c["input_clock_sha256"].as_str()
        {
            return Err("clock receipt SHA mismatch".into());
        }
        let prior: Value = serde_json::from_slice(&std::fs::read(path).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
        let load_tick = Instant::now();
        let loaded = multi_checkpoint::load(input)?;
        emit(json!({"event":"checkpoint-loaded","seconds":load_tick.elapsed().as_secs_f64()}));
        clock = restored_clock(
            &prior,
            &digest,
            loaded.counts.nodes,
            loaded.iteration,
            loaded.counts.pruned,
            clock_target,
            target,
        )?;
        loaded
    };
    if t.identity != game.identity()
        || t.seed != seed
        || t.players != 3
        || t.sampling != Sampling::Path
        || t.roots_per_seat != 8
        || t.last_average_street != 3
        || !t.freeze_at_cap
        || t.max_entries != cap
        || t.prune != expected_prune
    {
        return Err("trainer recipe differs".into());
    }
    let out = Path::new(c["out"].as_str().ok_or("out")?);
    std::fs::create_dir(out).map_err(|e| e.to_string())?;
    let stop = Path::new(c["stop_file"].as_str().ok_or("stop file")?);
    let initial_nodes = t.counts.nodes;
    let mut last = Instant::now();
    let mut saved_clock = false;
    let reference_iteration = c["reference_iteration"].as_u64().unwrap_or(212132);
    let mut iteration_landmark = t.iteration >= reference_iteration;
    let mut frozen_keys = t.frozen_at.map(|_| keyset(&t));
    emit(json!({"event":"phase","phase":"train","target":target}));
    while if mode == "nodes" {
        t.counts.nodes < target
    } else {
        !clock.reached()
    } {
        if stop.exists() {
            return Err("owner stop file".into());
        }
        let tick = Instant::now();
        t.step_fast(&game);
        clock.add(tick.elapsed().as_secs_f64());
        if !iteration_landmark && t.iteration >= reference_iteration {
            emit(
                json!({"event":"iteration-landmark","iteration":t.iteration,"nodes":t.counts.nodes,
                "active_seconds":clock.total(),"pruned_actions":t.counts.pruned}),
            );
            iteration_landmark = true;
        }
        if frozen_keys.is_none() && t.frozen_at.is_some() {
            frozen_keys = Some(keyset(&t));
        }
        if mode == "nodes" && clock.reached() && !saved_clock {
            endpoint(&t, out, "clock", target, clock)?;
            saved_clock = true;
            emit(json!({"event":"phase","phase":"train","target":target}));
        }
        if last.elapsed().as_secs_f64() >= 5. {
            emit(
                json!({"event":"progress","nodes":t.counts.nodes,"iteration":t.iteration,
                "entries":t.table.len(),"active_seconds":clock.total(),"segment_active_seconds":clock.segment,
                "pruned_actions":t.counts.pruned,"nodes_per_second":(t.counts.nodes-initial_nodes)as f64/clock.segment}),
            );
            last = Instant::now();
        }
    }
    let label = if mode == "nodes" { "nodes" } else { "clock" };
    endpoint(&t, out, label, target, clock)?;
    if frozen_keys.is_some_and(|expected| expected != keyset(&t)) {
        return Err("frozen membership changed".into());
    }
    emit(
        json!({"event":"complete","nodes":t.counts.nodes,"iteration":t.iteration,
        "active_seconds":clock.total(),"segment_active_seconds":clock.segment,
        "pruned_actions":t.counts.pruned,"clock_already_saved":saved_clock}),
    );
    Ok(())
}
fn main() {
    let result = (|| {
        let path = std::env::args().nth(1).ok_or("CONFIG.json")?;
        let c: Value = serde_json::from_slice(&std::fs::read(path).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
        run(&c)
    })();
    if let Err(e) = result {
        eprintln!("nplayer_pruning_study: {e}");
        std::process::exit(2);
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn resumed_clock_counts_only_new_traversal_and_never_restarts() {
        let mut clock = Clock::new(400., 630.740595090997).unwrap();
        clock.add(200.);
        assert!(!clock.reached());
        clock.add(30.75);
        assert!(clock.reached());
        assert_eq!(clock.segment, 230.75);
        assert_eq!(clock.total(), 630.75);
        assert!(Clock::new(clock.total(), clock.target).is_err());
        for value in [-1., f64::NAN, f64::INFINITY] {
            assert!(Clock::new(value, 630.).is_err());
        }
    }
    #[test]
    fn pruning_is_explicit_and_invalid_settings_fail() {
        assert_eq!(prune(&json!({})).unwrap(), None);
        assert_eq!(
            prune(&json!({"pruning":{"bb":0.05,"after":200}})).unwrap(),
            Some(Prune {
                bb: 0.05,
                after: 200
            })
        );
        assert!(prune(&json!({"pruning":{"bb":0.,"after":200}})).is_err());
        assert!(prune(&json!({"pruning":{"bb":0.05}})).is_err());
    }
    #[test]
    fn clock_receipt_is_bound_to_the_restored_checkpoint_and_budget() {
        let prior = json!({"checkpoint_sha256":"pinned", "nodes":3001,"iteration":212,
            "pruned_actions":17,"target_seconds":10.,"active_seconds":4.});
        let mut clock = restored_clock(&prior, "pinned", 3001, 212, 17, 10., 3000).unwrap();
        clock.add(6.);
        assert!(clock.reached());
        assert_eq!(clock.total(), 10.);
        for (field, bad) in [
            ("checkpoint_sha256", json!("wrong")),
            ("nodes", json!(3000)),
            ("iteration", json!(213)),
            ("pruned_actions", json!(18)),
            ("target_seconds", json!(11.)),
            ("active_seconds", json!(10.)),
        ] {
            let mut changed = prior.clone();
            changed[field] = bad;
            assert!(restored_clock(&changed, "pinned", 3001, 212, 17, 10., 3000).is_err());
        }
    }
}
