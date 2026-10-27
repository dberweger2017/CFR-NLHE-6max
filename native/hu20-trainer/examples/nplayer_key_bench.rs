//! Fixed-work key comparison. Auditing is a separate, deliberately untimed path.
use hu20_trainer::{
    cards::EquityTables,
    cfr::{Key, KeyHasher},
    gz::Gzip,
    multi_cfr::{Decision, Game, Sampling, State, Trainer},
    multi_checkpoint,
    multi_holdem::{observation_key_variants, CashGame, CashState, KeySchema},
    nplayer::{Config, Saved},
};
use rand::rngs::StdRng;
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    hash::BuildHasherDefault,
    io::{BufWriter, Write},
    path::Path,
    sync::{Arc, Mutex},
    time::Instant,
};

type Map = HashMap<Key, Key, BuildHasherDefault<KeyHasher>>;
type Forward = HashMap<Key, [Key; 2], BuildHasherDefault<KeyHasher>>;
const SHARDS: usize = 128;
struct Audit {
    forward: Vec<Mutex<Forward>>,
    reverse: [Vec<Mutex<Map>>; 2],
}
impl Audit {
    fn new() -> Self {
        Self {
            forward: (0..SHARDS)
                .map(|_| Mutex::new(Forward::default()))
                .collect(),
            reverse: std::array::from_fn(|_| {
                (0..SHARDS).map(|_| Mutex::new(Map::default())).collect()
            }),
        }
    }
    fn record(&self, d: [Decision; 3]) {
        let old = d[0].key;
        let pair = [d[1].key, d[2].key];
        let fresh = {
            use std::collections::hash_map::Entry;
            let mut map = self.forward[old[0] as usize % SHARDS].lock().unwrap();
            match map.entry(old) {
                Entry::Occupied(entry) => {
                    assert_eq!(*entry.get(), pair, "one old key has two new keys");
                    false
                }
                Entry::Vacant(entry) => {
                    entry.insert(pair);
                    true
                }
            }
        };
        // Most visits repeat existing states. Reverse collision checks are needed
        // once per new old key; this keeps the untimed full audit inexpensive.
        if fresh {
            for (i, key) in pair.into_iter().enumerate() {
                let mut map = self.reverse[i][key[0] as usize % SHARDS].lock().unwrap();
                assert_eq!(
                    *map.entry(key).or_insert(old),
                    old,
                    "two old keys share a new key"
                );
            }
        }
        for other in &d[1..] {
            assert_eq!(
                (d[0].owner, d[0].street, d[0].code),
                (other.owner, other.street, other.code)
            );
        }
    }
    fn legacy(&self, key: Key, schema: KeySchema) -> Key {
        let index = match schema {
            KeySchema::History => return key,
            KeySchema::CompactBlake => 0,
            KeySchema::CompactXxh3 => 1,
            KeySchema::LiveOrder | KeySchema::StackOwner | KeySchema::StackBuckets => panic!("coarse keys are not exact-history encodings"),
        };
        *self.reverse[index][key[0] as usize % SHARDS]
            .lock()
            .unwrap()
            .get(&key)
            .expect("unobserved candidate key")
    }
    fn write(&self, path: &Path) -> Result<Value, String> {
        let mut out = BufWriter::new(
            std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(path)
                .map_err(|e| e.to_string())?,
        );
        out.write_all(b"NPKEYMAP2\n").map_err(|e| e.to_string())?;
        let mut rows = 0u64;
        for shard in &self.forward {
            for (old, pair) in shard.lock().unwrap().iter() {
                out.write_all(old)
                    .and_then(|_| out.write_all(&pair[0]))
                    .and_then(|_| out.write_all(&pair[1]))
                    .map_err(|e| e.to_string())?;
                rows += 1;
            }
        }
        out.flush()
            .and_then(|_| out.get_ref().sync_all())
            .map_err(|e| e.to_string())?;
        Ok(json!({"rows":rows,"path":path,"sha256":hu20_trainer::export::sha256_file(path)}))
    }
}
struct AuditGame {
    inner: CashGame,
    audit: Arc<Audit>,
}
#[derive(Clone)]
struct AuditState {
    inner: CashState,
    audit: Arc<Audit>,
    tables: &'static EquityTables,
}
impl Game for AuditGame {
    type State = AuditState;
    fn players(&self) -> usize {
        self.inner.players()
    }
    fn identity(&self) -> Value {
        self.inner.identity()
    }
    fn sample(&self, rng: &mut StdRng) -> AuditState {
        AuditState {
            inner: self.inner.sample(rng),
            audit: self.audit.clone(),
            tables: self.inner.tables,
        }
    }
}
impl State for AuditState {
    type Saved = Saved;
    fn players(&self) -> usize {
        self.inner.players()
    }
    fn decision(&self) -> Option<Decision> {
        let actor = self.inner.hand.actor()?;
        let observation = self.inner.hand.observe(actor).unwrap();
        let d = observation_key_variants(&observation, self.tables);
        self.audit.record(d);
        Some(d[0])
    }
    fn payoff(&self, player: usize) -> f64 {
        self.inner.payoff(player)
    }
    fn save(&self) -> Saved {
        self.inner.save()
    }
    fn restore(&mut self, saved: Saved) {
        self.inner.restore(saved)
    }
    fn apply(&mut self, action: usize) {
        self.inner.apply(action)
    }
}
fn emit(value: Value) {
    println!("{value}");
    std::io::stdout().flush().unwrap();
}
fn phase(name: &str, target: u64) {
    emit(json!({"event":"phase","phase":name,"target":target}));
}
fn new_trainer<G: Game>(game: &G, seed: u64) -> Trainer {
    Trainer {
        sampling: Sampling::Path,
        roots_per_seat: 8,
        ..Trainer::new(game, seed, 3, 150_000_000, false)
    }
}
fn compare(reference: &Trainer, candidate: &Trainer, audit: &Audit, schema: KeySchema) {
    let mut identity = candidate.identity.clone();
    identity["schema"] = reference.identity["schema"].clone();
    identity.as_object_mut().unwrap().remove("key_encoding");
    assert_eq!(identity, reference.identity);
    assert_eq!(
        (
            candidate.iteration,
            candidate.seed,
            candidate.sampling,
            candidate.roots_per_seat,
            candidate.last_average_street,
            candidate.max_entries,
            candidate.freeze_at_cap,
            candidate.frozen_at
        ),
        (
            reference.iteration,
            reference.seed,
            reference.sampling,
            reference.roots_per_seat,
            reference.last_average_street,
            reference.max_entries,
            reference.freeze_at_cap,
            reference.frozen_at
        )
    );
    assert_eq!(
        multi_checkpoint::counts_json(&candidate.counts),
        multi_checkpoint::counts_json(&reference.counts)
    );
    assert_eq!(candidate.table.len(), reference.table.len());
    for (key, b) in candidate.table.iter() {
        let a = reference
            .table
            .get(&audit.legacy(key, schema))
            .expect("mapped row absent");
        assert_eq!(
            (a.actor, a.street, a.code, a.visits),
            (b.actor, b.street, b.code, b.visits)
        );
        assert!(
            a.regrets
                .iter()
                .map(|v| v.to_bits())
                .eq(b.regrets.iter().map(|v| v.to_bits())),
            "regret bits differ"
        );
        match (a.average, b.average) {
            (None, None) => {}
            (Some(x), Some(y)) => assert!(
                x.iter()
                    .map(|v| v.to_bits())
                    .eq(y.iter().map(|v| v.to_bits())),
                "average bits differ"
            ),
            _ => panic!("average scope differs"),
        }
    }
}
fn run() -> Result<(), String> {
    let a: Vec<String> = std::env::args().collect();
    if a.len() != 9 {
        return Err("MODE TABLES OUT SCHEMA SEED THREADS TARGETS INPUT-MANIFEST-OR-DASH".into());
    }
    let seed = a[5].parse::<u64>().map_err(|e| e.to_string())?;
    let threads = a[6].parse::<usize>().map_err(|e| e.to_string())?;
    if !(1..=16).contains(&threads) {
        return Err("threads outside1..16".into());
    }
    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global()
        .map_err(|e| e.to_string())?;
    let targets: Vec<u64> = a[7]
        .split(',')
        .map(|x| x.parse::<u64>().map_err(|e| e.to_string()))
        .collect::<Result<_, _>>()?;
    if targets.is_empty() || targets[0] == 0 || targets.windows(2).any(|x| x[0] >= x[1]) {
        return Err("targets must increase".into());
    }
    let out = Path::new(&a[3]);
    std::fs::create_dir(out).map_err(|e| e.to_string())?;
    let schema = KeySchema::parse(&a[4])?;
    if !KeySchema::EXACT_HISTORY.contains(&schema) { return Err("key benchmark compares exact-history encodings only".into()); }
    phase("load", 0);
    let start = Instant::now();
    let tables = EquityTables::load(Path::new(&a[2]), false)?;
    let game = CashGame {
        config: Config::new(&[2000; 3], 50, 100)?,
        tables,
        schema,
    };
    if a[1] == "audit" {
        if schema != KeySchema::History || targets.len() != 1 {
            return Err("audit needs v1 and one target".into());
        }
        let audit = Arc::new(Audit::new());
        let audited = AuditGame {
            inner: game,
            audit: audit.clone(),
        };
        let mut trainer = new_trainer(&audited, seed);
        phase("audit-training", targets[0]);
        let tick = Instant::now();
        while trainer.counts.nodes < targets[0] {
            trainer.step_fast(&audited);
            if trainer.iteration % 5000 == 0 {
                emit(
                    json!({"event":"progress","nodes":trainer.counts.nodes,"iteration":trainer.iteration,"entries":trainer.table.len(),"seconds":tick.elapsed().as_secs_f64()}),
                );
            }
        }
        let seconds = tick.elapsed().as_secs_f64();
        let reference = out.join("audit-reference.gz");
        phase("audit-save", targets[0]);
        multi_checkpoint::save(&trainer, &reference, Gzip::Compatible)?;
        emit(
            json!({"event":"audit-trained","seconds":seconds,"nodes":trainer.counts.nodes,"iteration":trainer.iteration,"entries":trainer.table.len()}),
        );
        drop(trainer);
        phase("mapping-write", targets[0]);
        let mapping = audit.write(&out.join("mapping.bin"))?;
        emit(json!({"event":"mapping","mapping":mapping}));
        if a[8] != "-" {
            let manifest: Value =
                serde_json::from_reader(std::fs::File::open(&a[8]).map_err(|e| e.to_string())?)
                    .map_err(|e| e.to_string())?;
            for group in manifest.as_array().ok_or("audit manifest needs groups")? {
                phase(
                    "canonical-load",
                    group["target"].as_u64().ok_or("missing target")?,
                );
                let legacy = Path::new(group["v1"]["path"].as_str().ok_or("missing v1 path")?);
                if hu20_trainer::export::sha256_file(legacy)
                    != group["v1"]["sha256"].as_str().ok_or("missing v1 pin")?
                {
                    return Err("reference hash mismatch".into());
                }
                let reference = multi_checkpoint::load(legacy)?;
                for s in [KeySchema::CompactBlake, KeySchema::CompactXxh3] {
                    let pin = &group[s.option()];
                    let path = Path::new(pin["path"].as_str().ok_or("missing candidate path")?);
                    if hu20_trainer::export::sha256_file(path)
                        != pin["sha256"].as_str().ok_or("missing candidate pin")?
                    {
                        return Err("candidate hash mismatch".into());
                    }
                    let candidate = multi_checkpoint::load(path)?;
                    if candidate.identity["schema"] != s.name() {
                        return Err("candidate schema mismatch".into());
                    }
                    phase("canonical-compare", group["target"].as_u64().unwrap());
                    compare(&reference, &candidate, &audit, s);
                    emit(
                        json!({"event":"canonical-verified","target":group["target"],"schema":s.option(),"rows":candidate.table.len()}),
                    );
                }
            }
        }
        emit(
            json!({"event":"complete","mode":"audit","wall_seconds":start.elapsed().as_secs_f64()}),
        );
        return Ok(());
    }
    if a[1] != "train" {
        return Err("mode must be train or audit".into());
    }
    let mut trainer = if a[8] == "-" {
        new_trainer(&game, seed)
    } else {
        let pin: Value =
            serde_json::from_reader(std::fs::File::open(&a[8]).map_err(|e| e.to_string())?)
                .map_err(|e| e.to_string())?;
        let path = Path::new(pin["path"].as_str().ok_or("missing resume path")?);
        if hu20_trainer::export::sha256_file(path)
            != pin["sha256"].as_str().ok_or("missing resume pin")?
        {
            return Err("resume hash mismatch".into());
        }
        let t = multi_checkpoint::load(path)?;
        if t.identity != game.identity()
            || t.seed != seed
            || t.sampling != Sampling::Path
            || t.roots_per_seat != 8
            || t.last_average_street != 3
            || t.max_entries != 150_000_000
            || t.freeze_at_cap
        {
            return Err("resume settings differ".into());
        }
        t
    };
    emit(
        json!({"event":"loaded","seconds":start.elapsed().as_secs_f64(),"nodes":trainer.counts.nodes}),
    );
    for target in targets {
        if target <= trainer.counts.nodes {
            return Err("target is not beyond resume point".into());
        }
        phase("train", target);
        let tick = Instant::now();
        let before = trainer.counts.nodes;
        while trainer.counts.nodes < target {
            trainer.step_fast(&game);
            if trainer.iteration % 5000 == 0 {
                emit(
                    json!({"event":"progress","target":target,"nodes":trainer.counts.nodes,"iteration":trainer.iteration,"entries":trainer.table.len()}),
                );
            }
        }
        let seconds = tick.elapsed().as_secs_f64();
        emit(
            json!({"event":"trained","target":target,"nodes":trainer.counts.nodes,"iteration":trainer.iteration,"entries":trainer.table.len(),"new_nodes":trainer.counts.nodes-before,"seconds":seconds,"nodes_per_second":(trainer.counts.nodes-before) as f64/seconds,"counts":multi_checkpoint::counts_json(&trainer.counts)}),
        );
        let checkpoint = out.join(format!("{target}.gz"));
        phase("save", target);
        let tick = Instant::now();
        multi_checkpoint::save(&trainer, &checkpoint, Gzip::Compatible)?;
        let save = tick.elapsed().as_secs_f64();
        phase("hash", target);
        let tick = Instant::now();
        let digest = hu20_trainer::export::sha256_file(&checkpoint);
        emit(
            json!({"event":"checkpoint","target":target,"path":checkpoint,"sha256":digest,"bytes":checkpoint.metadata().map_err(|e|e.to_string())?.len(),"save_seconds":save,"hash_seconds":tick.elapsed().as_secs_f64()}),
        );
    }
    emit(json!({"event":"complete","mode":"train","wall_seconds":start.elapsed().as_secs_f64()}));
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn decisions() -> [Decision; 3] {
        std::array::from_fn(|i| Decision {
            key: [i as u8; 16],
            actor: 0,
            owner: 0,
            street: 0,
            code: 3,
        })
    }
    #[test]
    fn registry_rejects_aliases_in_both_directions() {
        for forward in [false, true] {
            let audit = Audit::new();
            let mut d = decisions();
            audit.record(d);
            audit.record(d);
            if forward {
                d[1].key = [9; 16];
            } else {
                d[0].key = [9; 16];
            }
            assert!(std::panic::catch_unwind(|| audit.record(d)).is_err());
        }
        let audit = Audit::new();
        let d = decisions();
        audit.record(d);
        assert_eq!(audit.legacy(d[1].key, KeySchema::CompactBlake), d[0].key);
        assert_eq!(audit.legacy(d[2].key, KeySchema::CompactXxh3), d[0].key);
    }
    #[test]
    fn canonical_comparison_rejects_changed_regret_and_average_bits() {
        use hu20_trainer::{
            multi_cfr::Entry,
            small_games::{Kind, SmallGame},
        };
        let audit = Audit::new();
        let d = decisions();
        audit.record(d);
        let game = SmallGame::new(Kind::Kuhn, 3);
        let mut a = new_trainer(&game, 327);
        let mut b = new_trainer(&game, 327);
        a.identity["schema"] = json!(KeySchema::History.name());
        b.identity["schema"] = json!(KeySchema::CompactBlake.name());
        a.table.insert(d[0].key, Entry::new(d[0], 3));
        b.table.insert(d[1].key, Entry::new(d[1], 3));
        compare(&a, &b, &audit, KeySchema::CompactBlake);
        for average in [false, true] {
            let mut c = new_trainer(&game, 327);
            c.identity = b.identity.clone();
            let mut e = Entry::new(d[1], 3);
            if average {
                e.average.as_mut().unwrap()[0] = -0.0;
            } else {
                e.regrets[0] = -0.0;
            }
            c.table.insert(d[1].key, e);
            assert!(
                std::panic::catch_unwind(|| compare(&a, &c, &audit, KeySchema::CompactBlake))
                    .is_err()
            );
        }
    }
}
