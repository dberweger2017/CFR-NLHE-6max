//! Minimal N-player research export/loader. Policy inputs cannot reach a Hand.
use crate::{
    cards::{EquityTables, EQUITY_K50_SHA256},
    cfr::{Key, KeyHasher},
    gz::Gzip,
    multi_cfr::Trainer,
    multi_checkpoint,
    multi_holdem::{self, KeySchema},
    nplayer::{Action, Config, Observation},
};
#[cfg(test)]
use crate::multi_holdem::MENU;
use flate2::read::MultiGzDecoder as GzDecoder;
use rand::{Rng, SeedableRng};
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    hash::BuildHasherDefault,
    io::{BufRead, BufReader},
    path::Path,
    sync::Arc,
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    Current,
    Average,
    ScopedAverage,
}
impl Mode {
    pub fn parse(s: &str) -> Result<Self, String> {
        match s {
            "current" => Ok(Self::Current),
            "average" => Ok(Self::Average),
            "scoped-average" => Ok(Self::ScopedAverage),
            _ => Err("mode must be current, average or scoped-average".into()),
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            Self::Current => "current",
            Self::Average => "average",
            Self::ScopedAverage => "scoped-average",
        }
    }
    pub(crate) fn continuation(self) -> &'static str {
        if self == Self::ScopedAverage {
            "current-after-average-scope"
        } else {
            "none"
        }
    }
}
#[derive(Debug)]
pub struct Row {
    pub owner: u8,
    pub street: u8,
    pub code: u16,
    pub probabilities: Box<[f64]>,
    /// Diagnostic checkpoint mass; ordinary normalized exports do not identify it.
    pub original_average_mass: Option<bool>,
}
pub struct PolicyTable {
    pub identity: Value,
    pub players: usize,
    pub scope: usize,
    pub mode: Mode,
    pub source_checkpoint_sha256: String,
    config: crate::multi_stacks::CashIdentity,
    /// The key schema of `identity`; every lookup keys observations with it.
    pub schema: KeySchema,
    pub rows: Rows,
    pub binary_source_policy_sha256: Option<String>,
    pub binary_mass_metadata: Option<Value>,
}
/// Borrowed row view has the same probability order for either representation.
#[derive(Clone, Copy, Debug)]
pub struct RowView<'a> {
    pub owner: u8,
    pub street: u8,
    pub code: u16,
    pub probabilities: &'a [f64],
    pub original_average_mass: Option<bool>,
}
pub enum Rows {
    Json(HashMap<Key, Row, BuildHasherDefault<KeyHasher>>),
    Binary(crate::multi_binary::BinaryRows),
}
impl Rows {
    pub fn len(&self) -> usize {
        match self {
            Self::Json(r) => r.len(),
            Self::Binary(r) => r.len(),
        }
    }
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
    pub fn get(&self, key: &Key) -> Option<RowView<'_>> {
        match self {
            Self::Json(r) => r.get(key).map(|r| RowView {
                owner: r.owner,
                street: r.street,
                code: r.code,
                probabilities: &r.probabilities,
                original_average_mass: r.original_average_mass,
            }),
            Self::Binary(r) => r.get(key),
        }
    }
    pub fn tag_all_mass(&mut self, positive: bool) {
        match self {
            Self::Json(r) => r
                .values_mut()
                .for_each(|r| r.original_average_mass = Some(positive)),
            Self::Binary(r) => r.tag_all_mass(positive),
        }
    }
    pub fn tag_mass(&mut self, key: &Key, positive: bool) -> Result<(), String> {
        match self {
            Self::Json(r) => {
                r.get_mut(key)
                    .ok_or("mass key absent from policy")?
                    .original_average_mass = Some(positive);
                Ok(())
            }
            Self::Binary(r) => r.tag_mass(key, positive),
        }
    }
}
#[derive(Default)]
pub struct LoadReport {
    pub format: &'static str,
    pub rows: usize,
    pub total_seconds: f64,
    pub verify_seconds: f64,
    pub stream_seconds: f64,
    pub parse_validate_seconds: f64,
    pub insert_seconds: f64,
}
pub(crate) fn validate_header(h: &Value) -> Result<(), String> {
    if h["format"] != "nplayer-policy-v1" || h["missing"] != "uniform" {
        return Err("unsupported policy".into());
    }
    let config = crate::multi_stacks::CashIdentity::parse(&h["identity"])?;
    let players = h["players"].as_u64().ok_or("invalid N")?;
    let scope = h["last_average_street"].as_u64().ok_or("invalid scope")?;
    let mode = Mode::parse(h["strategy"].as_str().ok_or("missing strategy")?)?;
    let source = h["source_checkpoint_sha256"]
        .as_str()
        .ok_or("missing checkpoint pin")?;
    if players != config.players() as u64
        || scope > 3
        || (mode == Mode::Average && scope != 3)
        || h["continuation"] != mode.continuation()
        || !crate::multi_binary::valid_sha(source)
    {
        return Err("invalid policy metadata".into());
    }
    usize::try_from(h["entries"].as_u64().ok_or("invalid entry count")?)
        .map_err(|e| e.to_string())?;
    Ok(())
}
/// Streaming conversion must not first materialize a 250M-row legacy table.
pub(crate) struct TextReader {
    pub header: Value,
    input: BufReader<GzDecoder<std::fs::File>>,
    line: String,
    previous: Option<Key>,
    count: u64,
}
impl TextReader {
    pub fn open(path: &Path) -> Result<Self, String> {
        let mut input = BufReader::new(GzDecoder::new(
            std::fs::File::open(path).map_err(|e| e.to_string())?,
        ));
        let mut line = String::new();
        input.read_line(&mut line).map_err(|e| e.to_string())?;
        let header: Value = serde_json::from_str(&line).map_err(|e| e.to_string())?;
        validate_header(&header)?;
        Ok(Self {
            header,
            input,
            line,
            previous: None,
            count: 0,
        })
    }
    pub fn next_row(
        &mut self,
        profile: bool,
        report: &mut LoadReport,
    ) -> Result<Option<(Key, Row)>, String> {
        self.line.clear();
        let tick = profile.then(std::time::Instant::now);
        let n = self
            .input
            .read_line(&mut self.line)
            .map_err(|e| e.to_string())?;
        if let Some(t) = tick {
            report.stream_seconds += t.elapsed().as_secs_f64();
        }
        if n == 0 {
            if self.count != self.header["entries"].as_u64().unwrap() {
                return Err("entry count mismatch".into());
            }
            return Ok(None);
        }
        let tick = profile.then(std::time::Instant::now);
        let value: Value = serde_json::from_str(&self.line).map_err(|e| e.to_string())?;
        let a = value.as_array().ok_or("invalid row")?;
        if a.len() != 5 {
            return Err("invalid row length".into());
        }
        let hex = a[0].as_str().ok_or("invalid key")?;
        if hex.len() != 32 || !hex.is_ascii() {
            return Err("invalid key".into());
        }
        let mut key = [0; 16];
        for (i, k) in key.iter_mut().enumerate() {
            *k = u8::from_str_radix(&hex[2 * i..2 * i + 2], 16).map_err(|e| e.to_string())?;
        }
        if self.previous.is_some_and(|p| p >= key) {
            return Err("keys must be strictly sorted".into());
        }
        let owner = a[1].as_u64().ok_or("invalid owner")?;
        let street = a[2].as_u64().ok_or("invalid street")?;
        let code = a[3].as_u64().ok_or("invalid actions")?;
        if owner >= self.header["players"].as_u64().unwrap()
            || street > 3
            || code == 0
            || code & !63 != 0
        {
            return Err("invalid row identity".into());
        }
        let probabilities = a[4]
            .as_array()
            .ok_or("invalid probabilities")?
            .iter()
            .map(|v| {
                v.as_f64()
                    .filter(|p| p.is_finite() && *p >= 0. && *p <= 1.)
                    .ok_or("invalid probability".to_string())
            })
            .collect::<Result<Vec<_>, _>>()?;
        if probabilities.len() != code.count_ones() as usize
            || (probabilities.iter().sum::<f64>() - 1.).abs() > 1e-12
        {
            return Err("invalid distribution".into());
        }
        self.previous = Some(key);
        self.count += 1;
        if self.count > self.header["entries"].as_u64().unwrap() {
            return Err("too many rows".into());
        }
        if let Some(t) = tick {
            report.parse_validate_seconds += t.elapsed().as_secs_f64();
        }
        Ok(Some((
            key,
            Row {
                owner: owner as u8,
                street: street as u8,
                code: code as u16,
                probabilities: probabilities.into_boxed_slice(),
                original_average_mass: None,
            },
        )))
    }
}
#[cfg(test)]
pub(crate) fn cash_config(identity: &Value) -> Result<Config, String> {
    crate::multi_stacks::CashIdentity::parse(identity)?.fixed()
}
fn verified(path: &Path, expected: &str) -> Result<(), String> {
    if expected.len() != 64 || !expected.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("expected complete SHA256".into());
    }
    std::fs::File::open(path).map_err(|e| e.to_string())?;
    if crate::multi_binary::sha_file(path)? != expected {
        return Err("SHA256 mismatch".into());
    }
    Ok(())
}
pub fn export(
    checkpoint: &Path,
    expected: &str,
    mode: Mode,
    out: &Path,
    gzip: Gzip,
) -> Result<(), String> {
    verified(checkpoint, expected)?;
    let trainer = multi_checkpoint::load(checkpoint)?;
    write_trainer(&trainer, expected, mode, out, gzip)
}
/// Export an immutable trainer immediately after saving and pinning its checkpoint.
/// The caller owns the saved-state/source-hash association; no second trainer is loaded.
pub fn write_trainer(
    trainer: &Trainer,
    source: &str,
    mode: Mode,
    out: &Path,
    gzip: Gzip,
) -> Result<(), String> {
    crate::multi_stacks::CashIdentity::parse(&trainer.identity)?;
    if mode == Mode::Average && trainer.last_average_street != 3 {
        return Err("full average unavailable; explicitly choose scoped-average or current".into());
    }
    if out.exists() {
        return Err("output already exists".into());
    }
    let header = json!({"format":"nplayer-policy-v1","identity":trainer.identity,"players":trainer.players,"entries":trainer.table.len(),"strategy":mode.name(),"last_average_street":trainer.last_average_street,"continuation":mode.continuation(),"missing":"uniform","source_checkpoint_sha256":source});
    multi_checkpoint::write_atomic(out, |file| {
        trainer.table.write_sorted(
            file,
            gzip,
            format!("{header}\n").as_bytes(),
            |key, e, out| {
                let average =
                    mode != Mode::Current && e.street as usize <= trainer.last_average_street;
                let policy = e.policy(average);
                serde_json::to_writer(
                    &mut *out,
                    &(
                        multi_checkpoint::key_hex(&key),
                        e.actor,
                        e.street,
                        e.code,
                        &policy[..e.regrets.len()],
                    ),
                )
                .unwrap();
                out.push(b'\n');
            },
        )
    })
}
impl PolicyTable {
    pub fn load(path: &Path, expected: &str) -> Result<Self, String> {
        Ok(Self::load_profiled(path, expected, false)?.0)
    }
    /// Fine-grained counters are opt-in: per-row clocks must not tax ordinary play.
    pub fn load_profiled(
        path: &Path,
        expected: &str,
        profile: bool,
    ) -> Result<(Self, LoadReport), String> {
        let start = std::time::Instant::now();
        verified(path, expected)?;
        let verify_seconds = start.elapsed().as_secs_f64();
        let mut report = LoadReport {
            verify_seconds,
            ..LoadReport::default()
        };
        let table = if crate::multi_binary::is_binary(path)? {
            report.format = "binary";
            crate::multi_binary::read(path)?
        } else {
            report.format = "gzip-json";
            let mut reader = TextReader::open(path)?;
            let mut rows = HashMap::default();
            rows.try_reserve(reader.header["entries"].as_u64().unwrap() as usize)
                .map_err(|e| e.to_string())?;
            loop {
                let next = reader.next_row(profile, &mut report)?;
                if let Some((key, row)) = next {
                    let insert = if profile {
                        Some(std::time::Instant::now())
                    } else {
                        None
                    };
                    rows.insert(key, row);
                    if let Some(t) = insert {
                        report.insert_seconds += t.elapsed().as_secs_f64();
                    }
                } else {
                    break;
                }
            }
            Self::from_header(&reader.header, Rows::Json(rows))?
        };
        report.total_seconds = start.elapsed().as_secs_f64();
        report.rows = table.rows.len();
        Ok((table, report))
    }
    pub(crate) fn from_header(h: &Value, rows: Rows) -> Result<Self, String> {
        validate_header(h)?;
        if h["entries"].as_u64() != Some(rows.len() as u64) {
            return Err("entry count mismatch".into());
        }
        Ok(Self {
            identity: h["identity"].clone(),
            players: h["players"].as_u64().unwrap() as usize,
            scope: h["last_average_street"].as_u64().unwrap() as usize,
            mode: Mode::parse(h["strategy"].as_str().unwrap())?,
            source_checkpoint_sha256: h["source_checkpoint_sha256"].as_str().unwrap().to_owned(),
            config: crate::multi_stacks::CashIdentity::parse(&h["identity"])?,
            schema: KeySchema::from_identity(&h["identity"]).ok_or("unsupported key schema")?,
            rows,
            binary_source_policy_sha256: None,
            binary_mass_metadata: None,
        })
    }
    /// Fixed-only consumers must reject a mixture instead of choosing a tuple.
    pub fn config(&self) -> Result<Config, String> {
        self.config.fixed()
    }
    /// The model configuration a projected view uses; see `CashIdentity::projection`.
    pub fn projection_config(&self) -> Result<Config, String> {
        self.config.projection()
    }
    pub fn supports_config(&self, config: Config) -> bool {
        self.config.accepts(config)
    }
    /// The observation's key and identity under this table's schema.
    pub fn decision(&self, observation: &Observation<'_>, tables: &EquityTables) -> crate::multi_cfr::Decision {
        multi_holdem::observation_decision_for(self.schema, observation, tables)
    }
    pub fn distribution(
        &self,
        observation: &Observation<'_>,
        tables: &EquityTables,
    ) -> Result<(Vec<f64>, bool), String> {
        let c = observation.config;
        if !self.supports_config(c)
            || tables.sha256 != EQUITY_K50_SHA256
        {
            return Err("policy/table configuration mismatch".into());
        }
        if observation.actor != Some(observation.seat) || observation.legal.is_none() {
            return Err("policy requires its acting-seat observation".into());
        }
        let d = self.decision(observation, tables);
        if let Some(row) = self.rows.get(&d.key) {
            if (row.owner as usize, row.street as usize, row.code) != (d.owner, d.street, d.code) {
                return Err("policy key/action identity mismatch".into());
            }
            Ok((row.probabilities.to_vec(), true))
        } else {
            Ok((vec![1. / d.len() as f64; d.len()], false))
        }
    }
}
/// Instances share immutable weights if desired, but each seat owns its action RNG.
pub struct Policy {
    pub table: Arc<PolicyTable>,
    rng: rand::rngs::StdRng,
    pub decisions: u64,
    pub misses: u64,
}
impl Policy {
    pub fn new(table: Arc<PolicyTable>, seed: u64) -> Self {
        Self {
            table,
            rng: rand::rngs::StdRng::seed_from_u64(seed),
            decisions: 0,
            misses: 0,
        }
    }
    pub fn choose(
        &mut self,
        observation: &Observation<'_>,
        tables: &EquityTables,
    ) -> Result<Action, String> {
        let (p, found) = self.table.distribution(observation, tables)?;
        let choices = multi_holdem::menu(observation);
        let draw: f64 = self.rng.gen();
        let mut sum = 0.;
        let mut chosen = p.iter().rposition(|&v| v > 0.).ok_or("empty support")?;
        for (i, v) in p.iter().enumerate() {
            sum += v;
            if draw < sum {
                chosen = i;
                break;
            }
        }
        self.decisions += 1;
        self.misses += u64::from(!found);
        Ok(choices[chosen].1)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::multi_cfr::{Decision, Entry};
    use crate::small_games::{Kind, SmallGame};
    use flate2::{write::GzEncoder, Compression};
    use std::io::Write;
    fn fixture(n: usize, scope: usize) -> Trainer {
        let mut t = Trainer::new(&SmallGame::new(Kind::Kuhn, n), 11, scope, 100, false);
        t.identity = json!({"schema":multi_holdem::SCHEMA,"game":"nlhe-cash","players":n,"stacks":vec![2000;n],"small_blind":50,"big_blind":100,"menu":MENU,"card_tables":EQUITY_K50_SHA256,"utility_unit":"big-blind"});
        for street in 0..2 {
            let d = Decision {
                key: [street as u8; 16],
                actor: n - 1,
                owner: n - 1,
                street,
                code: 0b1010,
            };
            let mut e = Entry::new(d, scope);
            e.regrets.copy_from_slice(&[1., 3.]);
            if let Some(a) = &mut e.average {
                a.copy_from_slice(&[4., 0.]);
            }
            t.table.insert(d.key, e);
        }
        t
    }
    #[test]
    fn tables_carry_their_key_schema_and_refuse_unknown_ones() {
        let dir = std::env::temp_dir().join(format!("nplayer-schema-{}", std::process::id()));
        std::fs::create_dir(&dir).unwrap();
        for schema in KeySchema::ALL {
            let mut t=fixture(3,3); t.identity["schema"]=json!(schema.name());
            if schema.is_compact() { t.identity["key_encoding"]=multi_holdem::key_encoding_binding(schema); }
            let path=dir.join(format!("{}.gz",schema.option()));
            // Synthetic rows are intentionally sparse and need not contain root keys.
            write_trainer(&t,&"a".repeat(64),Mode::Average,&path,Gzip::Compatible).unwrap();
            let table=PolicyTable::load(&path,&crate::export::sha256_file(&path)).unwrap();
            assert_eq!(table.schema,schema);
            let binary=dir.join(format!("{}.bin",schema.option()));
            crate::multi_binary::convert(&path,&crate::export::sha256_file(&path),&binary,None).unwrap();
            let binary_table=PolicyTable::load(&binary,&crate::export::sha256_file(&binary)).unwrap();
            assert_eq!(binary_table.schema,schema);
            assert_eq!(binary_table.identity,table.identity);
            for (key,row) in t.table.iter() {
                let a=table.rows.get(&key).unwrap();let b=binary_table.rows.get(&key).unwrap();
                assert_eq!((a.owner,a.street,a.code),(b.owner,b.street,b.code));
                assert_eq!(a.probabilities.iter().map(|x|x.to_bits()).collect::<Vec<_>>(),b.probabilities.iter().map(|x|x.to_bits()).collect::<Vec<_>>());
                assert_eq!(row.code,a.code);
            }

        }
        let mut t=fixture(3,3);t.identity["schema"]=json!("unknown-v99");
        assert!(write_trainer(&t,&"a".repeat(64),Mode::Average,&dir.join("unknown.gz"),Gzip::Compatible).is_err());
        std::fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn mislabelled_compact_policy_and_checkpoint_headers_fail_closed() {
        let dir=std::env::temp_dir().join(format!("compact-binding-{}",std::process::id()));
        std::fs::create_dir(&dir).unwrap();
        let mut t=fixture(3,3);
        t.identity["schema"]=json!(KeySchema::CompactXxh3.name());
        t.identity["key_encoding"]=multi_holdem::key_encoding_binding(KeySchema::CompactXxh3);
        let valid=dir.join("valid.gz");
        write_trainer(&t,&"a".repeat(64),Mode::Average,&valid,Gzip::Compatible).unwrap();
        crate::multi_checkpoint::save(&t,&dir.join("checkpoint.gz"),Gzip::Compatible).unwrap();
        crate::multi_checkpoint::load(&dir.join("checkpoint.gz")).unwrap();
        for target in [KeySchema::History,KeySchema::LiveOrder,KeySchema::CompactBlake] {
            for (name,field) in [("valid.gz","identity"),("checkpoint.gz","game")] {
                let text=std::io::read_to_string(GzDecoder::new(std::fs::File::open(dir.join(name)).unwrap())).unwrap();
                let mut lines=text.lines();let mut h:Value=serde_json::from_str(lines.next().unwrap()).unwrap();
                h[field]["schema"]=json!(target.name());
                let bad=dir.join(format!("bad-{}-{name}",target.option()));
                let mut out=GzEncoder::new(std::fs::File::create(&bad).unwrap(),Compression::default());
                writeln!(out,"{h}").unwrap();for row in lines {writeln!(out,"{row}").unwrap();}out.finish().unwrap();
                let error=if field=="identity" { PolicyTable::load(&bad,&crate::export::sha256_file(&bad)).err() }
                    else { crate::multi_checkpoint::load(&bad).err() };
                assert!(error.unwrap().contains("key encoding binding/schema mismatch"));
            }
        }
        t.identity.as_object_mut().unwrap().remove("key_encoding");
        assert!(cash_config(&t.identity).is_err(),"unbound prototype compact rows must not silently load");
        t.identity["schema"]=json!(KeySchema::History.name());
        assert!(cash_config(&t.identity).is_ok(),"released history headers stay unchanged");
        // Empty compact tables are legal with a correct binding; no mandatory root-row probe.
        t.table=Default::default();t.identity["schema"]=json!(KeySchema::CompactBlake.name());
        t.identity["key_encoding"]=multi_holdem::key_encoding_binding(KeySchema::CompactBlake);
        let empty=dir.join("empty.gz");write_trainer(&t,&"a".repeat(64),Mode::Average,&empty,Gzip::Compatible).unwrap();
        assert!(PolicyTable::load(&empty,&crate::export::sha256_file(&empty)).unwrap().rows.is_empty());
        std::fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn history_checkpoint_and_export_bytes_remain_pinned() {
        let dir=std::env::temp_dir().join(format!("legacy-key-bytes-{}",std::process::id()));std::fs::create_dir(&dir).unwrap();
        let t=fixture(3,3);let cp=dir.join("checkpoint.gz");let policy=dir.join("policy.gz");
        crate::multi_checkpoint::save(&t,&cp,Gzip::Compatible).unwrap();
        write_trainer(&t,&"a".repeat(64),Mode::Average,&policy,Gzip::Compatible).unwrap();
        assert_eq!(crate::export::sha256_file(&cp),"d59e809bf2528035acb36834e30b617e51089476f12d2b40bf2ce841de347885");
        assert_eq!(crate::export::sha256_file(&policy),"20e4ef9031f8dd124068240b3fcceb43aa7013bb54a78ae4bf1afb6c3d54c406");
        std::fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn strategy_scope_is_explicit_and_export_is_deterministic_for_all_n() {
        let dir = std::env::temp_dir().join(format!("nplayer-export-{}", std::process::id()));
        std::fs::create_dir(&dir).unwrap();
        for n in 2..=6 {
            for mode in [Mode::Current, Mode::Average, Mode::ScopedAverage] {
                let t = fixture(n, if mode == Mode::Average { 3 } else { 0 });
                let a = dir.join(format!("{n}-{mode:?}-a.gz"));
                let b = dir.join(format!("{n}-{mode:?}-b.gz"));
                write_trainer(&t, &"a".repeat(64), mode, &a, Gzip::Compatible).unwrap();
                write_trainer(&t, &"a".repeat(64), mode, &b, Gzip::Compatible).unwrap();
                assert_eq!(std::fs::read(&a).unwrap(), std::fs::read(&b).unwrap());
                // Gzip members per piece: same text, read by the loader.
                let p = dir.join(format!("{n}-{mode:?}-p.gz"));
                write_trainer(&t, &"a".repeat(64), mode, &p, Gzip::Parallel).unwrap();
                let text = |path: &Path| {
                    std::io::read_to_string(GzDecoder::new(std::fs::File::open(path).unwrap()))
                        .unwrap()
                };
                assert_ne!(std::fs::read(&a).unwrap(), std::fs::read(&p).unwrap());
                assert_eq!(text(&a), text(&p));
                let members = PolicyTable::load(&p, &crate::export::sha256_file(&p)).unwrap();
                assert_eq!(members.rows.len(), t.table.len());
                let table = PolicyTable::load(&a, &crate::export::sha256_file(&a)).unwrap();
                assert_eq!(table.players, n);
                assert_eq!(table.mode, mode);
                for street in 0..2 {
                    let expected = if mode != Mode::Current && street <= t.last_average_street {
                        vec![1., 0.]
                    } else {
                        vec![0.25, 0.75]
                    };
                    assert_eq!(
                        table.rows.get(&[street as u8; 16]).unwrap().probabilities,
                        &expected
                    );
                }
                assert!(write_trainer(&t, &"a".repeat(64), mode, &a, Gzip::Compatible).is_err());
                assert!(PolicyTable::load(&a, &"0".repeat(64)).is_err());
            }
        }
        assert!(write_trainer(
            &fixture(3, 0),
            &"a".repeat(64),
            Mode::Average,
            &dir.join("missing-average.gz"),
            Gzip::Compatible
        )
        .is_err());
        std::fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn loader_rejects_metadata_rows_and_probability_corruption() {
        let dir =
            std::env::temp_dir().join(format!("nplayer-invalid-policy-{}", std::process::id()));
        std::fs::create_dir(&dir).unwrap();
        let valid = dir.join("valid.gz");
        write_trainer(
            &fixture(3, 0),
            &"a".repeat(64),
            Mode::ScopedAverage,
            &valid,
            Gzip::Compatible,
        )
        .unwrap();
        let values: Vec<Value> =
            BufReader::new(GzDecoder::new(std::fs::File::open(&valid).unwrap()))
                .lines()
                .map(|s| serde_json::from_str(&s.unwrap()).unwrap())
                .collect();
        for mutation in 0..13 {
            let mut bad = values.clone();
            match mutation {
                0 => bad[0]["players"] = json!(2),
                1 => bad[0]["last_average_street"] = json!(4),
                2 => bad[0]["continuation"] = json!("none"),
                3 => bad[0]["identity"]["card_tables"][0] = json!("wrong"),
                4 => bad[1][1] = json!(3),
                5 => bad[1][2] = json!(4),
                6 => bad[1][3] = json!(64),
                7 => bad[1][4] = json!([-0.1, 1.1]),
                8 => bad[1][4] = json!([0.2, 0.2]),
                9 => bad[1][4] = json!([1.]),
                10 => bad[2] = bad[1].clone(),
                11 => {
                    bad.pop();
                }
                _ => bad[0]["source_checkpoint_sha256"] = json!("invalid"),
            }
            let path = dir.join(format!("bad-{mutation}.gz"));
            let mut w = GzEncoder::new(
                std::fs::File::create(&path).unwrap(),
                Compression::default(),
            );
            for row in bad {
                writeln!(w, "{row}").unwrap();
            }
            w.finish().unwrap();
            assert!(
                PolicyTable::load(&path, &crate::export::sha256_file(&path)).is_err(),
                "mutation {mutation}"
            );
        }
        std::fs::remove_dir_all(dir).unwrap();
    }
}
