//! Host-only scripted-belief continuations. A belief input cannot contain a deck,
//! opponent holes or future boards. Policies still receive only Observation.
use crate::{
    game::Kind,
    multi_arena::{action_likelihood, Bot},
    nplayer::{Action, Config, Hand, Observation},
};
use rand::{seq::SliceRandom, Rng, SeedableRng};
use serde_json::Value;

#[derive(Clone, Debug)]
pub struct LegalState {
    pub id: String,
    pub hero: usize,
    pub button: usize,
    pub hole: [u8; 2],
    pub board: Vec<u8>,
    pub actions: Vec<(usize, Action)>,
    pub opponents: Vec<String>,
    pub street: usize,
    pub expected_key: String,
    pub stratum: String,
    pub split: String,
}
fn uint(v: &Value) -> Result<usize, String> {
    usize::try_from(v.as_u64().ok_or("unsigned integer required")?).map_err(|e| e.to_string())
}
fn cards(v: &Value) -> Result<Vec<u8>, String> {
    v.as_array()
        .ok_or("card array required")?
        .iter()
        .map(|x| {
            let x = uint(x)?;
            if x >= 52 {
                Err("card out of bounds".into())
            } else {
                Ok(x as u8)
            }
        })
        .collect()
}
impl LegalState {
    /// Historical three-player random/random+TAG boundary stays unchanged.
    pub fn parse(v: &Value) -> Result<Self, String> {
        Self::parse_for(v, 3)
    }
    /// Six-player qualification is deliberately limited to public-only check-call.
    /// Card-dependent scripts require a different joint posterior, not this path.
    pub fn parse_six_check_call(v: &Value) -> Result<Self, String> {
        Self::parse_for(v, 6)
    }
    fn parse_for(v: &Value, players: usize) -> Result<Self, String> {
        let fields = [
            "id",
            "hero",
            "button",
            "hole",
            "board",
            "actions",
            "opponents",
            "street",
            "expected_key",
            "stratum",
            "split",
        ];
        let obj = v.as_object().ok_or("legal state object required")?;
        if obj.len() != fields.len() || obj.keys().any(|k| !fields.contains(&k.as_str())) {
            return Err("legal-state fields differ; private extras forbidden".into());
        }
        let string = |k: &str| {
            v[k].as_str()
                .map(str::to_owned)
                .ok_or_else(|| format!("missing {k}"))
        };
        let hero = uint(&v["hero"])?;
        let button = uint(&v["button"])?;
        let street = uint(&v["street"])?;
        let hole: [u8; 2] = cards(&v["hole"])?
            .try_into()
            .map_err(|_| "two own cards required")?;
        let board = cards(&v["board"])?;
        if hero >= players || button >= players || street > 3 || board.len() != [0, 3, 4, 5][street] {
            return Err("invalid state bounds".into());
        }
        let mut seen = 0u64;
        for c in hole.iter().chain(&board) {
            if seen & (1u64 << c) != 0 {
                return Err("duplicate visible card".into());
            }
            seen |= 1u64 << c;
        }
        let mut actions = Vec::new();
        let rows = v["actions"]
            .as_array()
            .ok_or("public action array required")?;
        if rows.len() > 200 {
            return Err("public action bound".into());
        }
        for row in rows {
            let row = row.as_array().ok_or("public action triple required")?;
            if row.len() != 3 {
                return Err("public action triple required".into());
            }
            let seat = uint(&row[0])?;
            let target = row[2].as_u64().ok_or("raise amount")?;
            let kind = match row[1].as_str() {
                Some("fold") => Kind::Fold,
                Some("check") => Kind::Check,
                Some("call") => Kind::Call,
                Some("raise") => Kind::Raise,
                _ => return Err("unknown public action".into()),
            };
            if seat >= players || (kind != Kind::Raise && target != 0) {
                return Err("invalid public action".into());
            }
            actions.push((
                seat,
                Action {
                    kind,
                    raise_to: target,
                },
            ));
        }
        let opponents: Vec<_> = v["opponents"]
            .as_array()
            .ok_or("opponent list")?
            .iter()
            .map(|x| x.as_str().map(str::to_owned).ok_or("opponent name"))
            .collect::<Result<_, _>>()?;
        let allowed = if players == 3 {
            &["random", "tight-aggressive"][..]
        } else {
            &["check-call"][..]
        };
        if opponents.len() != players
            || opponents[hero] != "hero"
            || opponents.iter().filter(|x| x.as_str() == "tight-aggressive").count() > 1
            || opponents.iter().enumerate().any(|(i,n)| i != hero && !allowed.contains(&n.as_str()))
        {
            return Err("opponents outside declared belief scope".into());
        }
        let key = string("expected_key")?;
        if key.len() != 32 || !key.bytes().all(|c| c.is_ascii_hexdigit()) {
            return Err("key pin required".into());
        }
        let result = Self {
            id: string("id")?,
            hero,
            button,
            hole,
            board,
            actions,
            opponents,
            street,
            expected_key: key,
            stratum: string("stratum")?,
            split: string("split")?,
        };
        result.replay(&result.deck(None, &mut rand::rngs::StdRng::seed_from_u64(0))?)?;
        Ok(result)
    }
    pub fn deck<R: Rng>(
        &self,
        tag: Option<(usize, [u8; 2])>,
        rng: &mut R,
    ) -> Result<Vec<u8>, String> {
        let players = self.opponents.len();
        let mut slots = [None; 52];
        let mut place = |seat: usize, hole: [u8; 2]| {
            let offset = (seat + players - (self.button + 1) % players) % players;
            slots[offset] = Some(hole[0]);
            slots[players + offset] = Some(hole[1]);
        };
        place(self.hero, self.hole);
        if let Some((seat, hole)) = tag {
            if seat >= players || seat == self.hero {
                return Err("invalid hidden holding seat".into());
            }
            place(seat, hole);
        }
        for (i, c) in self.board.iter().enumerate() {
            slots[2 * players + i] = Some(*c);
        }
        let mut used = 0u64;
        for c in slots.iter().flatten() {
            if used & (1u64 << c) != 0 {
                return Err("incompatible holding".into());
            }
            used |= 1u64 << c;
        }
        let mut remaining: Vec<_> = (0..52u8).filter(|c| used & (1u64 << c) == 0).collect();
        remaining.shuffle(rng);
        let mut next = remaining.into_iter();
        Ok(slots
            .into_iter()
            .map(|c| c.unwrap_or_else(|| next.next().unwrap()))
            .collect())
    }
    pub fn replay(&self, deck: &[u8]) -> Result<Hand, String> {
        let mut h = Hand::from_deck(Config::new(&vec![10000; self.opponents.len()], 50, 100)?, self.button, deck)?;
        for (seat, action) in &self.actions {
            if h.actor() != Some(*seat) {
                return Err("public actor differs".into());
            }
            h.apply_mut(*action)?;
        }
        if h.actor() != Some(self.hero)
            || h.street() as usize != self.street
            || h.board() != self.board
            || h.observe(self.hero)?.hole != self.hole
        {
            return Err("reconstructed observation differs".into());
        }
        Ok(h)
    }
    fn log_likelihood(&self, deck: &[u8]) -> Result<f64, String> {
        let mut h = Hand::from_deck(Config::new(&vec![10000; self.opponents.len()], 50, 100)?, self.button, deck)?;
        let mut log = 0.;
        for (seat, action) in &self.actions {
            if h.actor() != Some(*seat) {
                return Err("public actor differs".into());
            }
            if *seat != self.hero {
                let probability =
                    action_likelihood(&self.opponents[*seat], &h.observe(*seat)?, *action)?;
                if probability <= 0. {
                    return Ok(f64::NEG_INFINITY);
                }
                // Random action likelihood depends only on the public menu,
                // hence is constant across holdings and cancels from Bayes.
                if self.opponents[*seat] != "random" {
                    log += probability.ln();
                }
            }
            h.apply_mut(*action)?;
        }
        Ok(log)
    }
}

pub struct Belief {
    tag: Option<usize>,
    holdings: Vec<[u8; 2]>,
    cumulative: Vec<f64>,
    pub probabilities: Vec<f64>,
}
impl Belief {
    pub fn new(s: &LegalState) -> Result<Self, String> {
        let tag = s.opponents.iter().position(|x| x == "tight-aggressive");
        if tag.is_none() {
            let deck = s.deck(None, &mut rand::rngs::StdRng::seed_from_u64(0))?;
            if !s.log_likelihood(&deck)?.is_finite() {
                return Err("zero support under scripts".into());
            }
            return Ok(Self {
                tag,
                holdings: vec![],
                cumulative: vec![],
                probabilities: vec![],
            });
        }
        let visible: Vec<_> = s.hole.iter().chain(&s.board).copied().collect();
        let cards: Vec<_> = (0..52u8).filter(|c| !visible.contains(c)).collect();
        let mut holdings = Vec::new();
        let mut weights = Vec::new();
        for i in 0..cards.len() {
            for j in i + 1..cards.len() {
                let holding = [cards[i], cards[j]];
                let deck = s.deck(
                    Some((tag.unwrap(), holding)),
                    &mut rand::rngs::StdRng::seed_from_u64(0),
                )?;
                let log = s.log_likelihood(&deck)?;
                if log.is_finite() {
                    holdings.push(holding);
                    weights.push(log);
                }
            }
        }
        if weights.is_empty() {
            return Err("zero posterior support under scripts".into());
        }
        let max = weights.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        let weights: Vec<_> = weights.into_iter().map(|v| (v - max).exp()).collect();
        let total = weights.iter().sum::<f64>();
        let probabilities: Vec<_> = weights.into_iter().map(|v| v / total).collect();
        let mut sum = 0.;
        let cumulative = probabilities
            .iter()
            .map(|p| {
                sum += p;
                sum
            })
            .collect();
        Ok(Self {
            tag,
            holdings,
            cumulative,
            probabilities,
        })
    }
    fn deal<R: Rng>(&self, s: &LegalState, rng: &mut R) -> Result<Vec<u8>, String> {
        let tag = if let Some(seat) = self.tag {
            let u = rng.gen::<f64>();
            let index = self
                .cumulative
                .partition_point(|p| *p <= u)
                .min(self.holdings.len() - 1);
            Some((seat, self.holdings[index]))
        } else {
            None
        };
        s.deck(tag, rng)
    }
    pub fn draw<R: Rng>(&self, s: &LegalState, rng: &mut R) -> Result<Hand, String> {
        s.replay(&self.deal(s, rng)?)
    }
    /// Host-only card equity against current live players on an independently
    /// sampled belief runout. Never supplied to any action policy.
    pub fn draw_with_equity<R: Rng>(
        &self,
        s: &LegalState,
        rng: &mut R,
    ) -> Result<(Hand, f64), String> {
        let deck = self.deal(s, rng)?;
        let hand = s.replay(&deck)?;
        let players = s.opponents.len();
        let mut ranks = Vec::new();
        for (seat, p) in hand.players().iter().enumerate() {
            if !p.folded {
                let offset = (seat + players - (s.button + 1) % players) % players;
                let mut cards = deck[2 * players..2 * players + 5].to_vec();
                cards.extend_from_slice(&[deck[offset], deck[offset + players]]);
                ranks.push((seat, hu20_buckets::evaluate(&cards)));
            }
        }
        let best = ranks
            .iter()
            .map(|(_, r)| *r)
            .max()
            .ok_or("no live player")?;
        let ties = ranks.iter().filter(|(_, r)| *r == best).count();
        let share = if ranks.iter().any(|(seat, r)| *seat == s.hero && *r == best) {
            1. / ties as f64
        } else {
            0.
        };
        Ok((hand, share))
    }
    pub fn holding_count(&self) -> usize {
        self.holdings.len()
    }
    pub fn effective_holdings(&self) -> f64 {
        if self.tag.is_none() {
            0.
        } else {
            1. / self.probabilities.iter().map(|p| p * p).sum::<f64>()
        }
    }
}

pub fn rollout<F>(
    mut hand: Hand,
    hero: usize,
    first: Action,
    opponents: &[String],
    seed: u64,
    mut choose: F,
) -> Result<f64, String>
where
    F: FnMut(&Observation<'_>) -> Result<Action, String>,
{
    if hand.config().players() != opponents.len() || hero >= opponents.len() {
        return Err("rollout player count differs".into());
    }
    if hand.actor() != Some(hero) {
        return Err("rollout root actor".into());
    }
    hand.apply_mut(first)?;
    let mut bots: Vec<_> = opponents
        .iter()
        .enumerate()
        .map(|(seat, name)| {
            Bot::new(
                if seat == hero { "random" } else { name },
                seed.wrapping_add(seat as u64),
            )
        })
        .collect::<Result<_, _>>()?;
    let mut actions = 0;
    while let Some(actor) = hand.actor() {
        if actions >= if opponents.len() == 3 { 200 } else { 10000 } {
            return Err("continuation action bound".into());
        }
        let o = hand.observe(actor)?;
        let a = if actor == hero {
            choose(&o)?
        } else {
            bots[actor].choose(&o)?
        };
        hand.apply_mut(a)?;
        actions += 1;
    }
    let settlement = hand.settlement().ok_or("unsettled continuation")?;
    if settlement.rewards.iter().sum::<i64>() != 0 {
        return Err("continuation accounting".into());
    }
    Ok(settlement.rewards[hero] as f64 / 100.)
}

#[cfg(test)]
#[path = "multi_counterfactual_tests.rs"]
mod tests;
