//! Checkpoint-audited original-average mass, independent of normalized policy rows.
use hu20_trainer::{export::sha256_file, multi_policy::PolicyTable};
use serde_json::Value;
use std::path::Path;

pub const LABELS: [&str; 3] = ["positive_mass", "zero_mass", "missing"];
pub struct MassMetadata {
    zero: Vec<[u8; 16]>,
    pub receipt_sha256: String,
    pub keyset_sha256: String,
}
impl MassMetadata {
    pub fn load(
        directory: &Path,
        expected: &str,
        policy_sha: &str,
        table: &PolicyTable,
    ) -> Result<Self, String> {
        let receipt = directory.join("receipt.json");
        let data = directory.join("zero-keys.bin");
        if !receipt.is_file() || !data.is_file() || sha256_file(&receipt) != expected {
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
            || h["policy_sha256"] != policy_sha
            || rows != table.rows.len() as u64
            || h["average_rows"].as_u64() != Some(rows)
            || h["current_rows"] != 0
            || zeros.checked_add(positive) != Some(rows)
            || keyset.len() != 64
            || !keyset.bytes().all(|b| b.is_ascii_hexdigit())
            || h["zero_keys_sha256"].as_str() != Some(&sha256_file(&data))
        {
            return Err("mass metadata lineage/counts differ".into());
        }
        let bytes = std::fs::read(&data).map_err(|e| e.to_string())?;
        if bytes.len() % 16 != 0 || bytes.len() as u64 / 16 != zeros {
            return Err("mass metadata byte/count mismatch".into());
        }
        let mut zero: Vec<[u8; 16]> = Vec::new();
        for key in bytes.chunks_exact(16) {
            let key: [u8; 16] = key.try_into().unwrap();
            if zero.last().is_some_and(|old| old >= &key) {
                return Err("zero mass keys not strictly sorted".into());
            }
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
            zero.push(key);
        }
        Ok(Self {
            zero,
            receipt_sha256: expected.into(),
            keyset_sha256: keyset.into(),
        })
    }
    pub fn classify(&self, key: &[u8; 16], found: bool) -> usize {
        if !found {
            2
        } else if self.zero.binary_search(key).is_ok() {
            1
        } else {
            0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn uniform_positive_mass_is_not_zero_mass_and_missing_is_distinct() {
        let m = MassMetadata {
            zero: vec![[2; 16]],
            receipt_sha256: String::new(),
            keyset_sha256: String::new(),
        };
        assert_eq!(LABELS[m.classify(&[1; 16], true)], "positive_mass");
        assert_eq!(LABELS[m.classify(&[2; 16], true)], "zero_mass");
        assert_eq!(LABELS[m.classify(&[3; 16], false)], "missing");
    }
    fn fixture() -> (std::path::PathBuf, PolicyTable, String) {
        use flate2::{write::GzEncoder, Compression};
        use serde_json::json;
        use std::io::Write;
        let path = std::env::temp_dir().join(format!(
            "mass-{}-{}",
            std::process::id(),
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
        let (path, table, digest) = fixture();
        let receipt = sha256_file(&path.join("receipt.json"));
        let m = MassMetadata::load(&path, &receipt, &digest, &table).unwrap();
        assert_eq!(m.classify(&[1; 16], true), 0);
        assert_eq!(m.classify(&[2; 16], true), 1);
        assert!(MassMetadata::load(&path, &receipt, &"c".repeat(64), &table).is_err());
        std::fs::write(path.join("zero-keys.bin"), [3u8; 16]).unwrap();
        assert!(MassMetadata::load(&path, &receipt, &digest, &table).is_err());
        std::fs::remove_dir_all(path).unwrap();
    }
    #[test]
    fn incomplete_receipt_and_forged_counts_refuse() {
        let (path, table, digest) = fixture();
        let file = path.join("receipt.json");
        let mut r: Value = serde_json::from_slice(&std::fs::read(&file).unwrap()).unwrap();
        r["positive_mass_rows"] = serde_json::json!(2);
        std::fs::write(&file, r.to_string()).unwrap();
        assert!(MassMetadata::load(&path, &sha256_file(&file), &digest, &table).is_err());
        std::fs::remove_file(&file).unwrap();
        assert!(MassMetadata::load(&path, &"a".repeat(64), &digest, &table).is_err());
        std::fs::remove_dir_all(path).unwrap();
    }
}
