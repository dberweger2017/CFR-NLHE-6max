//! Per-root observations only; this ledger never changes training probabilities or deltas.
use super::{
    coefficients::Moments,
    probe::{Contexts, RootMeta},
};
use hu20_trainer::{
    cfr::{fsum, Key},
    multi_cfr::{Delta, Deltas, Table},
    multi_checkpoint::key_hex,
};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Default)]
struct Evidence {
    roots: u64,
    declined: u64,
    retained: u64,
    regret_roots: u64,
    average_roots: u64,
    path_nonzero_root_cancel: u64,
    regret_raw: Moments,
    regret_linear: Moments,
    average_raw: Moments,
    average_linear: Moments,
    regret_l1: f64,
    average_mass: f64,
    min_nonzero_regret_l1: Option<f64>,
    max_regret_l1: f64,
}
impl Evidence {
    fn add(
        &mut self,
        d: &Delta,
        m: &RootMeta,
        weight: f64,
        epsilon: f64,
        accepted: bool,
    ) -> Result<(), String> {
        self.roots += 1;
        let r = fsum(d.regrets().iter().map(|x| x.abs()));
        let a = fsum(d.average().unwrap().iter().copied());
        if !r.is_finite() || !a.is_finite() || a < 0. {
            return Err("invalid root-aggregated update".into());
        }
        self.path_nonzero_root_cancel += u64::from(m.regret_nonzero_paths > 0 && r == 0.);
        if !accepted {
            self.declined += 1;
            return Ok(());
        }
        self.retained += 1;
        if r > 0. {
            self.regret_roots += 1;
            let c = (1. - epsilon) * m.regret_nonzero_paths as f64;
            self.regret_raw.add(c)?;
            self.regret_linear.add(c * weight)?;
            self.regret_l1 += r;
            self.min_nonzero_regret_l1 = Some(self.min_nonzero_regret_l1.map_or(r, |x| x.min(r)));
            self.max_regret_l1 = self.max_regret_l1.max(r);
        }
        if a > 0. {
            self.average_roots += 1;
            let c = m.average_paths as f64;
            self.average_raw.add(c)?;
            self.average_linear.add(c * weight)?;
            self.average_mass += a;
        }
        if !self.regret_l1.is_finite() || !self.average_mass.is_finite() {
            return Err("watch magnitude overflow".into());
        }
        Ok(())
    }
    pub fn qualifies(&self) -> bool {
        self.regret_roots >= 4
            && self.average_roots >= 4
            && self.regret_raw.ess() >= 4.
            && self.regret_linear.ess() >= 4.
            && self.average_raw.ess() >= 4.
            && self.average_linear.ess() >= 4.
    }
    fn value(&self, total: u64) -> Value {
        json!({"all_root_contexts":total,"encountered_root_groups":self.roots,"retained_root_groups":self.retained,
          "declined_root_groups":self.declined,"retained_nonzero_regret_roots":self.regret_roots,"retained_positive_average_roots":self.average_roots,
          "nonzero_path_but_zero_root_regret_groups":self.path_nonzero_root_cancel,
          "regret_raw_coefficients":self.regret_raw.value(),"regret_linear_coefficients":self.regret_linear.value(),
          "average_raw_coefficients":self.average_raw.value(),"average_linear_coefficients":self.average_linear.value(),
          "retained_root_regret_l1_sum":self.regret_l1,"retained_root_average_mass_sum":self.average_mass,
          "minimum_nonzero_root_regret_l1":self.min_nonzero_regret_l1,"maximum_root_regret_l1":self.max_regret_l1,
          "replicated_learning_proxy":self.qualifies(),
          "coefficient_scope":"Update-gated root-grouped coefficients; absent roots have zero weight. Visits/paths inside a root are correlated. ESS is concentration, not independent sample count."})
    }
}
#[derive(Default)]
pub struct Watch {
    all: Evidence,
    by_family: [Evidence; 5],
    targets: BTreeSet<u8>,
}
impl Watch {
    fn add(
        &mut self,
        d: &Delta,
        m: &RootMeta,
        weight: f64,
        epsilon: f64,
        accepted: bool,
    ) -> Result<(), String> {
        self.all.add(d, m, weight, epsilon, accepted)?;
        let f = if m.families.len() == 1 {
            *m.families.first().unwrap() as usize
        } else {
            4
        };
        self.by_family[f].add(d, m, weight, epsilon, accepted)
    }
    pub fn qualifies(&self) -> bool {
        self.targets
            .iter()
            .any(|f| *f <= 2 && self.by_family[*f as usize].qualifies())
    }
    fn value(&self, total: u64) -> Value {
        let mut v = self.all.value(total);
        v["all_history_key_proxy"] = v["replicated_learning_proxy"].clone();
        v["replicated_learning_proxy"] = json!(self.qualifies());
        let names = ["P0", "P1", "P2", "other", "merged-families"];
        v["by_actual_training_family"] = json!(names
            .iter()
            .enumerate()
            .map(|(i, n)| (*n, self.by_family[i].value(total)))
            .collect::<BTreeMap<_, _>>());
        v["qualifying_target_families"] = json!(self
            .targets
            .iter()
            .filter(|f| **f <= 2 && self.by_family[**f as usize].qualifies())
            .map(|f| names[*f as usize])
            .collect::<Vec<_>>());
        v
    }
}
#[derive(Default)]
struct Cell {
    groups: u64,
    regret_paths: u64,
    zero_regret_paths: u64,
    average_paths: u64,
    nonzero_roots: u64,
    cancelled_roots: u64,
    declined: u64,
    retained_nonzero: u64,
}
pub struct Ledger {
    pub roots: u64,
    pub watches: BTreeMap<Key, Watch>,
    pub watch_meta: BTreeMap<Key, Value>,
    cells: Vec<Vec<Cell>>,
    pub pending_new: BTreeSet<Key>,
    pub admitted: u64,
    pub zero_admission: u64,
    pub initially_zero: BTreeSet<Key>,
    pub zero_at_freeze: Option<u64>,
}
pub fn zero(d: hu20_trainer::multi_cfr::Stored<'_>) -> bool {
    d.regrets.iter().all(|x| *x == 0.) && d.average.is_none_or(|a| a.iter().all(|x| *x == 0.))
}
impl Ledger {
    pub fn new(meta: BTreeMap<Key, Value>) -> Self {
        Self {
            roots: 0,
            watches: meta
                .iter()
                .map(|(k, v)| {
                    (
                        *k,
                        Watch {
                            targets: v["families"]
                                .as_array()
                                .expect("watch families")
                                .iter()
                                .map(|f| u8::try_from(f.as_u64().unwrap()).unwrap())
                                .collect(),
                            ..Watch::default()
                        },
                    )
                })
                .collect(),
            watch_meta: meta,
            cells: (0..4)
                .map(|_| (0..5).map(|_| Cell::default()).collect())
                .collect(),
            pending_new: BTreeSet::new(),
            admitted: 0,
            zero_admission: 0,
            initially_zero: BTreeSet::new(),
            zero_at_freeze: None,
        }
    }
    pub fn observe(
        &mut self,
        w: f64,
        t: &Table,
        ds: &Deltas,
        meta: &Contexts,
        frozen: bool,
        eps: f64,
    ) -> Result<(), String> {
        self.roots += 1;
        for (k, d) in ds {
            let m = meta.get(k).ok_or("missing diagnostic context")?;
            assert_eq!(m.regret_nonzero_paths + m.regret_zero_paths, d.visits);
            let missing = !t.contains_key(k);
            let accepted = !missing || !frozen;
            if missing && !frozen {
                self.pending_new.insert(*k);
            }
            let family = if m.families.len() == 1 {
                *m.families.first().unwrap() as usize
            } else {
                4
            };
            let c = &mut self.cells[d.street as usize][family];
            let nonzero = d.regrets().iter().any(|x| *x != 0.);
            c.groups += 1;
            c.regret_paths += m.regret_nonzero_paths;
            c.zero_regret_paths += m.regret_zero_paths;
            c.average_paths += m.average_paths;
            c.nonzero_roots += u64::from(nonzero);
            c.cancelled_roots += u64::from(m.regret_nonzero_paths > 0 && !nonzero);
            c.declined += u64::from(!accepted);
            c.retained_nonzero += u64::from(accepted && nonzero);
            if let Some(watch) = self.watches.get_mut(k) {
                watch.add(d, m, w, eps, accepted)?;
            }
        }
        Ok(())
    }
    pub fn after_merge(&mut self, t: &Table, frozen: bool) {
        for k in std::mem::take(&mut self.pending_new) {
            let d = t.get(&k).expect("pre-freeze whole-iteration admission");
            self.admitted += 1;
            if zero(d) {
                self.zero_admission += 1;
                self.initially_zero.insert(k);
            }
        }
        if frozen && self.zero_at_freeze.is_none() {
            self.zero_at_freeze = Some(t.values().filter(|d| zero(*d)).count() as u64);
        }
    }
    pub fn value(&self, t: &Table) -> Value {
        let mut cells = Vec::new();
        for (s, families) in self.cells.iter().enumerate() {
            for (f, c) in families.iter().enumerate() {
                cells.push(json!({"street":s,"family":(["P0","P1","P2","other","merged-families"][f]),
              "root_key_groups":c.groups,"nonzero_regret_path_vectors":c.regret_paths,"zero_regret_path_vectors":c.zero_regret_paths,
              "average_path_vectors":c.average_paths,"nonzero_root_regret_vectors":c.nonzero_roots,
              "path_nonzero_root_cancelled":c.cancelled_roots,"declined_root_key_groups":c.declined,"retained_nonzero_root_regret_vectors":c.retained_nonzero}));
            }
        }
        let watches: Vec<_> = self
            .watches
            .iter()
            .map(|(k, w)| {
                let mut v = w.value(self.roots);
                v["key"] = json!(key_hex(k));
                v["public_watch_metadata"] = self.watch_meta[k].clone();
                v["final_retained"] = json!(t.contains_key(k));
                if let Some(d) = t.get(k) {
                    v["final_visits"] = json!(d.visits);
                    v["final_zero"] = json!(zero(d));
                    v["final_average_mass"] = json!(d.average.map(|a| fsum(a.iter().copied())));
                }
                v
            })
            .collect();
        json!({"all_root_contexts":self.roots,"watch_keys":self.watches.len(),"qualified_retained_watch_keys":self.watches.values().filter(|w|w.qualifies()).count(),
          "admitted_rows":self.admitted,"zero_at_admission":self.zero_admission,"zero_at_freeze":self.zero_at_freeze,
          "fully_zero_final_rows":t.values().filter(|d|zero(*d)).count(),
          "initially_zero_later_nonzero":self.initially_zero.iter().filter(|k|t.get(k).is_some_and(|d|!zero(d))).count(),
          "watch":watches,"cells":cells,
          "limits":"Public family labels can merge within a root; merged-families is retained separately. No individual signed-regret ESS. Positive coefficients, numerical path vectors, root cancellation and final row zeros are distinct. This changes target law and is not a strength test."})
    }
}
