//! Eager, portable inference derivatives. No unsafe casts or lazy integrity checks.
use crate::{
    cfr::Key,
    multi_policy::{validate_header, LoadReport, PolicyTable, RowView, Rows, TextReader},
};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{BufReader, BufWriter, Read, Seek, SeekFrom, Write},
    path::{Path, PathBuf},
};

const MAGIC: &[u8; 8] = b"NPLBIN01";
const PREFIX: usize = 128;
const RECORD: usize = 32;
const MAX_HEADER: usize = 65536;
fn err(e: impl std::fmt::Display) -> String {
    e.to_string()
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
pub fn valid_sha(s: &str) -> bool {
    s.len() == 64 && s.bytes().all(|b| b.is_ascii_hexdigit())
}
pub fn sha_file(path: &Path) -> Result<String, String> {
    let mut f = File::open(path).map_err(err)?;
    let mut h = Sha256::new();
    let mut b = vec![0; 1 << 20];
    loop {
        let n = f.read(&mut b).map_err(err)?;
        if n == 0 {
            break;
        }
        h.update(&b[..n]);
    }
    Ok(hex(&h.finalize()))
}
pub fn is_binary(path: &Path) -> Result<bool, String> {
    let mut b = [0; 8];
    let mut f = File::open(path).map_err(err)?;
    if f.metadata().map_err(err)?.len() < 8 {
        return Ok(false);
    }
    f.read_exact(&mut b).map_err(err)?;
    Ok(&b == MAGIC)
}
fn u64_at(b: &[u8], i: usize) -> u64 {
    u64::from_le_bytes(b[i..i + 8].try_into().unwrap())
}
fn checked_size(n: u64, width: u64) -> Result<u64, String> {
    n.checked_mul(width).ok_or("binary size overflow".into())
}
fn plus(a: u64, b: u64) -> Result<u64, String> {
    a.checked_add(b).ok_or("binary offset overflow".into())
}
fn count(n: u64) -> Result<usize, String> {
    usize::try_from(n).map_err(err)
}
fn partial(path: &Path, kind: &str) -> PathBuf {
    let mut name = path.file_name().unwrap_or_default().to_os_string();
    name.push(format!(".{kind}.partial-{}", std::process::id()));
    path.with_file_name(name)
}
#[derive(Clone)]
struct Record {
    key: Key,
    start: u64,
    code: u16,
    owner: u8,
    street: u8,
    mass: u8,
}
pub struct BinaryRows {
    records: Vec<Record>,
    probabilities: Vec<f64>,
}
impl BinaryRows {
    pub fn len(&self) -> usize {
        self.records.len()
    }
    pub fn is_empty(&self) -> bool {
        self.records.is_empty()
    }
    pub fn get(&self, key: &Key) -> Option<RowView<'_>> {
        self.records
            .binary_search_by_key(key, |r| r.key)
            .ok()
            .map(|i| self.row(&self.records[i]))
    }
    fn row(&self, r: &Record) -> RowView<'_> {
        let start = r.start as usize;
        RowView {
            owner: r.owner,
            street: r.street,
            code: r.code,
            probabilities: &self.probabilities[start..start + r.code.count_ones() as usize],
            original_average_mass: match r.mass {
                1 => Some(false),
                2 => Some(true),
                _ => None,
            },
        }
    }
    // Both inputs are sorted. A full audit must be linear rather than perform
    // hundreds of millions of binary searches through the resident index.
    fn row_at(&self, index: usize, key: &Key) -> Result<RowView<'_>, String> {
        let r = self.records.get(index).ok_or("binary key missing")?;
        if &r.key != key {
            return Err("binary sorted key parity mismatch".into());
        }
        Ok(self.row(r))
    }
    pub fn tag_all_mass(&mut self, positive: bool) {
        for r in &mut self.records {
            r.mass = if positive { 2 } else { 1 };
        }
    }
    pub fn tag_mass(&mut self, key: &Key, positive: bool) -> Result<(), String> {
        let i = self
            .records
            .binary_search_by_key(key, |r| r.key)
            .map_err(|_| "mass key absent from policy")?;
        self.records[i].mass = if positive { 2 } else { 1 };
        Ok(())
    }
}
struct MassInput {
    metadata: Value,
    input: BufReader<File>,
    next: Option<Key>,
    previous: Option<Key>,
    zeros: u64,
}
impl MassInput {
    fn open(path: &Path, expected: &str, source: &str, h: &Value) -> Result<Self, String> {
        if !valid_sha(expected) || sha_file(path)? != expected {
            return Err("mass receipt hash mismatch".into());
        }
        let m: Value = serde_json::from_slice(&std::fs::read(path).map_err(err)?).map_err(err)?;
        let data = path.parent().ok_or("mass parent")?.join("zero-keys.bin");
        let zeros = m["zero_mass_rows"].as_u64().ok_or("mass zeros")?;
        let positive = m["positive_mass_rows"].as_u64().ok_or("mass positive")?;
        let keyset = m["keyset_sha256"].as_str().ok_or("mass keyset")?;
        if h["strategy"] != "average"
            || h["last_average_street"] != 3
            || m["format"] != "nplayer-average-mass-v1"
            || m["status"] != "passed"
            || m["strategy"] != "average"
            || m["last_average_street"] != 3
            || m["checkpoint_sha256"] != h["source_checkpoint_sha256"]
            || m["policy_sha256"] != source
            || m["rows"] != h["entries"]
            || m["average_rows"] != h["entries"]
            || m["current_rows"] != 0
            || zeros.checked_add(positive) != h["entries"].as_u64()
            || !valid_sha(keyset)
            || m["zero_keys_sha256"] != sha_file(&data)?
            || std::fs::metadata(&data).map_err(err)?.len() != checked_size(zeros, 16)?
        {
            return Err("mass metadata source/count/schema mismatch".into());
        }
        let metadata = json!({"receipt_sha256":expected,"zero_keys_sha256":m["zero_keys_sha256"],
            "keyset_sha256":keyset,"zero_mass_rows":zeros,"positive_mass_rows":positive});
        let mut result = Self {
            metadata,
            input: BufReader::new(File::open(data).map_err(err)?),
            next: None,
            previous: None,
            zeros,
        };
        result.advance()?;
        Ok(result)
    }
    fn advance(&mut self) -> Result<(), String> {
        if self.zeros == 0 {
            self.next = None;
            return Ok(());
        }
        let mut k = [0; 16];
        self.input.read_exact(&mut k).map_err(err)?;
        if self.previous.is_some_and(|p| p >= k) {
            return Err("mass keys not strictly sorted".into());
        }
        self.previous = Some(k);
        self.next = Some(k);
        self.zeros -= 1;
        Ok(())
    }
    fn tag(&mut self, key: &Key, probabilities: &[f64]) -> Result<u8, String> {
        if self.next.is_some_and(|k| k < *key) {
            return Err("mass key absent from policy".into());
        }
        if self.next == Some(*key) {
            let uniform = 1. / probabilities.len() as f64;
            if probabilities.iter().any(|p| (*p - uniform).abs() > 1e-14) {
                return Err("zero mass row not uniform".into());
            }
            self.advance()?;
            Ok(1)
        } else {
            Ok(2)
        }
    }
}
/// Stream conversion writes the two known-offset regions with independent cursors,
/// without a second mature table or a duplicate on-disk probability spool.
/// Partial files survive failures; publication never overwrites an existing artifact.
pub fn convert(
    source: &Path,
    expected: &str,
    out: &Path,
    mass: Option<(&Path, &str)>,
) -> Result<Value, String> {
    let started = std::time::Instant::now();
    if out.exists() || !valid_sha(expected) {
        return Err("fresh output and complete source hash required".into());
    }
    if sha_file(source)? != expected {
        return Err("source SHA256 mismatch".into());
    }
    let mut text = TextReader::open(source)?;
    let mut mass = mass
        .map(|(p, h)| MassInput::open(p, h, expected, &text.header))
        .transpose()?;
    let metadata = json!({"format":"nplayer-policy-binary-v1","source_policy_sha256":expected,
        "policy":text.header,"dtype":"float64","byte_order":"little","record_bytes":RECORD,
        "mass":mass.as_ref().map(|m|&m.metadata)});
    let header = serde_json::to_vec(&metadata).map_err(err)?;
    if header.len() > MAX_HEADER {
        return Err("binary header too large".into());
    }
    let temp = partial(out, "records");
    let mut file = OpenOptions::new()
        .read(true)
        .write(true)
        .create_new(true)
        .open(&temp)
        .map_err(err)?;
    file.write_all(&[0; PREFIX]).map_err(err)?;
    file.write_all(&header).map_err(err)?;
    let rows_offset = (PREFIX + header.len()) as u64;
    let values_offset = plus(
        rows_offset,
        checked_size(text.header["entries"].as_u64().unwrap(), RECORD as u64)?,
    )?;
    // Opening again is deliberate: try_clone() shares a file offset on Unix.
    let mut value_file = OpenOptions::new().write(true).open(&temp).map_err(err)?;
    value_file
        .seek(SeekFrom::Start(values_offset))
        .map_err(err)?;
    let mut values = BufWriter::new(value_file);
    let mut rows = BufWriter::new(file);
    let mut count_rows = 0u64;
    let mut count_values = 0u64;
    let mut keyset = Sha256::new();
    while let Some((key, row)) = text.next_row(false, &mut LoadReport::default())? {
        let tag = if let Some(m) = mass.as_mut() {
            m.tag(&key, &row.probabilities)?
        } else {
            0
        };
        let mut b = [0; RECORD];
        b[..16].copy_from_slice(&key);
        b[16..24].copy_from_slice(&count_values.to_le_bytes());
        b[24] = row.owner;
        b[25] = row.street;
        b[26] = row.code as u8;
        b[27] = tag;
        rows.write_all(&b).map_err(err)?;
        for p in &row.probabilities {
            values.write_all(&p.to_bits().to_le_bytes()).map_err(err)?;
        }
        count_values = plus(count_values, row.probabilities.len() as u64)?;
        count_rows += 1;
        keyset.update(key);
    }
    if let Some(m) = &mass {
        if m.next.is_some() || m.metadata["keyset_sha256"] != hex(&keyset.finalize()) {
            return Err("mass keyset mismatch".into());
        }
    }
    if sha_file(source)? != expected {
        return Err("source changed during conversion".into());
    }
    values.flush().map_err(err)?;
    drop(values);
    rows.flush().map_err(err)?;
    let mut file = rows.into_inner().map_err(err)?;
    if file.stream_position().map_err(err)? != values_offset {
        return Err("record size mismatch".into());
    }
    let total = plus(values_offset, checked_size(count_values, 8)?)?;
    if file.metadata().map_err(err)?.len() != total {
        return Err("probability size mismatch".into());
    }
    file.seek(SeekFrom::Start(rows_offset)).map_err(err)?;
    let mut hash = Sha256::new();
    let mut buffer = vec![0; 1 << 20];
    loop {
        let n = file.read(&mut buffer).map_err(err)?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    let mut prefix = [0; PREFIX];
    prefix[..8].copy_from_slice(MAGIC);
    for (i, n) in [
        (8, header.len() as u64),
        (16, count_rows),
        (24, count_values),
        (32, rows_offset),
        (40, values_offset),
        (48, total),
    ] {
        prefix[i..i + 8].copy_from_slice(&n.to_le_bytes());
    }
    prefix[56..88].copy_from_slice(&Sha256::digest(&header));
    prefix[88..120].copy_from_slice(&hash.finalize());
    file.seek(SeekFrom::Start(0)).map_err(err)?;
    file.write_all(&prefix).map_err(err)?;
    file.sync_all().map_err(err)?;
    // Same-directory hard-link publication provides atomic no-replace semantics.
    std::fs::hard_link(&temp, out).map_err(err)?;
    std::fs::remove_file(temp).map_err(err)?;
    Ok(
        json!({"status":"converted","source_policy_sha256":expected,"rows":count_rows,"probabilities":count_values,
        "bytes":total,"sha256":sha_file(out)?,"conversion_seconds":started.elapsed().as_secs_f64(),"metadata":metadata}),
    )
}
pub(crate) fn read(path: &Path) -> Result<PolicyTable, String> {
    let mut input = BufReader::with_capacity(1 << 20, File::open(path).map_err(err)?);
    let bytes = input.get_ref().metadata().map_err(err)?.len();
    let mut prefix = [0; PREFIX];
    input.read_exact(&mut prefix).map_err(err)?;
    if &prefix[..8] != MAGIC || prefix[120..].iter().any(|b| *b != 0) {
        return Err("unsupported binary prefix".into());
    }
    let header_len = count(u64_at(&prefix, 8))?;
    let n = u64_at(&prefix, 16);
    let floats = u64_at(&prefix, 24);
    let row_start = u64_at(&prefix, 32);
    let float_start = u64_at(&prefix, 40);
    let total = u64_at(&prefix, 48);
    if header_len > MAX_HEADER
        || row_start != plus(PREFIX as u64, header_len as u64)?
        || float_start != plus(row_start, checked_size(n, RECORD as u64)?)?
        || total != plus(float_start, checked_size(floats, 8)?)?
        || total != bytes
        || floats < n
        || floats > checked_size(n, 6)?
    {
        return Err("binary counts/offsets/length mismatch".into());
    }
    let mut header = vec![0; header_len];
    input.read_exact(&mut header).map_err(err)?;
    if Sha256::digest(&header)[..] != prefix[56..88] {
        return Err("binary header checksum mismatch".into());
    }
    let metadata: Value = serde_json::from_slice(&header).map_err(err)?;
    let h = &metadata["policy"];
    validate_header(h)?;
    let source = metadata["source_policy_sha256"]
        .as_str()
        .ok_or("missing source policy")?;
    if metadata["format"] != "nplayer-policy-binary-v1"
        || metadata["dtype"] != "float64"
        || metadata["byte_order"] != "little"
        || metadata["record_bytes"] != RECORD
        || !valid_sha(source)
        || h["entries"].as_u64() != Some(n)
    {
        return Err("binary schema/source mismatch".into());
    }
    let known_mass = !metadata["mass"].is_null();
    let mass = &metadata["mass"];
    if known_mass
        && (h["strategy"] != "average"
            || h["last_average_street"] != 3
            || ["receipt_sha256", "zero_keys_sha256", "keyset_sha256"]
                .iter()
                .any(|k| !mass[k].as_str().is_some_and(valid_sha)))
    {
        return Err("invalid binary mass identity".into());
    }
    let mut records = Vec::new();
    records.try_reserve_exact(count(n)?).map_err(err)?;
    let players = h["players"].as_u64().unwrap();
    let mut payload = Sha256::new();
    let mut keyset = Sha256::new();
    let mut expected_start = 0;
    let mut zeros = 0u64;
    let mut buffer = vec![0; RECORD * 32768];
    let mut left = n;
    while left > 0 {
        let size = count(left.min(32768))? * RECORD;
        input.read_exact(&mut buffer[..size]).map_err(err)?;
        payload.update(&buffer[..size]);
        for b in buffer[..size].chunks_exact(RECORD) {
            let key: Key = b[..16].try_into().unwrap();
            let start = u64_at(b, 16);
            let code = b[26] as u16;
            let tag = b[27];
            if records.last().is_some_and(|r: &Record| r.key >= key)
                || start != expected_start
                || b[24] as u64 >= players
                || b[25] > 3
                || code == 0
                || code & !63 != 0
                || b[28..].iter().any(|v| *v != 0)
                || tag > 2
                || (known_mass && tag == 0)
                || (!known_mass && tag != 0)
            {
                return Err("invalid binary record".into());
            }
            expected_start = plus(start, code.count_ones() as u64)?;
            zeros += u64::from(tag == 1);
            if expected_start > floats {
                return Err("binary probability offset out of bounds".into());
            }
            records.push(Record {
                key,
                start,
                code,
                owner: b[24],
                street: b[25],
                mass: tag,
            });
            if known_mass {
                keyset.update(key);
            }
        }
        left -= size as u64 / RECORD as u64;
    }
    if expected_start != floats {
        return Err("binary probability count mismatch".into());
    }
    let mut probabilities = Vec::new();
    probabilities
        .try_reserve_exact(count(floats)?)
        .map_err(err)?;
    let mut left = floats;
    while left > 0 {
        let size = count(left.min((buffer.len() / 8) as u64))? * 8;
        input.read_exact(&mut buffer[..size]).map_err(err)?;
        payload.update(&buffer[..size]);
        probabilities.extend(
            buffer[..size]
                .chunks_exact(8)
                .map(|b| f64::from_bits(u64::from_le_bytes(b.try_into().unwrap()))),
        );
        left -= size as u64 / 8;
    }
    if payload.finalize()[..] != prefix[88..120] {
        return Err("binary payload checksum mismatch".into());
    }
    for r in &records {
        let a = &probabilities[r.start as usize..r.start as usize + r.code.count_ones() as usize];
        if a.iter().any(|p| !p.is_finite() || *p < 0. || *p > 1.)
            || (a.iter().sum::<f64>() - 1.).abs() > 1e-12
            || (r.mass == 1 && a.iter().any(|p| (*p - 1. / a.len() as f64).abs() > 1e-14))
        {
            return Err("invalid binary probability distribution".into());
        }
    }
    if known_mass
        && (mass["keyset_sha256"] != hex(&keyset.finalize())
            || mass["zero_mass_rows"].as_u64() != Some(zeros)
            || mass["positive_mass_rows"].as_u64() != Some(n - zeros))
    {
        return Err("binary mass counts/keyset mismatch".into());
    }
    let mut table = PolicyTable::from_header(
        h,
        Rows::Binary(BinaryRows {
            records,
            probabilities,
        }),
    )?;
    table.binary_source_policy_sha256 = Some(source.to_string());
    table.binary_mass_metadata = known_mass.then(|| mass.clone());
    Ok(table)
}
/// Compare every row against the pinned source, including IEEE754 bits and mass tags.
pub fn verify(
    source: &Path,
    source_sha: &str,
    binary: &Path,
    binary_sha: &str,
    mass: Option<(&Path, &str)>,
) -> Result<Value, String> {
    let started = std::time::Instant::now();
    if !valid_sha(source_sha) || sha_file(source)? != source_sha {
        return Err("source SHA256 mismatch".into());
    }
    let table = PolicyTable::load(binary, binary_sha)?;
    if table.binary_source_policy_sha256.as_deref() != Some(source_sha) {
        return Err("binary source binding mismatch".into());
    }
    let mut text = TextReader::open(source)?;
    let mut rows = 0u64;
    let mut mass = mass
        .map(|(p, h)| MassInput::open(p, h, source_sha, &text.header))
        .transpose()?;
    if mass.as_ref().map(|m| &m.metadata) != table.binary_mass_metadata.as_ref() {
        return Err(
            "full audit requires the matching mass receipt, or neither input has mass".into(),
        );
    }
    let binary_rows = match &table.rows {
        Rows::Binary(rows) => rows,
        _ => return Err("binary derivative required".into()),
    };
    while let Some((key, a)) = text.next_row(false, &mut LoadReport::default())? {
        let b = binary_rows.row_at(count(rows)?, &key)?;
        if (a.owner, a.street, a.code) != (b.owner, b.street, b.code)
            || a.probabilities.len() != b.probabilities.len()
            || a.probabilities
                .iter()
                .zip(b.probabilities)
                .any(|(a, b)| a.to_bits() != b.to_bits())
        {
            return Err("binary row parity mismatch".into());
        }
        let expected = mass
            .as_mut()
            .map(|m| m.tag(&key, &a.probabilities))
            .transpose()?;
        let actual = b
            .original_average_mass
            .map(|positive| if positive { 2 } else { 1 });
        if expected != actual {
            return Err("binary original-mass parity mismatch".into());
        }
        rows += 1;
    }
    if mass.as_ref().is_some_and(|m| m.next.is_some()) {
        return Err("mass key absent from policy".into());
    }
    if sha_file(source)? != source_sha {
        return Err("source changed during audit".into());
    }
    if table.identity != text.header["identity"]
        || table.mode.name() != text.header["strategy"]
        || table.scope as u64 != text.header["last_average_street"]
        || table.source_checkpoint_sha256 != text.header["source_checkpoint_sha256"]
        || rows != table.rows.len() as u64
    {
        return Err("binary header parity mismatch".into());
    }
    Ok(
        json!({"status":"passed","rows":rows,"source_policy_sha256":source_sha,"binary_sha256":binary_sha,"verify_seconds":started.elapsed().as_secs_f64()}),
    )
}

#[cfg(test)]
#[path = "multi_binary_tests.rs"]
mod tests;
