//! Experimental, frozen-policy value estimation. This module is not called by training or play.
//! The critic combines simulated seats' information and must remain behind this boundary.
use crate::{
    cards::EquityTables,
    multi_holdem::menu,
    nplayer::{Config, Hand},
    policy_features as features,
    policy_network::Fast,
};
use rand::{seq::SliceRandom, Rng, SeedableRng};
use serde_json::{json, Value};

pub const INPUTS: usize = 670;
pub const HIDDEN: usize = 64;

/// An action-dependent control variate. Arbitrary fixed baselines preserve expectation when
/// q has full support over p; unsupported target actions are an error, never silently clipped.
pub fn corrected(p: &[f64], q: &[f64], b: &[f64], sampled: usize, y: f64) -> Result<f64, String> {
    if p.is_empty()
        || p.len() != q.len()
        || p.len() != b.len()
        || sampled >= p.len()
        || !y.is_finite()
        || p.iter().chain(q).chain(b).any(|v| !v.is_finite())
        || p.iter().chain(q).any(|&v| v < 0.)
        || (p.iter().sum::<f64>() - 1.).abs() > 1e-8
        || (q.iter().sum::<f64>() - 1.).abs() > 1e-8
        || p.iter().zip(q).any(|(&p, &q)| p > 0. && q == 0.)
        || q[sampled] == 0.
    {
        return Err("invalid importance-sampling distribution/value".into());
    }
    let v = p.iter().zip(b).map(|(p, b)| p * b).sum::<f64>()
        + p[sampled] / q[sampled] * (y - b[sampled]);
    if !v.is_finite() {
        return Err("nonfinite corrected value".into());
    }
    Ok(v)
}

/// Separate file format: these privileged critic weights cannot be loaded as a playing policy.
pub struct Critic {
    w: Vec<f32>,
    b: Vec<f32>,
    v: Vec<f32>,
    c: Vec<f32>,
}
impl Critic {
    pub fn zero() -> Self {
        Self {
            w: vec![0.; INPUTS * HIDDEN],
            b: vec![0.; HIDDEN],
            v: vec![0.; HIDDEN * 6],
            c: vec![0.; 6],
        }
    }
    pub fn load(path: &std::path::Path) -> Result<Self, String> {
        let j: Value = serde_json::from_slice(&std::fs::read(path).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
        if j["format"] != "variance-probe-critic-v1"
            || j["inputs"] != INPUTS
            || j["hidden"] != HIDDEN
            || j["policy_layout"] != features::layout_sha256()
        {
            return Err("critic schema".into());
        }
        fn take(j: &Value, key: &str, count: usize) -> Result<Vec<f32>, String> {
            let a = j[key].as_array().ok_or("critic array")?;
            if a.len() != count {
                return Err("critic shape".into());
            }
            a.iter()
                .map(|x| {
                    let v = x.as_f64().ok_or("critic number")? as f32;
                    if v.is_finite() {
                        Ok(v)
                    } else {
                        Err("critic nonfinite".into())
                    }
                })
                .collect()
        }
        Ok(Self {
            w: take(&j, "w", INPUTS * HIDDEN)?,
            b: take(&j, "b", HIDDEN)?,
            v: take(&j, "v", HIDDEN * 6)?,
            c: take(&j, "c", 6)?,
        })
    }
    pub fn predict(&self, x: &[u8]) -> [f64; 6] {
        assert_eq!(x.len(), INPUTS);
        let mut h = [0f32; HIDDEN];
        h.copy_from_slice(&self.b);
        // Input-major loops skip the many zeros without changing each output's summation order.
        for (i, &x) in x.iter().enumerate() {
            if x != 0 {
                let x = x as f32 / 255.;
                for (k, h) in h.iter_mut().enumerate() {
                    *h += self.w[k * INPUTS + i] * x;
                }
            }
        }
        let mut out = [0.; 6];
        for (a, out) in out.iter_mut().enumerate() {
            let mut y = self.c[a];
            for (k, &h) in h.iter().enumerate() {
                y += self.v[a * HIDDEN + k] * h.max(0.);
            }
            *out = y as f64 * 100.;
        }
        out
    }
}

pub fn critic_features(
    hand: &Hand,
    focal: usize,
    tables: Option<&EquityTables>,
) -> Result<Vec<u8>, String> {
    let actor = hand.actor().ok_or("critic at terminal")?;
    let view = hand.observe(actor)?;
    let mut x = features::quantize(&features::encode(&view, tables)?);
    let focal_view = hand.observe(focal)?;
    for c in 0..52 {
        x.push(if focal_view.hole.contains(&c) { 255 } else { 0 });
    }
    let slot = features::slot(&focal_view, focal);
    for s in 0..6 {
        x.push(if slot == s { 255 } else { 0 });
    }
    if x.len() != INPUTS {
        return Err("critic feature count".into());
    }
    Ok(x)
}

pub struct Sampler<'a> {
    pub net: &'a Fast,
    pub tables: &'a EquityTables,
    pub critic: Option<&'a Critic>,
    scratch: [Vec<f32>; 2],
    pub nodes: u64,
    pub calls: u64,
}
impl<'a> Sampler<'a> {
    pub fn new(net: &'a Fast, tables: &'a EquityTables, critic: Option<&'a Critic>) -> Self {
        Self {
            net,
            tables,
            critic,
            scratch: [Vec::new(), Vec::new()],
            nodes: 0,
            calls: 0,
        }
    }
    pub fn strategy(&mut self, h: &Hand) -> Result<[f64; 6], String> {
        let view = h.observe(h.actor().ok_or("strategy at terminal")?)?;
        let x = features::quantize(&features::encode(&view, Some(self.tables))?);
        Ok(self
            .net
            .strategy(&x, features::legal_mask(&view), &mut self.scratch))
    }
    pub fn pick(p: &[f64; 6], rng: &mut impl Rng) -> usize {
        let u = rng.gen::<f64>();
        let mut sum = 0.;
        let mut last = 0;
        for (i, &p) in p.iter().enumerate() {
            if p > 0. {
                last = i;
                sum += p;
                if u < sum {
                    return i;
                }
            }
        }
        last
    }
    fn terminal(h: &Hand, focal: usize) -> Option<f64> {
        h.settlement()
            .map(|s| s.rewards[focal] as f64 / h.config().big_blind() as f64)
    }
    /// Plain rollouts supply training labels only. They never train the frozen actor network.
    pub fn rollout(
        &mut self,
        h: &mut Hand,
        focal: usize,
        rng: &mut impl Rng,
        records: &mut Vec<(Vec<u8>, usize)>,
    ) -> Result<f64, String> {
        for _ in 0..256 {
            self.nodes += 1;
            if let Some(y) = Self::terminal(h, focal) {
                return Ok(y);
            }
            let p = self.strategy(h)?;
            let a = Self::pick(&p, rng);
            if h.actor() != Some(focal) {
                records.push((critic_features(h, focal, Some(self.tables))?, a));
            }
            let action = menu(&h.observe(h.actor().unwrap())?)
                .into_iter()
                .find(|(l, _)| *l as usize == a)
                .ok_or("sample off menu")?
                .1;
            h.apply_mut(action)?;
        }
        Err("rollout decision cap".into())
    }
    fn value(
        &mut self,
        h: &mut Hand,
        focal: usize,
        rng: &mut impl Rng,
        mut counts: [u8; 4],
        depth: u8,
    ) -> Result<f64, String> {
        self.nodes += 1;
        if self.nodes > 2_000_000 {
            return Err("estimate node cap".into());
        }
        if let Some(y) = Self::terminal(h, focal) {
            return Ok(y);
        }
        let actor = h.actor().unwrap();
        let street = h.street() as usize;
        let p = self.strategy(h)?;
        let choices = menu(&h.observe(actor)?);
        if actor == focal && counts[street] < 3 && depth < 8 {
            counts[street] += 1;
            let mut v = 0.;
            // Explore zero-probability actions too, as external sampling does, preserving RNG
            // consumption and computational cost across the control and corrected arms.
            for (a, action) in choices {
                let saved = h.save();
                h.apply_mut(action)?;
                let y = self.value(h, focal, rng, counts, depth + 1)?;
                h.restore(saved);
                v += p[a as usize] * y;
            }
            return Ok(v);
        }
        let a = Self::pick(&p, rng);
        let b = if actor != focal {
            if let Some(c) = self.critic {
                self.calls += 1;
                Some(c.predict(&critic_features(h, focal, Some(self.tables))?))
            } else {
                None
            }
        } else {
            None
        };
        let action = choices
            .into_iter()
            .find(|(l, _)| *l as usize == a)
            .ok_or("sample off menu")?
            .1;
        let saved = h.save();
        h.apply_mut(action)?;
        let y = self.value(h, focal, rng, counts, depth)?;
        h.restore(saved);
        if let Some(b) = b {
            corrected(&p, &p, &b, a, y)
        } else {
            Ok(y)
        }
    }
    pub fn advantages(&mut self, root: &Hand, seed: u64) -> Result<([f64; 6], u8), String> {
        self.nodes = 0;
        self.calls = 0;
        let mut h = root.clone();
        let focal = h.actor().ok_or("terminal root")?;
        let p = self.strategy(&h)?;
        let choices = menu(&h.observe(focal)?);
        let mask = features::legal_mask(&h.observe(focal)?);
        let mut rng = rand::rngs::StdRng::seed_from_u64(seed);
        let mut counts = [0; 4];
        counts[h.street() as usize] = 1;
        let mut v = [0.; 6];
        for (a, action) in choices {
            let saved = h.save();
            h.apply_mut(action)?;
            v[a as usize] = self.value(&mut h, focal, &mut rng, counts, 1)?;
            h.restore(saved);
        }
        let mean: f64 = (0..6).map(|a| p[a] * v[a]).sum();
        for a in 0..6 {
            v[a] = if mask >> a & 1 == 1 { v[a] - mean } else { 0. };
        }
        if v.iter().any(|v| !v.is_finite()) {
            return Err("nonfinite advantage".into());
        }
        Ok((v, mask))
    }
}

pub struct Root {
    pub hand: Hand,
    pub id: String,
    pub candidate: u64,
}
/// First eligible deal, independent of payoffs. Selection fails closed if a stratum cannot fill.
pub fn roots(s: &mut Sampler, seed: u64, per_stratum: usize) -> Result<Vec<Root>, String> {
    let mut out = Vec::new();
    for family in 0..4 {
        for street in 1..4 {
            let n = [3, 4, 6, 6][family];
            let mut found = 0;
            for candidate in 0..20_000u64 {
                let mixed = seed ^ ((family * 4 + street) as u64).wrapping_mul(0x9e3779b97f4a7c15);
                let mut rng = rand::rngs::StdRng::seed_from_u64(mixed.wrapping_add(candidate));
                let mut deck: Vec<u8> = (0..52).collect();
                deck.shuffle(&mut rng);
                let stacks = if family == 3 {
                    vec![500, 10_000, 10_000, 10_000, 10_000, 10_000]
                } else {
                    vec![10_000; n]
                };
                let button = rng.gen_range(0..n);
                let mut h = Hand::from_deck(Config::new(&stacks, 50, 100)?, button, &deck)?;
                for _ in 0..256 {
                    let Some(actor) = h.actor() else { break };
                    if h.street() as usize > street {
                        break;
                    }
                    let choices = menu(&h.observe(actor)?);
                    if h.street() as usize == street && choices.len() >= 2 {
                        out.push(Root {
                            hand: h.clone(),
                            id: format!(
                                "{}-{}-{}",
                                ["3p100", "4p100", "6p100", "6pmix"][family],
                                street,
                                found
                            ),
                            candidate,
                        });
                        found += 1;
                        break;
                    }
                    let p = s.strategy(&h)?;
                    let a = Sampler::pick(&p, &mut rng);
                    h.apply_mut(
                        choices
                            .into_iter()
                            .find(|(l, _)| *l as usize == a)
                            .ok_or("root action")?
                            .1,
                    )?;
                }
                if found == per_stratum {
                    break;
                }
            }
            if found != per_stratum {
                return Err(format!(
                    "root coverage failed family {family} street {street}"
                ));
            }
        }
    }
    Ok(out)
}

pub fn root_receipt(r: &Root) -> Value {
    json!({"id":r.id,"candidate":r.candidate,"players":r.hand.config().players(),
    "street":r.hand.street() as usize,"focal":r.hand.actor(),"board":r.hand.board(),"history":format!("{:?}",r.hand.history())})
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        multi_cfr::State,
        small_games::{Kind, SmallGame},
    };
    #[test]
    fn critic_reads_no_future_cards_and_never_changes_actor_features() {
        let config = Config::new(&[10000; 3], 50, 100).unwrap();
        let mut deck: Vec<u8> = (0..52).collect();
        let h = Hand::from_deck(config, 0, &deck).unwrap();
        deck.swap(40, 41);
        let future = Hand::from_deck(config, 0, &deck).unwrap();
        assert_eq!(
            critic_features(&h, 1, None).unwrap(),
            critic_features(&future, 1, None).unwrap()
        );
        // Seat 1's hole cards occupy deck slots 0/3. Actor 0 cannot see them,
        // while the training-only critic is explicitly allowed focal seat 1's cards.
        deck.swap(0, 40);
        let changed = Hand::from_deck(config, 0, &deck).unwrap();
        assert_eq!(
            features::encode(&h.observe(0).unwrap(), None).unwrap(),
            features::encode(&changed.observe(0).unwrap(), None).unwrap()
        );
        assert_ne!(
            critic_features(&h, 1, None).unwrap(),
            critic_features(&changed, 1, None).unwrap()
        );
    }
    fn exact(h: crate::small_games::Hand, baseline: f64) -> (f64, f64) {
        if h.actor.is_none() {
            return (h.payoff(0), h.payoff(0));
        }
        let choices = h.actions();
        let n = choices.len();
        let p: Vec<f64> = (1..=n)
            .map(|a| a as f64 / (n * (n + 1) / 2) as f64)
            .collect();
        let q = vec![1. / n as f64; n];
        let b: Vec<f64> = (0..n).map(|i| baseline * (i + 1) as f64).collect();
        let mut ev = 0.;
        let mut cv = 0.;
        for (i, &a) in choices.iter().enumerate() {
            let mut child = h;
            child.play(a);
            let (e, c) = exact(child, baseline);
            ev += p[i] * e;
            cv += q[i] * corrected(&p, &q, &b, i, c).unwrap();
        }
        (ev, cv)
    }
    #[test]
    fn exhaustive_kuhn_wrong_baselines_preserve_values_and_regrets() {
        for players in [2, 3] {
            for (h, _) in SmallGame::new(Kind::Kuhn, players).deals() {
                for b in [0., 1., -7., 1000.] {
                    let (e, c) = exact(h, b);
                    assert!((e - c).abs() < 1e-9, "{players} {b} {e} {c}");
                    let mut ev = Vec::new();
                    let mut cv = Vec::new();
                    for a in h.actions() {
                        let mut child = h;
                        child.play(a);
                        let (e, c) = exact(child, b);
                        ev.push(e);
                        cv.push(c);
                    }
                    let n = ev.len();
                    let weights: Vec<f64> = (1..=n)
                        .map(|i| i as f64 / (n * (n + 1) / 2) as f64)
                        .collect();
                    let em = ev.iter().zip(&weights).map(|(v, p)| v * p).sum::<f64>();
                    let cm = cv.iter().zip(&weights).map(|(v, p)| v * p).sum::<f64>();
                    for (e, c) in ev.iter().zip(cv) {
                        assert!((e - em - (c - cm)).abs() < 1e-9);
                    }
                }
            }
        }
    }
    #[test]
    fn support_and_nonfinite_fail_closed() {
        assert!(corrected(&[0.5, 0.5], &[1., 0.], &[1., 2.], 0, 3.).is_err());
        assert!(corrected(&[1., 0.], &[1., 0.], &[0., 0.], 1, 3.).is_err());
        assert!(corrected(&[1.], &[1.], &[f64::NAN], 0, 3.).is_err());
        assert!(corrected(&[1.], &[1.], &[0.], 0, f64::INFINITY).is_err());
        assert_eq!(
            corrected(&[1., 0.], &[1., 0.], &[99., -999.], 0, 3.).unwrap(),
            3.
        );
        assert_eq!(
            corrected(&[0.2, 0.8], &[0.2, 0.8], &[0., 0.], 1, 3.).unwrap(),
            3.
        );
    }
    #[test]
    fn exact_action_baseline_removes_action_sampling_variance() {
        let p = [0.2, 0.8, 0.];
        let q = [0.4, 0.5, 0.1];
        let y = [-7., 13., 99.];
        for a in 0..3 {
            assert!((corrected(&p, &q, &y, a, y[a]).unwrap() - 9.).abs() < 1e-12);
        }
    }
}
