//! Frozen-policy diagnostic only. Nothing here is called by the trainer.
use hu20_trainer::{
    cfr::{fsum, Key},
    multi_cfr::{child_path, Decision, State, Table},
    multi_checkpoint::key_hex,
};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};

pub fn product(a: f64, b: f64) -> Result<f64, String> {
    if !a.is_finite() || !b.is_finite() {
        return Err("nonfinite factor".into());
    }
    let v = a * b;
    if !v.is_finite() {
        return Err("product overflow".into());
    }
    if a != 0. && b != 0. && v == 0. {
        return Err("positive-magnitude product underflow".into());
    }
    Ok(v)
}

#[derive(Clone, Default, Debug)]
pub struct Moments {
    pub count: u64,
    pub zero: u64,
    pub sum: f64,
    pub squares: f64,
    pub max: f64,
}
impl Moments {
    pub fn add(&mut self, w: f64) -> Result<(), String> {
        if !w.is_finite() || w < 0. {
            return Err("importance coefficient must be finite and nonnegative".into());
        }
        self.count += 1;
        self.zero += u64::from(w == 0.);
        self.sum += w;
        self.squares += product(w, w)?;
        self.max = self.max.max(w);
        if !self.sum.is_finite() || !self.squares.is_finite() {
            return Err("weight accumulator overflow".into());
        }
        Ok(())
    }
    pub fn merge(&mut self, other: &Self) -> Result<(), String> {
        self.count += other.count;
        self.zero += other.zero;
        self.sum += other.sum;
        self.squares += other.squares;
        self.max = self.max.max(other.max);
        if !self.sum.is_finite() || !self.squares.is_finite() {
            return Err("weight accumulator overflow".into());
        }
        Ok(())
    }
    pub fn ess(&self) -> f64 {
        if self.squares == 0. {
            0.
        } else {
            (self.sum / self.squares.sqrt()).powi(2)
        }
    }
    pub fn value(&self) -> Value {
        json!({"events":self.count,"exact_zero":self.zero,"sum":self.sum,"sum_squares":self.squares,"max":self.max,"ess":self.ess()})
    }
}

pub fn passive_index(d: Decision) -> Result<usize, String> {
    let label = if d.code & (1 << 1) != 0 {
        1
    } else if d.code & (1 << 2) != 0 {
        2
    } else {
        return Err("no legal check/call label".into());
    };
    Ok((d.code & ((1 << label) - 1)).count_ones() as usize)
}
pub fn frozen_sigma(table: &Table, d: Decision) -> Result<Vec<f64>, String> {
    let Some(entry) = table.get(&d.key) else {
        return Ok(vec![1. / d.len() as f64; d.len()]);
    };
    entry.check(d);
    let sigma = entry.policy(false)[..d.len()].to_vec();
    if entry.regrets.iter().any(|r| !r.is_finite())
        || sigma.iter().any(|p| !p.is_finite() || *p < 0.)
        || (fsum(sigma.iter().copied()) - 1.).abs() > 1e-12
    {
        return Err("nonfinite or invalid warmed current policy".into());
    }
    if entry
        .regrets
        .iter()
        .zip(&sigma)
        .any(|(r, p)| *r > 0. && *p == 0.)
    {
        return Err("current-policy normalization underflow; not exact zero reach".into());
    }
    Ok(sigma)
}
pub fn proposal(sigma: &[f64], passive: usize, biased: bool) -> Result<Vec<f64>, String> {
    if passive >= sigma.len()
        || sigma.is_empty()
        || sigma.iter().any(|p| !p.is_finite() || *p < 0.)
        || (fsum(sigma.iter().copied()) - 1.).abs() > 1e-12
    {
        return Err("invalid policy or passive index".into());
    }
    sigma
        .iter()
        .enumerate()
        .map(|(a, p)| {
            if biased {
                Ok(product(0.75, *p)? + if a == passive { 0.25 } else { 0. })
            } else {
                Ok(*p)
            }
        })
        .collect()
}

#[derive(Clone, Debug)]
pub struct Increment {
    pub key: Key,
    pub owner: usize,
    pub street: usize,
    pub code: u16,
    pub family: String,
    pub missing: bool,
    pub regret: Vec<f64>,
    pub average: Vec<f64>,
    pub regret_coeff: Moments,
    pub average_coeff: Moments,
    pub regret_linear_coeff: Moments,
    pub average_linear_coeff: Moments,
}
impl Increment {
    fn new(d: Decision, family: String, missing: bool) -> Self {
        Self {
            key: d.key,
            owner: d.owner,
            street: d.street,
            code: d.code,
            family,
            missing,
            regret: vec![0.; d.len()],
            average: vec![0.; d.len()],
            regret_coeff: Moments::default(),
            average_coeff: Moments::default(),
            regret_linear_coeff: Moments::default(),
            average_linear_coeff: Moments::default(),
        }
    }
    pub fn value(&self) -> Value {
        json!({"key":key_hex(&self.key),"owner":self.owner,"street":self.street,"code":self.code,"family":self.family,"missing":self.missing,
            "regret":self.regret,"average":self.average,"regret_coeff":self.regret_coeff.value(),"average_coeff":self.average_coeff.value(),
            "regret_linear_coeff":self.regret_linear_coeff.value(),"average_linear_coeff":self.average_linear_coeff.value()})
    }
}

#[derive(Default)]
pub struct Root {
    pub value: f64,
    pub nodes: u64,
    pub increments: BTreeMap<Key, Increment>,
    pub metrics: BTreeMap<String, Moments>,
    pub first_zero: Vec<Value>,
}
impl Root {
    fn metric(&mut self, name: String, weight: f64) -> Result<(), String> {
        self.metrics.entry(name).or_default().add(weight)
    }
    pub fn value(&self) -> Value {
        json!({"estimated_root_value":self.value,"nodes":self.nodes,
            "increments":self.increments.values().map(Increment::value).collect::<Vec<_>>(),
            "metrics":self.metrics.iter().map(|(k,v)|(k.clone(),v.value())).collect::<BTreeMap<_,_>>(),"first_zero":self.first_zero})
    }
}

struct Walk<'a, D, F> {
    table: &'a Table,
    traverser: usize,
    biased: bool,
    linear: f64,
    draw: &'a mut D,
    family: &'a F,
    root: Root,
}
impl<D, F> Walk<'_, D, F> {
    fn visit<S>(&mut self, s: &mut S, path: u64, prefix: f64, own: f64) -> Result<f64, String>
    where
        S: State,
        D: FnMut(&[f64], u64) -> usize,
        F: Fn(&S, usize) -> String,
    {
        self.root.nodes += 1;
        let Some(d) = s.decision() else {
            self.root
                .metric("terminal_counterfactual_coefficient".into(), prefix)?;
            self.root.metric(
                "terminal_root_value_coefficient_with_own_reach".into(),
                product(prefix, own)?,
            )?;
            let u = s.payoff(self.traverser);
            if !u.is_finite() {
                return Err("nonfinite payoff".into());
            }
            return Ok(u);
        };
        let stored = self.table.get(&d.key);
        let sigma = frozen_sigma(self.table, d)?;
        // Family belongs to the information-set owner, not to whichever seat
        // happens to be the current CFR traverser in this root.
        let family = (self.family)(s, d.actor);
        self.root
            .metric(format!("street{}:{family}:update_prefix", d.street), prefix)?;
        self.root.metric(
            format!("street{}:{family}:linear_update_prefix", d.street),
            product(prefix, self.linear)?,
        )?;
        let inc = self
            .root
            .increments
            .entry(d.key)
            .or_insert_with(|| Increment::new(d, family.clone(), stored.is_none()));
        if (inc.owner, inc.street, inc.code) != (d.owner, d.street, d.code) || inc.family != family
        {
            return Err("key metadata changed".into());
        }
        if d.actor != self.traverser {
            inc.average_coeff.add(prefix)?;
            inc.average_linear_coeff
                .add(product(prefix, self.linear)?)?;
            for (a, p) in sigma.iter().enumerate() {
                inc.average[a] += product(product(prefix, self.linear)?, *p)?;
            }
            let q = proposal(&sigma, passive_index(d)?, self.biased)?;
            let a = (self.draw)(&q, path);
            if a >= q.len() || q[a] <= 0. {
                return Err("sampled outside proposal support".into());
            }
            let ratio = sigma[a] / q[a];
            self.root
                .metric(format!("street{}:{family}:action_ratio", d.street), ratio)?;
            if ratio == 0. && self.root.first_zero.len() < 8 {
                self.root.first_zero.push(
                    json!({"path":path,"key":key_hex(&d.key),"actor":d.actor,"street":d.street,
                    "action":a,"sigma":sigma[a],"q":q[a],"prefix_before":prefix}),
                );
            }
            let next_prefix = product(prefix, ratio)?;
            let saved = s.save();
            s.apply(a);
            let child = self.visit(s, child_path(path, a), next_prefix, own);
            s.restore(saved);
            return product(ratio, child?);
        }
        let mut values = Vec::with_capacity(d.len());
        for (a, p) in sigma.iter().enumerate() {
            let next_own = product(own, *p)?;
            let saved = s.save();
            s.apply(a);
            let child = self.visit(s, child_path(path, a), prefix, next_own);
            s.restore(saved);
            values.push(child?);
        }
        let terms = values
            .iter()
            .zip(&sigma)
            .map(|(v, p)| product(*v, *p))
            .collect::<Result<Vec<_>, _>>()?;
        let value = fsum(terms.into_iter());
        self.root.metric(
            format!(
                "street{}:{family}:all_estimated_action_values_tied",
                d.street
            ),
            if values.iter().all(|v| *v == values[0]) {
                1.
            } else {
                0.
            },
        )?;
        let inc = self.root.increments.get_mut(&d.key).unwrap();
        inc.regret_coeff.add(prefix)?;
        inc.regret_linear_coeff.add(product(prefix, self.linear)?)?;
        for (a, v) in values.iter().enumerate() {
            inc.regret[a] += product(product(prefix, self.linear)?, v - value)?;
        }
        if inc
            .regret
            .iter()
            .chain(&inc.average)
            .any(|v| !v.is_finite())
        {
            return Err("nonfinite update".into());
        }
        Ok(value)
    }
}

pub fn run<S, D, F>(
    table: &Table,
    state: &mut S,
    traverser: usize,
    biased: bool,
    linear: f64,
    draw: &mut D,
    family: &F,
) -> Result<Root, String>
where
    S: State,
    D: FnMut(&[f64], u64) -> usize,
    F: Fn(&S, usize) -> String,
{
    if traverser >= state.players() || !linear.is_finite() || linear <= 0. {
        return Err("invalid root metadata".into());
    }
    let mut walk = Walk {
        table,
        traverser,
        biased,
        linear,
        draw,
        family,
        root: Root::default(),
    };
    let v = walk.visit(state, 0, 1., 1.)?;
    walk.root.value = v;
    Ok(walk.root)
}

#[derive(Default, Clone)]
pub struct Learning {
    regret: Vec<f64>,
    average: Vec<f64>,
    average_roots: Moments,
    regret_roots: Moments,
    average_linear_roots: Moments,
    regret_linear_roots: Moments,
    pub roots: u64,
    pub average_positive_roots: u64,
    pub regret_nonzero_roots: u64,
}
impl Learning {
    fn add(&mut self, i: &Increment) -> Result<(), String> {
        if self.regret.is_empty() {
            self.regret = vec![0.; i.regret.len()];
            self.average = vec![0.; i.average.len()];
        }
        if self.regret.len() != i.regret.len() {
            return Err("row action count changed".into());
        }
        for (a, v) in i.regret.iter().enumerate() {
            self.regret[a] += v;
            self.average[a] += i.average[a];
        }
        let reg = i.regret.iter().any(|v| *v != 0.);
        let avg = i.average.iter().any(|v| *v > 0.);
        self.roots += 1;
        self.average_positive_roots += u64::from(avg);
        self.regret_nonzero_roots += u64::from(reg);
        self.average_roots
            .add(if avg { i.average_coeff.sum } else { 0. })?;
        self.regret_roots
            .add(if reg { i.regret_coeff.sum } else { 0. })?;
        self.average_linear_roots
            .add(if avg { i.average_linear_coeff.sum } else { 0. })?;
        self.regret_linear_roots
            .add(if reg { i.regret_linear_coeff.sum } else { 0. })?;
        if self
            .regret
            .iter()
            .chain(&self.average)
            .any(|v| !v.is_finite())
        {
            return Err("row accumulator overflow".into());
        }
        Ok(())
    }
    pub fn zero(&self) -> bool {
        self.regret.iter().chain(&self.average).all(|v| *v == 0.)
    }
    pub fn replicated(&self) -> bool {
        self.average.iter().any(|v| *v > 0.)
            && self.regret.iter().any(|v| *v != 0.)
            && self.average_positive_roots >= 4
            && self.regret_nonzero_roots >= 4
            && self.average_roots.ess() >= 4.
            && self.regret_roots.ess() >= 4.
    }
    fn value(&self) -> Value {
        json!({"regret":self.regret,"average":self.average,"roots_seen":self.roots,
        "positive_average_roots":self.average_positive_roots,"nonzero_regret_roots":self.regret_nonzero_roots,
        "average_root_coeff":self.average_roots.value(),"regret_root_coeff":self.regret_roots.value(),
        "average_linear_root_coeff":self.average_linear_roots.value(),"regret_linear_root_coeff":self.regret_linear_roots.value(),
        "zero_update":self.zero(),"replicated_positive_learning_proxy":self.replicated()})
    }
}
pub struct Row {
    street: usize,
    family: String,
    pub admitted: Option<u64>,
    pub first_batch: Option<u64>,
    zero_at_admission: bool,
    pub potential: Learning,
    pub retained: Learning,
    discarded_roots: u64,
}
impl Row {
    fn new(street: usize, family: String) -> Self {
        Self {
            street,
            family,
            admitted: None,
            first_batch: None,
            zero_at_admission: false,
            potential: Learning::default(),
            retained: Learning::default(),
            discarded_roots: 0,
        }
    }
    pub fn value(&self, key: &Key) -> Value {
        json!({"key":key_hex(key),"street":self.street,"family":self.family,"first_batch":self.first_batch,
        "admitted_batch":self.admitted,"zero_at_admission":self.zero_at_admission,"discarded_roots":self.discarded_roots,
        "potential":self.potential.value(),"retained":self.retained.value()})
    }
}
pub struct Shadow {
    pub rows: BTreeMap<Key, Row>,
    watched: BTreeSet<Key>,
    admitted: usize,
    cap: usize,
    pub frozen: Option<u64>,
    pub batches: u64,
    pub nodes: u64,
    pub roots: u64,
    discarded_key_batches: u64,
    pub metrics: BTreeMap<String, Moments>,
    pub freeze_snapshot: Option<Value>,
}
impl Shadow {
    pub fn new(cap: usize, watch: &BTreeMap<Key, usize>) -> Result<Self, String> {
        if cap == 0 {
            return Err("zero shadow cap".into());
        }
        Ok(Self {
            rows: watch
                .iter()
                .map(|(k, s)| (*k, Row::new(*s, "watched-never-encountered".into())))
                .collect(),
            watched: watch.keys().copied().collect(),
            admitted: 0,
            cap,
            frozen: None,
            batches: 0,
            nodes: 0,
            roots: 0,
            discarded_key_batches: 0,
            metrics: BTreeMap::new(),
            freeze_snapshot: None,
        })
    }
    pub fn batch(&mut self, roots: &[Root]) -> Result<(), String> {
        self.batches += 1;
        let mut discarded = BTreeSet::new();
        let mut newly_admitted = BTreeSet::new();
        let initially_frozen = self.frozen.is_some();
        for root in roots {
            self.roots += 1;
            self.nodes += root.nodes;
            for (key, v) in &root.metrics {
                self.metrics.entry(key.clone()).or_default().merge(v)?;
            }
            for (key, i) in &root.increments {
                if !i.missing {
                    continue;
                }
                let already = self.rows.get(key).is_some_and(|r| r.admitted.is_some());
                let admit = !initially_frozen || already;
                if !admit {
                    discarded.insert(*key);
                    for (label, flag) in [
                        (
                            "positive_coefficient",
                            i.regret_coeff.sum > 0. || i.average_coeff.sum > 0.,
                        ),
                        ("nonzero_regret_update", i.regret.iter().any(|v| *v != 0.)),
                        ("positive_average_update", i.average.iter().any(|v| *v > 0.)),
                    ] {
                        self.metrics
                            .entry(format!(
                                "discarded_root_key_event:street{}:{}:{label}",
                                i.street, i.family
                            ))
                            .or_default()
                            .add(if flag { 1. } else { 0. })?;
                    }
                }
                if !admit && !self.watched.contains(key) {
                    continue;
                }
                let row = self
                    .rows
                    .entry(*key)
                    .or_insert_with(|| Row::new(i.street, i.family.clone()));
                if row.street != i.street {
                    return Err("watch key street differs".into());
                }
                if row.first_batch.is_none() {
                    row.first_batch = Some(self.batches);
                    row.family = i.family.clone();
                } else if row.family != i.family {
                    return Err("history family changed for the same key".into());
                }
                row.potential.add(i)?;
                if admit {
                    if row.admitted.is_none() {
                        row.admitted = Some(self.batches);
                        self.admitted += 1;
                        newly_admitted.insert(*key);
                    }
                    row.retained.add(i)?;
                } else {
                    row.discarded_roots += 1;
                }
            }
        }
        // Production combines every root delta before inserting an iteration's
        // rows. A zero first-root delta is not a zero-at-admission row when a
        // later root in the same batch supplies positive evidence.
        for key in newly_admitted {
            let row = self.rows.get_mut(&key).unwrap();
            row.zero_at_admission = row.retained.zero();
        }
        self.discarded_key_batches += discarded.len() as u64;
        if self.frozen.is_none() && self.admitted >= self.cap {
            self.frozen = Some(self.batches);
            self.freeze_snapshot = Some(self.summary());
        }
        Ok(())
    }
    pub fn summary(&self) -> Value {
        let admitted = self
            .rows
            .values()
            .filter(|r| r.admitted.is_some())
            .collect::<Vec<_>>();
        let by_street=(0..4).map(|s|json!({"street":s,"admitted":admitted.iter().filter(|r|r.street==s).count(),
            "zero_end":admitted.iter().filter(|r|r.street==s&&r.retained.zero()).count(),
            "replicated_positive_learning_proxy":admitted.iter().filter(|r|r.street==s&&r.retained.replicated()).count(),
            "watched_admitted_replicated":self.rows.iter().filter(|(k,r)|self.watched.contains(*k)&&r.street==s&&r.admitted.is_some()&&r.retained.replicated()).count(),
            "watched_potential_replicated_but_discarded":self.rows.iter().filter(|(k,r)|self.watched.contains(*k)&&r.street==s&&r.admitted.is_none()&&r.potential.replicated()).count(),
            "watched_never_encountered":self.rows.iter().filter(|(k,r)|self.watched.contains(*k)&&r.street==s&&r.first_batch.is_none()).count()})).collect::<Vec<_>>();
        let groups=self.rows.values().map(|r|(r.street,r.family.clone())).collect::<BTreeSet<_>>().into_iter().map(|(street,family)|{
            let rows=self.rows.values().filter(|r|r.street==street&&r.family==family).collect::<Vec<_>>();
            json!({"street":street,"family":family,"tracked_keys":rows.len(),"admitted":rows.iter().filter(|r|r.admitted.is_some()).count(),
                "zero_at_end":rows.iter().filter(|r|r.admitted.is_some()&&r.retained.zero()).count(),
                "replicated_positive_learning_proxy":rows.iter().filter(|r|r.admitted.is_some()&&r.retained.replicated()).count()})
        }).collect::<Vec<_>>();
        json!({"batches":self.batches,"roots":self.roots,"nodes":self.nodes,"shadow_cap":self.cap,"admitted":self.admitted,"frozen_batch":self.frozen,
            "whole_batch_overshoot":self.admitted.saturating_sub(self.cap),"zero_end":admitted.iter().filter(|r|r.retained.zero()).count(),
            "zero_at_admission":admitted.iter().filter(|r|r.zero_at_admission).count(),
            "zero_at_admission_later_positive":admitted.iter().filter(|r|r.zero_at_admission&&!r.retained.zero()).count(),
            "discarded_key_batches_not_unique_keys":self.discarded_key_batches,"by_street":by_street,"by_street_family":groups,
            "metrics":self.metrics.iter().map(|(k,v)|(k.clone(),v.value())).collect::<BTreeMap<_,_>>()})
    }
}
