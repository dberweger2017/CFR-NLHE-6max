//! Opt-in research player: preserve every base row; fill only missing positive rows.
use super::mass;
use hu20_trainer::{
    cards::EquityTables,
    multi_cfr::Decision,
    multi_holdem,
    multi_policy::{Mode, PolicyTable, RowView},
    nplayer::{Action, Observation},
};
use rand::{Rng, SeedableRng};
use serde_json::{json, Value};
use std::sync::Arc;

pub const FORMAT: &str = "nplayer-missing-positive-v1";

/// No RNG or game state is available to the row selection rule.
pub struct Selection {
    pub probabilities: Vec<f64>,
    pub status: &'static str,
    pub source: &'static str,
    pub base_status: &'static str,
    pub donor_status: &'static str,
}
impl Selection {
    pub fn diagnostic(&self) -> Value {
        json!({"format":FORMAT,"source":self.source,"base_status":self.base_status,
            "donor_status":self.donor_status,"probabilities":self.probabilities})
    }
}

fn checked<'a>(row: Option<RowView<'a>>, d: &Decision) -> Result<Option<RowView<'a>>, String> {
    if let Some(r) = row {
        if (r.owner as usize, r.street as usize, r.code) != (d.owner, d.street, d.code)
            || r.probabilities.len() != d.len()
            || r.probabilities.iter().any(|x| !x.is_finite() || *x < 0.)
            || (r.probabilities.iter().sum::<f64>() - 1.).abs() > 1e-12
        {
            return Err("composition row identity/probabilities differ".into());
        }
        if r.original_average_mass == Some(false)
            && r.probabilities
                .iter()
                .any(|p| (*p - 1. / d.len() as f64).abs() > 1e-14)
        {
            return Err("composition zero mass must retain uniform fallback".into());
        }
    }
    Ok(row)
}

pub fn select(base: &PolicyTable, donor: &PolicyTable, d: &Decision) -> Result<Selection, String> {
    if d.len() == 0 {
        return Err("composition empty legal menu".into());
    }
    let row = checked(base.rows.get(&d.key), d)?;
    let base_status = mass::LABELS[mass::MassMetadata::classify_row(row)?];
    if let Some(r) = row {
        // Existence takes precedence, even for a zero-mass base row. Do not
        // consult the donor or renormalize the original float64 probabilities.
        return Ok(Selection {
            probabilities: r.probabilities.to_vec(),
            status: base_status,
            source: "base",
            base_status,
            donor_status: "not_queried",
        });
    }
    let row = checked(donor.rows.get(&d.key), d)?;
    let donor_status = mass::LABELS[mass::MassMetadata::classify_row(row)?];
    if donor_status == "positive_mass" {
        return Ok(Selection {
            probabilities: row.unwrap().probabilities.to_vec(),
            status: donor_status,
            source: "donor",
            base_status,
            donor_status,
        });
    }
    Ok(Selection {
        probabilities: vec![1. / d.len() as f64; d.len()],
        status: "missing",
        source: "uniform",
        base_status,
        donor_status,
    })
}

pub fn compatible(base: &PolicyTable, donor: &PolicyTable) -> Result<(), String> {
    if base.identity != donor.identity
        || base.config() != donor.config()
        || base.mode != Mode::Average
        || donor.mode != Mode::Average
        || base.scope != 3
        || donor.scope != 3
    {
        return Err(
            "composition requires identical full-average game/key/menu/card identities".into(),
        );
    }
    Ok(())
}

pub struct Policy {
    base: Arc<PolicyTable>,
    donor: Arc<PolicyTable>,
    rng: rand::rngs::StdRng,
}
impl Policy {
    pub fn new(base: Arc<PolicyTable>, donor: Arc<PolicyTable>, seed: u64) -> Result<Self, String> {
        compatible(&base, &donor)?;
        Ok(Self {
            base,
            donor,
            rng: rand::rngs::StdRng::seed_from_u64(seed),
        })
    }
    pub fn choose(
        &mut self,
        view: &Observation<'_>,
        tables: &EquityTables,
    ) -> Result<(Action, Selection), String> {
        if view.actor != Some(view.seat)
            || view.legal.is_none()
            || view.config != self.base.config()
            || tables.sha256 != hu20_trainer::cards::EQUITY_K50_SHA256
        {
            return Err("composition requires matching acting-seat observation/K50".into());
        }
        let decision = multi_holdem::observation_decision(view, tables);
        let selection = select(&self.base, &self.donor, &decision)?;
        let choices = multi_holdem::menu(view);
        // Exactly the existing Policy::choose sampler: one draw per decision,
        // same accumulation order and last-positive rounding fallback.
        let draw: f64 = self.rng.gen();
        let mut sum = 0.;
        let mut chosen = selection
            .probabilities
            .iter()
            .rposition(|&v| v > 0.)
            .ok_or("empty composition support")?;
        for (i, v) in selection.probabilities.iter().enumerate() {
            sum += v;
            if draw < sum {
                chosen = i;
                break;
            }
        }
        Ok((choices[chosen].1, selection))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use flate2::{write::GzEncoder, Compression};
    use hu20_trainer::{multi_checkpoint::key_hex, multi_policy::Row};
    use std::io::Write;
    fn table() -> PolicyTable {
        let file = std::env::temp_dir().join(format!(
            "composition-{}-{}.gz",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let mut out = GzEncoder::new(Vec::new(), Compression::default());
        let identity = json!({"players":6,"stacks":vec![10000;6],"small_blind":50,"big_blind":100,"schema":multi_holdem::SCHEMA,"menu":multi_holdem::MENU,"game":"nlhe-cash","utility_unit":"big-blind","card_tables":hu20_trainer::cards::EQUITY_K50_SHA256});
        writeln!(out,"{}",json!({"format":"nplayer-policy-v1","identity":identity,"players":6,"entries":1,"strategy":"average","last_average_street":3,"continuation":"none","missing":"uniform","source_checkpoint_sha256":"a".repeat(64)})).unwrap();
        writeln!(out, "{}", json!([key_hex(&[1; 16]), 0, 0, 5, [0.5, 0.5]])).unwrap();
        std::fs::write(&file, out.finish().unwrap()).unwrap();
        let table = PolicyTable::load(&file, &hu20_trainer::export::sha256_file(&file)).unwrap();
        std::fs::remove_file(file).unwrap();
        table
    }
    fn set(t: &mut PolicyTable, kind: usize) {
        let hu20_trainer::multi_policy::Rows::Json(rows) = &mut t.rows else {
            panic!()
        };
        rows.clear();
        if kind != 2 {
            rows.insert(
                [1; 16],
                Row {
                    owner: 0,
                    street: 0,
                    code: 5,
                    probabilities: if kind == 0 {
                        vec![0.75, 0.25]
                    } else {
                        vec![0.5, 0.5]
                    }
                    .into_boxed_slice(),
                    original_average_mass: Some(kind == 0),
                },
            );
        }
    }
    fn decision() -> Decision {
        Decision {
            key: [1; 16],
            actor: 0,
            owner: 0,
            street: 0,
            code: 5,
        }
    }
    #[test]
    fn all_nine_presence_mass_combinations_preserve_base_precedence() {
        let mut base = table();
        let mut donor = table();
        let d = decision();
        for b in 0..3 {
            for a in 0..3 {
                set(&mut base, b);
                set(&mut donor, a);
                let s = select(&base, &donor, &d).unwrap();
                if b < 2 {
                    assert_eq!(s.source, "base");
                    assert_eq!(s.base_status, mass::LABELS[b]);
                    assert_eq!(s.donor_status, "not_queried");
                    assert_eq!(
                        s.probabilities,
                        base.rows.get(&d.key).unwrap().probabilities
                    );
                } else if a == 0 {
                    assert_eq!(s.source, "donor");
                    assert_eq!(s.probabilities, [0.75, 0.25]);
                } else {
                    assert_eq!(s.source, "uniform");
                    assert_eq!(s.status, "missing");
                    assert_eq!(s.probabilities, [0.5, 0.5]);
                }
            }
        }
    }
    #[test]
    fn positive_uniform_is_learned_but_zero_uniform_is_not() {
        let mut base = table();
        let mut donor = table();
        set(&mut base, 2);
        set(&mut donor, 1);
        assert_eq!(
            select(&base, &donor, &decision()).unwrap().source,
            "uniform"
        );
        donor.rows.tag_mass(&[1; 16], true).unwrap();
        assert_eq!(select(&base, &donor, &decision()).unwrap().source, "donor");
    }
    #[test]
    fn wrong_identity_unknown_mass_and_nonuniform_zero_fail_closed() {
        let mut base = table();
        let donor = table();
        set(&mut base, 0);
        let mut d = decision();
        d.code = 7;
        assert!(select(&base, &donor, &d).is_err());
        let hu20_trainer::multi_policy::Rows::Json(rows) = &mut base.rows else {
            panic!()
        };
        rows.get_mut(&[1; 16]).unwrap().original_average_mass = None;
        assert!(select(&base, &donor, &decision()).is_err());
        base.rows.tag_mass(&[1; 16], false).unwrap();
        assert!(select(&base, &donor, &decision()).is_err());
    }
    #[test]
    fn incompatible_schema_and_average_scope_refuse() {
        let base = table();
        let mut donor = table();
        assert!(compatible(&base, &donor).is_ok());
        donor.scope = 2;
        assert!(compatible(&base, &donor).is_err());
        donor.scope = 3;
        donor.identity["schema"] = json!("different");
        assert!(compatible(&base, &donor).is_err());
    }
}
