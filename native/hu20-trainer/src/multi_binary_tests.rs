use super::*;
use crate::{
    cards::EQUITY_K50_SHA256,
    multi_holdem::{MENU, SCHEMA},
    multi_policy::Mode,
};
use flate2::{write::GzEncoder, Compression};
use std::sync::atomic::{AtomicUsize, Ordering};
static SERIAL: AtomicUsize = AtomicUsize::new(0);
fn dir() -> PathBuf {
    let p = std::env::temp_dir().join(format!(
        "binary-policy-{}-{}",
        std::process::id(),
        SERIAL.fetch_add(1, Ordering::Relaxed)
    ));
    std::fs::create_dir(&p).unwrap();
    p
}
fn fixture(path: &Path, n: usize, mode: Mode, scope: usize, rows: usize) -> String {
    let identity = json!({"schema":SCHEMA,"game":"nlhe-cash","players":n,"stacks":vec![10000;n],"small_blind":50,"big_blind":100,"menu":MENU,"card_tables":EQUITY_K50_SHA256,"utility_unit":"big-blind"});
    let h = json!({"format":"nplayer-policy-v1","identity":identity,"players":n,"entries":rows,"strategy":mode.name(),"last_average_street":scope,"continuation":mode.continuation(),"missing":"uniform","source_checkpoint_sha256":"a".repeat(64)});
    let mut w = GzEncoder::new(File::create(path).unwrap(), Compression::default());
    writeln!(w, "{h}").unwrap();
    for i in 0..rows {
        let key = (i as u128).to_be_bytes();
        // Include signed zero and non-binary fractions; no renormalization is allowed.
        let (code, p) = match i % 3 {
            0 => (3, vec![0.5, 0.5]),
            1 => (7, vec![0.1, 0.2, 0.7]),
            _ => (15, vec![-0.0, 1. / 3., 1. / 3., 1. - 2. / 3.]),
        };
        writeln!(
            w,
            "{}",
            json!([
                crate::multi_checkpoint::key_hex(&key),
                i % n,
                i % 4,
                code,
                p
            ])
        )
        .unwrap();
    }
    w.finish().unwrap();
    sha_file(path).unwrap()
}
fn repin(bytes: &mut [u8]) {
    let len = u64_at(bytes, 8) as usize;
    let start = u64_at(bytes, 32) as usize;
    let h = Sha256::digest(&bytes[PREFIX..PREFIX + len]);
    bytes[56..88].copy_from_slice(&h);
    let p = Sha256::digest(&bytes[start..]);
    bytes[88..120].copy_from_slice(&p);
}
#[test]
fn all_modes_seats_and_every_float_bit_roundtrip() {
    let root = dir();
    for n in 2..=6 {
        for mode in [Mode::Current, Mode::Average, Mode::ScopedAverage] {
            let source = root.join(format!("{n}-{mode:?}.gz"));
            let sha = fixture(
                &source,
                n,
                mode,
                if mode == Mode::Average { 3 } else { 1 },
                127,
            );
            let out = source.with_extension("bin");
            convert(&source, &sha, &out, None).unwrap();
            let receipt = verify(&source, &sha, &out, &sha_file(&out).unwrap(), None).unwrap();
            assert_eq!(receipt["rows"], 127);
            let a = PolicyTable::load(&source, &sha).unwrap();
            let b = PolicyTable::load(&out, &sha_file(&out).unwrap()).unwrap();
            assert_eq!(a.config(), b.config());
            assert_eq!(a.mode, b.mode);
            assert_eq!(a.scope, b.scope);
            assert_eq!(
                b.rows.get(&2u128.to_be_bytes()).unwrap().probabilities[0].to_bits(),
                (-0.0f64).to_bits()
            );
            assert!(a.rows.get(&[255; 16]).is_none() && b.rows.get(&[255; 16]).is_none());
            let before = std::fs::read(&out).unwrap();
            assert!(convert(&source, &sha, &out, None).is_err());
            assert_eq!(std::fs::read(&out).unwrap(), before);
            assert!(verify(
                &source,
                &"b".repeat(64),
                &out,
                &sha_file(&out).unwrap(),
                None
            )
            .is_err());
        }
    }
    // Empty policies preserve the missing/uniform behavior rather than invent rows.
    let s = root.join("empty.gz");
    let sha = fixture(&s, 3, Mode::Average, 3, 0);
    let b = root.join("empty.bin");
    convert(&s, &sha, &b, None).unwrap();
    assert!(PolicyTable::load(&b, &sha_file(&b).unwrap())
        .unwrap()
        .rows
        .is_empty());
    std::fs::remove_dir_all(root).unwrap();
}
#[test]
fn corruption_lengths_offsets_rows_probabilities_and_schema_refuse() {
    let root = dir();
    let source = root.join("source.gz");
    let sha = fixture(&source, 3, Mode::Average, 3, 9);
    let out = root.join("valid.bin");
    convert(&source, &sha, &out, None).unwrap();
    let valid = std::fs::read(out).unwrap();
    let row = u64_at(&valid, 32) as usize;
    let floats = u64_at(&valid, 40) as usize;
    for mutation in 0..19 {
        let mut b = valid.clone();
        match mutation {
            0 => b.truncate(PREFIX - 1),
            1 => {
                b.pop();
            }
            2 => b.push(0),
            3 => b[0] ^= 1,
            4 => b[8..16].copy_from_slice(&u64::MAX.to_le_bytes()),
            5 => b[16..24].copy_from_slice(&u64::MAX.to_le_bytes()),
            6 => b[40..48].copy_from_slice(&0u64.to_le_bytes()),
            7 => b[PREFIX + 4] ^= 1,
            8 => b[floats] ^= 1,
            9 => b[row + 24] = 3,
            10 => b[row + 25] = 4,
            11 => b[row + 26] = 0,
            12 => b[row + 26] = 64,
            13 => b[row + 27] = 2,
            14 => b[row + 28] = 1,
            15 => b[row + 16..row + 24].copy_from_slice(&5u64.to_le_bytes()),
            16 => {
                let k = b[row..row + 16].to_vec();
                b[row + RECORD..row + RECORD + 16].copy_from_slice(&k);
            }
            17 => b[floats..floats + 8].copy_from_slice(&f64::NAN.to_bits().to_le_bytes()),
            _ => b[120] = 1,
        }
        // Internal semantic validation must reject bad records even if a caller
        // supplies a matching outer checksum and recomputes internal checksums.
        if mutation >= 9 && mutation <= 17 {
            repin(&mut b);
        }
        let path = root.join(format!("bad-{mutation}.bin"));
        std::fs::write(&path, b).unwrap();
        assert!(
            PolicyTable::load(&path, &sha_file(&path).unwrap()).is_err(),
            "mutation {mutation}"
        );
    }
    for (old, new) in [
        ("float64", "float32"),
        ("little", "middle"),
        (SCHEMA, "wrong-key-schema"),
        (MENU, "wrong-menu"),
    ] {
        let mut b = valid.clone();
        let len = u64_at(&b, 8) as usize;
        let mut h: Value = serde_json::from_slice(&b[PREFIX..PREFIX + len]).unwrap();
        if old == "float64" {
            h["dtype"] = json!(new);
        } else if old == "little" {
            h["byte_order"] = json!(new);
        } else if old == SCHEMA {
            h["policy"]["identity"]["schema"] = json!(new);
        } else {
            h["policy"]["identity"]["menu"] = json!(new);
        }
        // Pad shorter replacement JSON to retain legal offsets, exposing schema checks.
        let text = serde_json::to_vec(&h).unwrap();
        assert!(text.len() <= len);
        b[PREFIX..PREFIX + len].fill(b' ');
        b[PREFIX..PREFIX + text.len()].copy_from_slice(&text);
        repin(&mut b);
        let p = root.join("schema.bin");
        std::fs::write(&p, b).unwrap();
        assert!(PolicyTable::load(&p, &sha_file(&p).unwrap()).is_err());
    }
    std::fs::remove_dir_all(root).unwrap();
}
fn mass(root: &Path, source_sha: &str) -> (PathBuf, String) {
    let zeros = root.join("zero-keys.bin");
    std::fs::write(&zeros, 0u128.to_be_bytes()).unwrap();
    let mut keys = Sha256::new();
    for i in 0..9u128 {
        keys.update(i.to_be_bytes());
    }
    let receipt = root.join("receipt.json");
    let h = json!({"format":"nplayer-average-mass-v1","status":"passed","strategy":"average","last_average_street":3,
        "checkpoint_sha256":"a".repeat(64),"policy_sha256":source_sha,"rows":9,"average_rows":9,"current_rows":0,"zero_mass_rows":1,"positive_mass_rows":8,
        "keyset_sha256":hex(&keys.finalize()),"zero_keys_sha256":sha_file(&zeros).unwrap()});
    std::fs::write(&receipt, h.to_string()).unwrap();
    let sha = sha_file(&receipt).unwrap();
    (receipt, sha)
}
#[test]
fn audited_mass_is_preserved_and_wrong_receipts_are_refused() {
    let root = dir();
    let source = root.join("source.gz");
    let sha = fixture(&source, 3, Mode::Average, 3, 9);
    let (receipt, pin) = mass(&root, &sha);
    let out = root.join("policy.bin");
    convert(&source, &sha, &out, Some((&receipt, &pin))).unwrap();
    let binary_sha = sha_file(&out).unwrap();
    let table = PolicyTable::load(&out, &binary_sha).unwrap();
    assert_eq!(
        table
            .rows
            .get(&0u128.to_be_bytes())
            .unwrap()
            .original_average_mass,
        Some(false)
    );
    assert_eq!(
        table
            .rows
            .get(&1u128.to_be_bytes())
            .unwrap()
            .original_average_mass,
        Some(true)
    );
    assert!(verify(&source, &sha, &out, &binary_sha, None).is_err());
    verify(&source, &sha, &out, &binary_sha, Some((&receipt, &pin))).unwrap();
    assert!(convert(
        &source,
        &sha,
        &root.join("bad.bin"),
        Some((&receipt, &"0".repeat(64)))
    )
    .is_err());
    // A valid normalized uniform distribution alone must not be labeled zero mass.
    let plain = root.join("plain.bin");
    convert(&source, &sha, &plain, None).unwrap();
    assert_eq!(
        PolicyTable::load(&plain, &sha_file(&plain).unwrap())
            .unwrap()
            .rows
            .get(&0u128.to_be_bytes())
            .unwrap()
            .original_average_mass,
        None
    );
    std::fs::write(root.join("zero-keys.bin"), 1u128.to_be_bytes()).unwrap();
    let mut h: Value = serde_json::from_slice(&std::fs::read(&receipt).unwrap()).unwrap();
    h["zero_keys_sha256"] = json!(sha_file(&root.join("zero-keys.bin")).unwrap());
    std::fs::write(&receipt, h.to_string()).unwrap();
    assert!(convert(
        &source,
        &sha,
        &root.join("nonuniform.bin"),
        Some((&receipt, &sha_file(&receipt).unwrap()))
    )
    .is_err());
    std::fs::remove_dir_all(root).unwrap();
}
#[test]
fn seeded_legal_trajectories_and_missing_fallback_are_identical() {
    use crate::{
        cards::EquityTables,
        game::Kind,
        multi_holdem,
        multi_policy::Policy,
        nplayer::{Action, Config, Hand},
    };
    use rand::{seq::SliceRandom, SeedableRng};
    use std::{
        collections::{BTreeMap, BTreeSet},
        sync::Arc,
    };
    let root = dir();
    let config = Config::new(&[10000; 3], 50, 100).unwrap();
    let mut cards: [BTreeSet<u128>; 3] = std::array::from_fn(|_| BTreeSet::new());
    let mut decks = Vec::new();
    for seed in 0..24 {
        let mut deck: Vec<u8> = (0..52).collect();
        deck.shuffle(&mut rand::rngs::StdRng::seed_from_u64(seed));
        let mut hand = Hand::from_deck(config, seed as usize % 3, &deck).unwrap();
        while let Some(actor) = hand.actor() {
            let o = hand.observe(actor).unwrap();
            if !o.board.is_empty() {
                cards[o.board.len() - 3].insert(hu20_buckets::class_key(&o.hole, o.board));
            }
            hand.apply_mut(Action {
                kind: if hand.legal().unwrap().check {
                    Kind::Check
                } else {
                    Kind::Call
                },
                raise_to: 0,
            })
            .unwrap();
        }
        decks.push(deck);
    }
    let tables = EquityTables::policy_test_fixture(cards.map(|s| s.into_iter().collect()));
    let mut rows = BTreeMap::new();
    for (i, deck) in decks.iter().enumerate() {
        let mut hand = Hand::from_deck(config, i % 3, deck).unwrap();
        while let Some(actor) = hand.actor() {
            let o = hand.observe(actor).unwrap();
            let d = multi_holdem::observation_decision(&o, &tables);
            let action = Action {
                kind: if o.legal.unwrap().check {
                    Kind::Check
                } else {
                    Kind::Call
                },
                raise_to: 0,
            };
            let choices = multi_holdem::menu(&o);
            let mut p = vec![0.; choices.len()];
            p[choices.iter().position(|a| a.1 == action).unwrap()] = 1.;
            // Keep some known rows and deliberately omit others; new betting
            // histories reached in play also exercise the uniform missing path.
            if i % 3 != 0 {
                rows.insert(
                    d.key,
                    json!([
                        crate::multi_checkpoint::key_hex(&d.key),
                        d.owner,
                        d.street,
                        d.code,
                        p
                    ]),
                );
            }
            hand.apply_mut(action).unwrap();
        }
    }
    let source = root.join("game.gz");
    fixture(&source, 3, Mode::Average, 3, 0);
    let mut h = TextReader::open(&source).unwrap().header;
    h["entries"] = json!(rows.len());
    let mut w = GzEncoder::new(File::create(&source).unwrap(), Compression::default());
    writeln!(w, "{h}").unwrap();
    for row in rows.values() {
        writeln!(w, "{row}").unwrap();
    }
    w.finish().unwrap();
    let binary = root.join("game.bin");
    let sha = sha_file(&source).unwrap();
    convert(&source, &sha, &binary, None).unwrap();
    let a = Arc::new(PolicyTable::load(&source, &sha).unwrap());
    let b = Arc::new(PolicyTable::load(&binary, &sha_file(&binary).unwrap()).unwrap());
    let mut known = 0;
    let mut missing = 0;
    for seed in 0..3 {
        for (i, deck) in decks.iter().enumerate() {
            let mut left = Hand::from_deck(config, i % 3, deck).unwrap();
            let mut right = left.clone();
            let mut pa: Vec<_> = (0..3)
                .map(|seat| Policy::new(a.clone(), seed * 3 + seat))
                .collect();
            let mut pb: Vec<_> = (0..3)
                .map(|seat| Policy::new(b.clone(), seed * 3 + seat))
                .collect();
            while let Some(actor) = left.actor() {
                let o = left.observe(actor).unwrap();
                let da = a.distribution(&o, &tables).unwrap();
                let db = b
                    .distribution(&right.observe(actor).unwrap(), &tables)
                    .unwrap();
                assert_eq!(da, db);
                if da.1 {
                    known += 1;
                } else {
                    missing += 1;
                    assert_eq!(da.0, vec![1. / da.0.len() as f64; da.0.len()]);
                }
                let aa = pa[actor].choose(&o, &tables).unwrap();
                let ab = pb[actor]
                    .choose(&right.observe(actor).unwrap(), &tables)
                    .unwrap();
                assert_eq!(aa, ab);
                left.apply_mut(aa).unwrap();
                right.apply_mut(ab).unwrap();
                assert_eq!(left, right);
            }
            for seat in 0..3 {
                assert_eq!(
                    (pa[seat].decisions, pa[seat].misses),
                    (pb[seat].decisions, pb[seat].misses)
                );
            }
        }
    }
    assert!(known > 0 && missing > 0);
    assert_eq!(std::mem::size_of::<Record>(), 32);
    std::fs::remove_dir_all(root).unwrap();
}
