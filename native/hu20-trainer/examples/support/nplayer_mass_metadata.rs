//! Checkpoint-audited original-average mass, independent of normalized policy rows.
use hu20_trainer::{
    export::sha256_file,
    multi_policy::{PolicyTable, RowView},
};
use serde_json::Value;
use std::path::Path;

pub const LABELS: [&str; 3] = ["positive_mass", "zero_mass", "missing"];
pub struct MassMetadata {
    pub receipt_sha256: String,
    pub keyset_sha256: String,
}
impl MassMetadata {
    pub fn load(
        directory: &Path,
        expected: &str,
        policy_sha: &str,
        table: &mut PolicyTable,
    ) -> Result<Self, String> {
        let receipt = directory.join("receipt.json");
        let data = directory.join("zero-keys.bin");
        if !receipt.is_file() || sha256_file(&receipt) != expected {
            return Err("mass metadata receipt missing or changed".into());
        }
        let h: Value = serde_json::from_slice(&std::fs::read(&receipt).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
        let rows = h["rows"].as_u64().ok_or("mass rows")?;
        let zeros = h["zero_mass_rows"].as_u64().ok_or("zero mass rows")?;
        let positive = h["positive_mass_rows"]
            .as_u64()
            .ok_or("positive mass rows")?;
        let keyset = h["keyset_sha256"].as_str().ok_or("mass keyset")?;
        if h["format"] != "nplayer-average-mass-v1"
            || h["status"] != "passed"
            || h["strategy"] != "average"
            || h["last_average_street"] != 3
            || h["checkpoint_sha256"] != table.source_checkpoint_sha256
            || h["policy_sha256"]
                != table
                    .binary_source_policy_sha256
                    .as_deref()
                    .unwrap_or(policy_sha)
            || rows != table.rows.len() as u64
            || h["average_rows"].as_u64() != Some(rows)
            || h["current_rows"] != 0
            || zeros.checked_add(positive) != Some(rows)
            || keyset.len() != 64
            || !keyset.bytes().all(|b| b.is_ascii_hexdigit())
        {
            return Err("mass metadata lineage/counts differ".into());
        }
        if let Some(m) = &table.binary_mass_metadata {
            // The eager reader already checked every embedded tag, row, count
            // and keyset. Bind the exact audit receipt without reloading its
            // potentially multi-gigabyte zero-key list or retagging rows.
            if m["receipt_sha256"] != expected
                || m["zero_keys_sha256"] != h["zero_keys_sha256"]
                || m["keyset_sha256"] != h["keyset_sha256"]
                || m["zero_mass_rows"] != zeros
                || m["positive_mass_rows"] != positive
            {
                return Err("embedded mass receipt mismatch".into());
            }
            return Ok(Self {
                receipt_sha256: expected.into(),
                keyset_sha256: keyset.into(),
            });
        }
        if !data.is_file() || h["zero_keys_sha256"].as_str() != Some(&sha256_file(&data)) {
            return Err("mass zero keys missing or changed".into());
        }
        if std::fs::metadata(&data).map_err(|e| e.to_string())?.len()
            != zeros.checked_mul(16).ok_or("zero byte overflow")?
        {
            return Err("mass metadata byte/count mismatch".into());
        }
        // Row already has alignment padding. Tag it once while loading rather
        // than retain tens of millions of zero-key hashes for every decision.
        table.rows.tag_all_mass(true);
        use std::io::Read;
        let mut input =
            std::io::BufReader::new(std::fs::File::open(&data).map_err(|e| e.to_string())?);
        let mut previous = None;
        for _ in 0..zeros {
            let mut key = [0u8; 16];
            input.read_exact(&mut key).map_err(|e| e.to_string())?;
            if previous.is_some_and(|old| old >= key) {
                return Err("zero mass keys not strictly sorted".into());
            }
            previous = Some(key);
            let row = table
                .rows
                .get(&key)
                .ok_or("zero mass key absent from policy")?;
            let uniform = 1. / row.probabilities.len() as f64;
            if row
                .probabilities
                .iter()
                .any(|p| (*p - uniform).abs() > 1e-14)
            {
                return Err("zero mass row does not use uniform fallback".into());
            }
            table.rows.tag_mass(&key, false)?;
        }
        Ok(Self {
            receipt_sha256: expected.into(),
            keyset_sha256: keyset.into(),
        })
    }
    #[cfg(test)]
    pub fn classify(table: &PolicyTable, key: &[u8; 16]) -> Result<usize, String> {
        Self::classify_row(table.rows.get(key))
    }
    pub fn classify_row(row: Option<RowView<'_>>) -> Result<usize, String> {
        match row {
            None => Ok(2),
            Some(row) => match row.original_average_mass {
                Some(true) => Ok(0),
                Some(false) => Ok(1),
                None => Err("original mass metadata not attached".into()),
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn diagnostic_mass_tag_uses_existing_row_padding() {
        struct LegacyRow {
            _owner: u8,
            _street: u8,
            _code: u16,
            _probabilities: Box<[f64]>,
        }
        assert_eq!(
            std::mem::size_of::<hu20_trainer::multi_policy::Row>(),
            std::mem::size_of::<LegacyRow>()
        );
    }
    static FIXTURE_ID: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);

    fn fixture() -> (std::path::PathBuf, PolicyTable, String) {
        use flate2::{write::GzEncoder, Compression};
        use serde_json::json;
        use std::io::Write;
        let path = std::env::temp_dir().join(format!(
            "mass-{}-{}-{}",
            std::process::id(),
            FIXTURE_ID.fetch_add(1, std::sync::atomic::Ordering::Relaxed),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&path).unwrap();
        let cp = "a".repeat(64);
        let identity = json!({"players":3,"stacks":[10000,10000,10000],"small_blind":50,"big_blind":100,
            "schema":hu20_trainer::multi_holdem::SCHEMA,"menu":hu20_trainer::multi_holdem::MENU,
            "game":"nlhe-cash","utility_unit":"big-blind","card_tables":hu20_trainer::cards::EQUITY_K50_SHA256});
        let mut gzip = GzEncoder::new(Vec::new(), Compression::default());
        writeln!(gzip,"{}",json!({"format":"nplayer-policy-v1","identity":identity,"players":3,"entries":2,
            "strategy":"average","last_average_street":3,"continuation":"none","missing":"uniform","source_checkpoint_sha256":cp})).unwrap();
        for value in [1u8, 2] {
            writeln!(
                gzip,
                "{}",
                json!([
                    hu20_trainer::multi_checkpoint::key_hex(&[value; 16]),
                    0,
                    0,
                    6,
                    [0.5, 0.5]
                ])
            )
            .unwrap();
        }
        let policy = path.join("policy.gz");
        std::fs::write(&policy, gzip.finish().unwrap()).unwrap();
        let digest = sha256_file(&policy);
        let table = PolicyTable::load(&policy, &digest).unwrap();
        let zero = path.join("zero-keys.bin");
        std::fs::write(&zero, [2u8; 16]).unwrap();
        std::fs::write(path.join("receipt.json"),json!({"format":"nplayer-average-mass-v1","status":"passed",
            "checkpoint_sha256":cp,"policy_sha256":digest,"strategy":"average","last_average_street":3,
            "rows":2,"average_rows":2,"current_rows":0,"zero_mass_rows":1,"positive_mass_rows":1,
            "keyset_sha256":"b".repeat(64),"zero_keys_sha256":sha256_file(&zero)}).to_string()).unwrap();
        (path, table, digest)
    }
    #[test]
    fn audited_metadata_loads_and_wrong_model_binding_refuses() {
        let (path, mut table, digest) = fixture();
        let receipt = sha256_file(&path.join("receipt.json"));
        let _m = MassMetadata::load(&path, &receipt, &digest, &mut table).unwrap();
        assert_eq!(MassMetadata::classify(&table, &[1; 16]).unwrap(), 0);
        assert_eq!(MassMetadata::classify(&table, &[2; 16]).unwrap(), 1);
        assert_eq!(MassMetadata::classify(&table, &[3; 16]).unwrap(), 2);
        assert!(MassMetadata::load(&path, &receipt, &"c".repeat(64), &mut table).is_err());
        std::fs::write(path.join("zero-keys.bin"), [3u8; 16]).unwrap();
        assert!(MassMetadata::load(&path, &receipt, &digest, &mut table).is_err());
        std::fs::remove_dir_all(path).unwrap();
    }
    #[test]
    fn incomplete_receipt_and_forged_counts_refuse() {
        let (path, mut table, digest) = fixture();
        let file = path.join("receipt.json");
        let mut r: Value = serde_json::from_slice(&std::fs::read(&file).unwrap()).unwrap();
        r["positive_mass_rows"] = serde_json::json!(2);
        std::fs::write(&file, r.to_string()).unwrap();
        assert!(MassMetadata::load(&path, &sha256_file(&file), &digest, &mut table).is_err());
        std::fs::remove_file(&file).unwrap();
        assert!(MassMetadata::load(&path, &"a".repeat(64), &digest, &mut table).is_err());
        std::fs::remove_dir_all(path).unwrap();
    }
    #[test]
    fn binary_embedded_tags_bind_receipt_without_zero_key_reload() {
        let (path, _, digest) = fixture();
        // The original helper fixture uses a placeholder keyset; conversion
        // enforces the actual sorted-key digest, so replace it before pinning.
        use sha2::{Digest, Sha256};
        let receipt = path.join("receipt.json");
        let mut h: Value = serde_json::from_slice(&std::fs::read(&receipt).unwrap()).unwrap();
        let mut keys = Sha256::new();
        keys.update([1u8; 16]);
        keys.update([2u8; 16]);
        h["keyset_sha256"] = serde_json::json!(format!("{:x}", keys.finalize()));
        std::fs::write(&receipt, h.to_string()).unwrap();
        let receipt_sha = sha256_file(&receipt);
        let binary = path.join("policy.bin");
        hu20_trainer::multi_binary::convert(
            &path.join("policy.gz"),
            &digest,
            &binary,
            Some((&receipt, &receipt_sha)),
        )
        .unwrap();
        let binary_sha = sha256_file(&binary);
        let mut table = PolicyTable::load(&binary, &binary_sha).unwrap();
        // The derivative is self-contained after receipt binding. Source inputs
        // stay retained in real campaigns; this removal is a temporary fixture.
        std::fs::remove_file(path.join("zero-keys.bin")).unwrap();
        MassMetadata::load(&path, &receipt_sha, &binary_sha, &mut table).unwrap();
        assert_eq!(MassMetadata::classify(&table, &[1; 16]).unwrap(), 0);
        assert_eq!(MassMetadata::classify(&table, &[2; 16]).unwrap(), 1);
        h["zero_mass_rows"] = serde_json::json!(0);
        h["positive_mass_rows"] = serde_json::json!(2);
        std::fs::write(&receipt, h.to_string()).unwrap();
        assert!(
            MassMetadata::load(&path, &sha256_file(&receipt), &binary_sha, &mut table).is_err()
        );
        std::fs::remove_dir_all(path).unwrap();
    }
}
