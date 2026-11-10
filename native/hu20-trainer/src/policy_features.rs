//! A fixed-length numeric view of one acting seat's observation, for neural policies
//! (docs/neural-policy-data.md). Training data and network play both go through `encode`, so the
//! two can't drift; the layout is versioned by `SCHEMA` and pinned by `layout_sha256`.
//!
//! Every value is in [0, 1], so a sample stores each one as a byte (`quantize`). Seats occupy six
//! slots by position, the way a projected view places them: the button, small blind and big
//! blind in slots 0–2 and the remaining seats in the last slots, so a three-player table fills
//! the same slots a six-player table does after three early-position folds. Empty slots are
//! absent, not folded. Only the observation is read; nothing about other seats' cards.
use crate::cards::EquityTables;
use crate::game::{Kind, Street};
use crate::multi_holdem::menu;
use crate::nplayer::{Event, Observation};
use sha2::{Digest, Sha256};

pub const SCHEMA: &str = "nplayer-policy-features-v1";
pub const SLOTS: usize = 6;
/// The most recent actions kept, oldest first; earlier ones are summarized per seat and street.
pub const HISTORY: usize = 16;
/// Menu labels as in `multi_holdem::menu`: fold, check, call, min raise, pot raise, all-in.
pub const ACTIONS: usize = 6;
pub const BUCKETS: usize = 50;
/// Amounts are scaled by ln(1 + x/BB) / ln(1 + MAX_BB): 0 at nothing, 1 at 500 BB and above.
const MAX_BB: f64 = 500.;
/// Ratios to the pot are capped here and divided by it.
const RATIO_CAP: f64 = 32.;
const COUNT_CAP: f64 = 3.;

/// Feature names in order; their hash pins the layout.
pub fn names() -> Vec<String> {
    let mut n: Vec<String> = Vec::new();
    let mut push = |s: String| n.push(s);
    for s in ["preflop", "flop", "turn", "river"] {
        push(format!("street.{s}"));
    }
    for p in 2..=6 {
        push(format!("players.{p}"));
    }
    push("live_share".into());
    for s in 0..SLOTS {
        push(format!("hero_slot.{s}"));
    }
    for s in ["pot", "to_call", "price", "hero_spr", "effective", "effective_spr"] {
        push(format!("global.{s}"));
    }
    for a in 0..ACTIONS {
        push(format!("legal.{a}"));
    }
    for a in 3..ACTIONS {
        push(format!("raise_size.{a}"));
    }
    for c in 0..52 {
        push(format!("hole.{c}"));
    }
    for c in 0..52 {
        push(format!("board.{c}"));
    }
    for r in 0..13 {
        push(format!("high_rank.{r}"));
    }
    for r in 0..13 {
        push(format!("low_rank.{r}"));
    }
    for k in ["pair", "suited", "offsuit"] {
        push(format!("shape.{k}"));
    }
    for b in 0..BUCKETS {
        push(format!("bucket.{b}"));
    }
    for s in 0..SLOTS {
        for f in ["present", "hero", "folded", "all_in", "live", "stack", "spr", "street_bet", "contributed"] {
            push(format!("slot{s}.{f}"));
        }
        for street in ["preflop", "flop", "turn", "river"] {
            for f in ["raises", "calls", "checked"] {
                push(format!("slot{s}.{street}.{f}"));
            }
        }
    }
    for h in 0..HISTORY {
        push(format!("history{h}.valid"));
        for s in 0..SLOTS {
            push(format!("history{h}.slot.{s}"));
        }
        for street in ["preflop", "flop", "turn", "river"] {
            push(format!("history{h}.street.{street}"));
        }
        for k in ["fold", "check", "call", "raise"] {
            push(format!("history{h}.kind.{k}"));
        }
        push(format!("history{h}.raise_to"));
        push(format!("history{h}.paid"));
    }
    n
}
/// The feature count. `encode` asks for it at every traversal node, and rebuilding the 612 names
/// each time was most of a Deep CFR traversal's cost, so it is computed once.
pub fn len() -> usize {
    static LEN: std::sync::OnceLock<usize> = std::sync::OnceLock::new();
    *LEN.get_or_init(|| names().len())
}
/// SHA-256 over the schema name and every feature name, newline-separated.
pub fn layout_sha256() -> String {
    let mut h = Sha256::new();
    h.update(SCHEMA.as_bytes());
    for name in names() {
        h.update(b"\n");
        h.update(name.as_bytes());
    }
    format!("{:x}", h.finalize())
}

/// The slot a seat occupies: blinds and button keep their positions, the other seats take the
/// last slots, as in `multi_view::project`.
pub fn slot(observation: &Observation<'_>, seat: usize) -> usize {
    let n = observation.config.players();
    let position = (seat + n - observation.button) % n;
    if position < 3 { position } else { position + SLOTS - n }
}
/// Which menu labels are legal, as a bit set.
pub fn legal_mask(observation: &Observation<'_>) -> u8 {
    menu(observation).iter().fold(0, |m, (label, _)| m | 1 << label)
}

fn scaled(amount: u64, bb: u64) -> f64 {
    ((amount as f64 / bb as f64).ln_1p() / MAX_BB.ln_1p()).min(1.)
}
fn ratio(value: u64, base: u64) -> f64 {
    if base == 0 { return 1.; }
    (value as f64 / base as f64).min(RATIO_CAP) / RATIO_CAP
}
fn street_index(s: Street) -> usize {
    s as usize
}

fn one_hot(out: &mut Vec<f32>, size: usize, index: usize) {
    out.extend((0..size).map(|i| (i == index) as u8 as f32));
}

/// Encodes an acting seat's observation. `tables` gives the K50 bucket and is needed after the
/// flop only.
pub fn encode(observation: &Observation<'_>, tables: Option<&EquityTables>) -> Result<Vec<f32>, String> {
    let legal = observation.legal.ok_or("features need the acting seat's legal set")?;
    if observation.actor != Some(observation.seat) {
        return Err("features need the acting seat's observation".into());
    }
    let n = observation.config.players();
    if !(2..=SLOTS).contains(&n) {
        return Err("features cover 2 to 6 players".into());
    }
    let bb = observation.config.big_blind();
    let players = observation.players;
    let hero = observation.seat;
    let mut out = Vec::with_capacity(len());
    one_hot(&mut out, 4, street_index(observation.street));
    one_hot(&mut out, 5, n - 2);
    let live: Vec<usize> = (0..n).filter(|&p| !players[p].folded).collect();
    out.push(live.len() as f32 / SLOTS as f32);
    one_hot(&mut out, SLOTS, slot(observation, hero));
    let pot: u64 = players.iter().map(|p| p.contributed).sum();
    let start = |p: usize| players[p].stack + players[p].street_bet;
    let own = players[hero].stack;
    let deepest = live.iter().filter(|&&p| p != hero).map(|&p| players[p].stack).max().unwrap_or(0);
    let effective = own.min(deepest);
    out.push(scaled(pot, bb) as f32);
    out.push(scaled(legal.call_amount, bb) as f32);
    out.push((legal.call_amount as f64 / (pot + legal.call_amount).max(1) as f64) as f32);
    out.push(ratio(own, pot) as f32);
    out.push(scaled(effective, bb) as f32);
    out.push(ratio(effective, pot) as f32);
    let choices = menu(observation);
    let mask = choices.iter().fold(0u8, |m, (label, _)| m | 1 << label);
    for a in 0..ACTIONS {
        out.push((mask >> a & 1) as f32);
    }
    let matched = players[hero].street_bet + legal.call_amount;
    let after_call = pot + legal.call_amount;
    for label in 3..ACTIONS as u8 {
        let size = choices.iter().find(|(l, _)| *l == label).map_or(0., |(_, a)| {
            ((a.raise_to - matched) as f64 / after_call.max(1) as f64).min(RATIO_CAP) / RATIO_CAP
        });
        out.push(size as f32);
    }
    let mut hole = [0f32; 52];
    for &c in &observation.hole {
        hole[c as usize] = 1.;
    }
    out.extend_from_slice(&hole);
    let mut board = [0f32; 52];
    for &c in observation.board {
        board[c as usize] = 1.;
    }
    out.extend_from_slice(&board);
    let [a, b] = observation.hole;
    let (hi, lo) = ((a / 4).max(b / 4) as usize, (a / 4).min(b / 4) as usize);
    one_hot(&mut out, 13, hi);
    one_hot(&mut out, 13, lo);
    one_hot(&mut out, 3, if hi == lo { 0 } else if a % 4 == b % 4 { 1 } else { 2 });
    if observation.board.is_empty() {
        out.extend(std::iter::repeat(0.).take(BUCKETS));
    } else {
        let bucket = tables.ok_or("postflop features need the K50 tables")?.bucket(observation.hole, observation.board) as usize;
        if bucket >= BUCKETS {
            return Err(format!("card bucket {bucket} outside the K50 range"));
        }
        one_hot(&mut out, BUCKETS, bucket);
    }
    // Per seat and street: raises, calls and whether it checked.
    let mut counts = [[[0u8; 3]; 4]; SLOTS];
    for event in observation.history {
        if let Event::Action { street, actor, action, .. } = event {
            let c = &mut counts[slot(observation, *actor)][street_index(*street)];
            match action.kind {
                Kind::Raise => c[0] += 1,
                Kind::Call => c[1] += 1,
                Kind::Check => c[2] = 1,
                Kind::Fold => {}
            }
        }
    }
    let mut by_slot = [None; SLOTS];
    for seat in 0..n {
        by_slot[slot(observation, seat)] = Some(seat);
    }
    for s in 0..SLOTS {
        match by_slot[s] {
            None => out.extend(std::iter::repeat(0.).take(9 + 12)),
            Some(seat) => {
                let p = players[seat];
                let all_in = !p.folded && p.stack == 0;
                for v in [1., (seat == hero) as u8 as f64, p.folded as u8 as f64, all_in as u8 as f64,
                          (!p.folded) as u8 as f64, scaled(p.stack, bb), ratio(start(seat), pot.max(1)),
                          scaled(p.street_bet, bb), scaled(p.contributed, bb)] {
                    out.push(v as f32);
                }
                for street in &counts[s] {
                    out.push((street[0] as f64).min(COUNT_CAP) as f32 / COUNT_CAP as f32);
                    out.push((street[1] as f64).min(COUNT_CAP) as f32 / COUNT_CAP as f32);
                    out.push(street[2] as f32);
                }
            }
        }
    }
    let actions: Vec<_> = observation.history.iter().filter_map(|e| match e {
        Event::Action { street, actor, action, paid } => Some((*street, *actor, *action, *paid)),
        Event::Board(_) => None,
    }).collect();
    let recent = &actions[actions.len().saturating_sub(HISTORY)..];
    for h in 0..HISTORY {
        match recent.get(h) {
            None => out.extend(std::iter::repeat(0.).take(1 + SLOTS + 4 + 4 + 2)),
            Some(&(street, actor, action, paid)) => {
                out.push(1.);
                one_hot(&mut out, SLOTS, slot(observation, actor));
                one_hot(&mut out, 4, street_index(street));
                one_hot(&mut out, 4, match action.kind { Kind::Fold => 0, Kind::Check => 1, Kind::Call => 2, Kind::Raise => 3 });
                out.push(if action.kind == Kind::Raise { scaled(action.raise_to, bb) as f32 } else { 0. });
                out.push(scaled(paid, bb) as f32);
            }
        }
    }
    debug_assert_eq!(out.len(), len());
    if let Some(bad) = out.iter().position(|v| !(0. ..=1.).contains(v)) {
        return Err(format!("feature {} = {} outside [0, 1]", names()[bad], out[bad]));
    }
    Ok(out)
}
/// One byte per feature: round(255·v).
pub fn quantize(features: &[f32]) -> Vec<u8> {
    features.iter().map(|v| (v * 255.).round() as u8).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::multi_holdem::menu;
    use crate::nplayer::{Config, Hand};
    use rand::{seq::SliceRandom, Rng, SeedableRng};

    fn tables() -> Option<&'static EquityTables> {
        let dir = std::env::var("HU20_K50_TABLES").ok()?;
        EquityTables::load(std::path::Path::new(&dir), false).ok()
    }

    #[test]
    fn names_are_unique_and_pin_the_layout() {
        let names = names();
        let unique: std::collections::HashSet<_> = names.iter().collect();
        assert_eq!(unique.len(), names.len());
        assert_eq!(names.len(), 4 + 5 + 1 + 6 + 6 + 6 + 3 + 52 + 52 + 13 + 13 + 3 + 50 + 6 * 21 + 16 * 17);
        assert_eq!(layout_sha256().len(), 64);
    }

    #[test]
    fn slots_match_the_projected_view() {
        for n in 3..=6 {
            let hand = Hand::from_deck(Config::new(&vec![10000; n], 50, 100).unwrap(), 1, &(0..52).collect::<Vec<_>>()).unwrap();
            let o = hand.observe(hand.actor().unwrap()).unwrap();
            let slots: Vec<_> = (0..n).map(|s| slot(&o, s)).collect();
            assert_eq!(slots[1], 0, "the button is slot 0");
            assert_eq!(slots[2], 1);
            assert_eq!(slots[3 % n], 2);
            let mut sorted = slots.clone();
            sorted.sort_unstable();
            sorted.dedup();
            assert_eq!(sorted.len(), n);
            // The seats after the big blind take the last slots, as phantom folds leave them.
            assert!(slots.iter().filter(|&&s| s >= 3).all(|&s| s >= SLOTS - (n - 3)));
        }
    }

    /// Preflop decisions need no K50 tables: walk random hands to the flop and check every
    /// preflop encoding is in range, has the right length and reflects the legal menu.
    #[test]
    fn preflop_encodings_are_bounded_and_carry_the_legal_menu() {
        let mut rng = rand::rngs::StdRng::seed_from_u64(4);
        let mut checked = 0;
        for _ in 0..300 {
            let n = rng.gen_range(2..=6);
            let stacks: Vec<u64> = (0..n).map(|_| rng.gen_range(1..=250) * 100).collect();
            let mut deck: Vec<u8> = (0..52).collect();
            deck.shuffle(&mut rng);
            let mut hand = Hand::from_deck(Config::new(&stacks, 50, 100).unwrap(), rng.gen_range(0..n), &deck).unwrap();
            while let Some(actor) = hand.actor() {
                if !hand.board().is_empty() {
                    break;
                }
                let o = hand.observe(actor).unwrap();
                let f = encode(&o, None).unwrap();
                assert_eq!(f.len(), len());
                let names = names();
                let legal: u8 = (0..ACTIONS).filter(|a| f[names.iter().position(|x| *x == format!("legal.{a}")).unwrap()] == 1.).fold(0, |m, a| m | 1 << a);
                assert_eq!(legal, legal_mask(&o));
                assert_eq!(f[names.iter().position(|x| x == "slot0.present").unwrap()], 1.);
                let choices = menu(&o);
                hand.apply_mut(choices[rng.gen_range(0..choices.len())].1).unwrap();
                checked += 1;
            }
        }
        assert!(checked > 500);
    }

    #[test]
    fn quantization_round_trips_within_half_a_step() {
        let v = [0., 0.25, 0.5, 1., 0.123];
        for (q, x) in quantize(&v).iter().zip(v) {
            assert!(((*q as f32) / 255. - x).abs() <= 0.5 / 255. + 1e-6);
        }
    }

    #[test]
    fn postflop_encodings_use_the_k50_bucket_when_tables_are_present() {
        let Some(t) = tables() else { return };
        let mut hand = Hand::from_deck(Config::new(&[10000; 3], 50, 100).unwrap(), 0, &(0..52).collect::<Vec<_>>()).unwrap();
        while hand.board().is_empty() {
            let o = hand.observe(hand.actor().unwrap()).unwrap();
            let call = menu(&o).into_iter().find(|(l, _)| *l == 1 || *l == 2).unwrap().1;
            hand.apply_mut(call).unwrap();
        }
        let o = hand.observe(hand.actor().unwrap()).unwrap();
        assert!(encode(&o, None).is_err());
        let f = encode(&o, Some(t)).unwrap();
        let start = names().iter().position(|x| x == "bucket.0").unwrap();
        assert_eq!(f[start..start + BUCKETS].iter().sum::<f32>(), 1.);
    }
}
