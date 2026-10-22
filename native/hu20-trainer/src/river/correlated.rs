//! Exact folded-card removal as a low-rank weighted rank-prefix operator.
//!
//! For disjoint a={x,y}, b={u,v}, removal mass is
//! 1+B(a)+B(b)+F[x,u]+F[x,v]+F[y,u]+F[y,v], where
//! B({x,y})=-single[x]-single[y]+F[x,y]. Prefixes accumulate 54 weighted
//! opponent features. Sparse corrections remove overlapping active hands and
//! repair cancellation near an impossible folded assignment. The dense oracle
//! remains independent. No regret, averaging, or best-response rule changes.
use super::{Game, Holding, Terminal};
use std::sync::atomic::{AtomicU64, Ordering};

const WIDTH: usize = 54;

struct Removal {
    single: [f64; 52],
    pair: [[f64; 52]; 52],
    folded: Vec<(u64, f64)>,
}
impl Removal {
    fn new(board: u64, holdings: Vec<Holding>) -> Result<Self, String> {
        if holdings.is_empty() || holdings.len() > 1081 {
            return Err("folded range size invalid".into());
        }
        let mut seen = std::collections::HashSet::new();
        let mut largest = 0f64;
        for h in &holdings {
            let [a, b] = h.cards;
            if a >= 52 || b >= 52 || a == b || !h.weight.is_finite() || h.weight < 0. {
                return Err("invalid folded holding".into());
            }
            let mask = (1u64 << a) | (1u64 << b);
            if mask & board != 0 || !seen.insert(mask) {
                return Err("blocked or duplicate folded holding".into());
            }
            largest = largest.max(h.weight);
        }
        if largest == 0. {
            return Err("folded range has no mass".into());
        }
        let total: f64 = holdings.iter().map(|h| h.weight / largest).sum();
        let mut out = Self {
            single: [0.; 52],
            pair: [[0.; 52]; 52],
            folded: Vec::new(),
        };
        for h in holdings {
            let [a, b] = h.cards.map(usize::from);
            let w = (h.weight / largest) / total;
            out.single[a] += w;
            out.single[b] += w;
            out.pair[a][b] = w;
            out.pair[b][a] = w;
            if w > 0. {
                out.folded.push(((1u64 << a) | (1u64 << b), w));
            }
        }
        Ok(out)
    }
    fn b(&self, cards: [u8; 2]) -> f64 {
        let [a, b] = cards.map(usize::from);
        -self.single[a] - self.single[b] + self.pair[a][b]
    }
    fn features(&self, cards: [u8; 2]) -> [f64; WIDTH] {
        let [a, b] = cards.map(usize::from);
        let mut f = [0.; WIDTH];
        f[0] = 1.;
        f[1] = self.b(cards);
        for c in 0..52 {
            f[c + 2] = self.pair[c][a] + self.pair[c][b];
        }
        f
    }
    fn scalar(&self, mask: u64) -> f64 {
        self.folded
            .iter()
            .filter(|(m, _)| m & mask == 0)
            .map(|(_, w)| w)
            .sum()
    }
    fn compatible(&self, a: [u8; 2], b: [u8; 2]) -> f64 {
        let f = self.features(b);
        let raw = 1. + self.b(a) + f[1] + f[a[0] as usize + 2] + f[a[1] as usize + 2];
        if raw < 1e-10 {
            self.scalar(a.into_iter().chain(b).fold(0, |m, c| m | (1u64 << c)))
        } else {
            raw
        }
    }
}

pub(super) struct FoldedLaw {
    removal: Removal,
    features: [Vec<[f64; WIDTH]>; 2],
    corrections: [Vec<Vec<(usize, f64)>>; 2],
    positive: [Vec<bool>; 2],
    z: f64,
    scalar_rows: AtomicU64,
}
impl FoldedLaw {
    pub(super) fn new(game: &Game, folded: Vec<Holding>) -> Result<Self, String> {
        let removal = Removal::new(game.board_mask, folded)?;
        let features = std::array::from_fn(|s| {
            game.hands[s]
                .iter()
                .map(|h| removal.features(h.cards))
                .collect::<Vec<_>>()
        });
        let mut corrections: [Vec<Vec<(usize, f64)>>; 2] =
            std::array::from_fn(|s| vec![Vec::new(); game.holdings(s)]);
        let mut positive = std::array::from_fn(|s| vec![false; game.holdings(s)]);
        let mut z = 0.;
        for (i, a) in game.hands[0].iter().enumerate() {
            if a.weight == 0. {
                continue;
            }
            for (j, b) in game.hands[1].iter().enumerate() {
                if b.weight == 0. {
                    continue;
                }
                let c0 = 1.
                    + features[0][i][1]
                    + features[1][j][1]
                    + features[1][j][a.cards[0] as usize + 2]
                    + features[1][j][a.cards[1] as usize + 2];
                let c1 = 1.
                    + features[1][j][1]
                    + features[0][i][1]
                    + features[0][i][b.cards[0] as usize + 2]
                    + features[0][i][b.cards[1] as usize + 2];
                let blocked = a.mask & b.mask != 0;
                let near = c0 < 1e-10;
                let mass = if blocked {
                    0.
                } else if near {
                    removal.scalar(a.mask | b.mask)
                } else {
                    c0
                };
                if blocked || near {
                    if mass - c0 != 0. {
                        corrections[0][i].push((j, mass - c0));
                    }
                    if mass - c1 != 0. {
                        corrections[1][j].push((i, mass - c1));
                    }
                }
                if mass > 0. {
                    positive[0][i] = true;
                    positive[1][j] = true;
                }
                z += a.weight * b.weight * mass;
            }
        }
        if !z.is_finite() || z < 1e-4 {
            return Err(
                "three-seat compatible chance mass below supported conditioning floor".into(),
            );
        }
        Ok(Self {
            removal,
            features,
            corrections,
            positive,
            z,
            scalar_rows: AtomicU64::new(0),
        })
    }
    fn combine(&self, seat: usize, i: usize, cards: [u8; 2], p: &[f64; WIDTH]) -> f64 {
        (1. + self.features[seat][i][1]) * p[0]
            + p[1]
            + p[cards[0] as usize + 2]
            + p[cards[1] as usize + 2]
    }
    fn add(&self, seat: usize, j: usize, q: f64, p: &mut [f64; WIDTH]) {
        for (x, &f) in p.iter_mut().zip(&self.features[seat][j]) {
            *x += q * f;
        }
    }
    fn direct(&self, game: &Game, t: Terminal, seat: usize, i: usize, reach: &[f64]) -> f64 {
        self.scalar_rows.fetch_add(1, Ordering::Relaxed);
        let h = &game.hands[seat][i];
        let mut sum = 0.;
        for (j, o) in game.hands[1 - seat].iter().enumerate() {
            if h.mask & o.mask != 0 || reach[j] == 0. || o.weight == 0. {
                continue;
            }
            let (a, b) = if seat == 0 { (h, o) } else { (o, h) };
            let u = t.base
                + t.win0 * if a.rank > b.rank { 1. } else { 0. }
                + t.tie0 * if a.rank == b.rank { 1. } else { 0. };
            sum += o.weight * reach[j] * self.removal.compatible(h.cards, o.cards) * u;
        }
        let value = sum * h.weight / self.z;
        if seat == 0 {
            value
        } else {
            -value
        }
    }
    pub(super) fn leaf_into(
        &self,
        game: &Game,
        t: Terminal,
        seat: usize,
        reach: &[f64],
        out: &mut [f64],
    ) {
        let other = 1 - seat;
        let fold = t.win0 == 0. && t.tie0 == 0.;
        let mut total = [0.; WIDTH];
        for (j, h) in game.hands[other].iter().enumerate() {
            self.add(other, j, h.weight * reach[j], &mut total);
        }
        if total[0] == 0. {
            out.fill(0.);
            return;
        }
        let (mut low, mut high) = (0, 0);
        let (mut below, mut through) = ([0.; WIDTH], [0.; WIDTH]);
        for &i in &game.sorted[seat] {
            let h = &game.hands[seat][i];
            if h.weight == 0. || !self.positive[seat][i] {
                out[i] = 0.;
                continue;
            }
            if !fold {
                while low < game.sorted[other].len()
                    && game.hands[other][game.sorted[other][low]].rank < h.rank
                {
                    let j = game.sorted[other][low];
                    self.add(other, j, game.hands[other][j].weight * reach[j], &mut below);
                    low += 1;
                }
                while high < game.sorted[other].len()
                    && game.hands[other][game.sorted[other][high]].rank <= h.rank
                {
                    let j = game.sorted[other][high];
                    self.add(
                        other,
                        j,
                        game.hands[other][j].weight * reach[j],
                        &mut through,
                    );
                    high += 1;
                }
            }
            let mut mass = self.combine(seat, i, h.cards, &total);
            let mut weaker = if fold {
                0.
            } else {
                self.combine(seat, i, h.cards, &below)
            };
            let mut equal = if fold {
                0.
            } else {
                self.combine(seat, i, h.cards, &through) - weaker
            };
            for &(j, delta) in &self.corrections[seat][i] {
                let o = &game.hands[other][j];
                let q = o.weight * reach[j] * delta;
                mass += q;
                if !fold {
                    if o.rank < h.rank {
                        weaker += q;
                    } else if o.rank == h.rank {
                        equal += q;
                    }
                }
            }
            // Do not turn cancellation or entirely blocked conditional reach
            // into spurious mass, nor floor a genuinely tiny compatible world.
            if mass <= 1e-10 * total[0] {
                out[i] = self.direct(game, t, seat, i, reach);
                continue;
            }
            let win0 = if seat == 0 {
                weaker
            } else {
                mass - weaker - equal
            };
            let value = (t.base * mass + t.win0 * win0 + t.tie0 * equal) * h.weight / self.z;
            out[i] = if seat == 0 { value } else { -value };
        }
    }
    pub(super) fn stats(&self) -> serde_json::Value {
        let rows: usize = self.corrections.iter().flatten().map(Vec::len).sum();
        serde_json::json!({"backend":"exact-folded-prefix-v1","normalizer":self.z,
            "features":WIDTH,"correction_entries":rows,"scalar_rows":self.scalar_rows.load(Ordering::Relaxed),
            "payload_scope":"feature and correction elements only; excludes removal summaries, vector/allocator overhead",
            "payload_bytes":self.features.iter().map(|v|v.len()*WIDTH*8).sum::<usize>()+rows*std::mem::size_of::<(usize,f64)>()})
    }
}

impl Game {
    /// Exact three-seat modeled law, with one folded two-card range integrated
    /// out. Active ranges passed to Game::new must be original likelihoods,
    /// not the projected posterior marginals. The dense oracle stays opt-in.
    pub fn with_folded_range(mut self, folded: Vec<Holding>) -> Result<Self, String> {
        if self.joint.is_some() || self.folded.is_some() {
            return Err("chance law already replaced".into());
        }
        self.folded = Some(FoldedLaw::new(&self, folded)?);
        Ok(self)
    }
    pub fn chance_stats(&self) -> serde_json::Value {
        match &self.folded {
            Some(law) => law.stats(),
            None => {
                serde_json::json!({"backend":if self.joint.is_some(){"exact-dense-v1"}else{"projected-product-v1"}})
            }
        }
    }
}

#[cfg(test)]
#[path = "correlated_tests.rs"]
mod tests;
