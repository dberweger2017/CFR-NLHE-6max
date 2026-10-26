//! Public-only cash-game adapter to the same traversal used by Kuhn and Leduc.
use crate::cards::EquityTables;
use crate::game::Kind;
use crate::multi_cfr::{Decision, Game, State};
use crate::nplayer::{Action, Config, Event, Hand, Observation, Saved};
use rand::{seq::SliceRandom, Rng};
use serde_json::{json, Value};

pub const SCHEMA: &str = "nplayer-button-live-actor-history-equity-k50-v1";
/// Coarse keys: docs/nplayer-live-order-keys.md.
pub const LIVE_ORDER_SCHEMA: &str = "nplayer-live-order-summary-equity-k50-v1";
pub const MENU: &str = "min-pot-conditional-jam-v1";

/// How a decision's public history enters its information key. Released models use `History`.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum KeySchema {
    /// Every public action with its amounts, and every seat's chips.
    #[default]
    History,
    /// The live players' order and a capped summary of the betting (`live_order_payload`).
    LiveOrder,
    CompactBlake,
    CompactXxh3,
}
impl KeySchema {
    pub const ALL: [Self; 4] = [Self::History, Self::LiveOrder, Self::CompactBlake, Self::CompactXxh3];
    pub const EXACT_HISTORY: [Self; 3] = [Self::History, Self::CompactBlake, Self::CompactXxh3];
    pub fn option(self) -> &'static str {
        match self {
            Self::History => "v1", Self::LiveOrder => "live-order",
            Self::CompactBlake => "compact-blake2b-v2", Self::CompactXxh3 => "compact-xxh3-v2",
        }
    }
    pub fn parse(value: &str) -> Result<Self, String> {
        if value == "history" { return Ok(Self::History); }
        Self::ALL.into_iter().find(|s| s.option() == value || s.name() == value)
            .ok_or_else(|| format!("unsupported n-player key schema: {value}"))
    }
    pub fn is_compact(self) -> bool { matches!(self, Self::CompactBlake | Self::CompactXxh3) }

    pub fn name(self) -> &'static str {
        match self {
            KeySchema::History => SCHEMA,
            KeySchema::LiveOrder => LIVE_ORDER_SCHEMA,
            Self::CompactBlake => "nplayer-button-history-equity-k50-compact-blake2b-v2",
            Self::CompactXxh3 => "nplayer-button-history-equity-k50-compact-xxh3-v2",
        }
    }
    pub fn from_name(name: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|s| s.name() == name)
    }
    pub fn from_identity(identity: &Value) -> Option<Self> {
        identity["schema"].as_str().and_then(Self::from_name)
    }
}

/// HU v1 sizing, clamping, duplicate removal and conditional all-in admission.
/// Constructed from an observation, so legality/sizing cannot inspect a deal.
pub fn menu(observation: &Observation<'_>) -> Vec<(u8, Action)> {
    let legal = observation.legal.expect("only the acting seat has a menu");
    assert_eq!(observation.actor, Some(observation.seat));
    let mut out = Vec::with_capacity(5);
    let passive = if legal.check { Kind::Check } else { Kind::Fold };
    out.push((
        if legal.check { 1 } else { 0 },
        Action {
            kind: passive,
            raise_to: 0,
        },
    ));
    if !legal.check {
        out.push((
            2,
            Action {
                kind: Kind::Call,
                raise_to: 0,
            },
        ));
    }
    if let Some((low, high)) = legal.raise_to {
        let matched = observation.players[observation.seat].street_bet + legal.call_amount;
        let pot: u64 = observation.players.iter().map(|p| p.contributed).sum();
        let after_call = pot + legal.call_amount;
        let pot_target = (matched + after_call).clamp(low, high);
        for (label, target) in [(3, low), (4, pot_target), (5, high)] {
            if label == 5 && high - matched > 2 * after_call && high != low {
                continue;
            }
            if out
                .iter()
                .any(|(_, a)| a.kind == Kind::Raise && a.raise_to == target)
            {
                continue;
            }
            out.push((
                label,
                Action {
                    kind: Kind::Raise,
                    raise_to: target,
                },
            ));
        }
    }
    out
}

fn kind_code(kind: Kind) -> u8 {
    match kind {
        Kind::Fold => 0,
        Kind::Check => 1,
        Kind::Call => 2,
        Kind::Raise => 3,
    }
}

/// Byte framing is explicit: fixed-width integers, counted players/history and
/// typed events. Board reveals add a street marker; raw board cards would undo
/// the requested K50 abstraction. Only the current street's card class changes.
fn payload(observation: &Observation<'_>, cards: &[u8], choices: &[(u8, Action)]) -> Vec<u8> {
    let n = observation.config.players();
    let relative = |seat: usize| ((seat + n - observation.button) % n) as u8;
    let mut out = SCHEMA.as_bytes().to_vec();
    out.push(0);
    out.extend_from_slice(&[
        n as u8,
        relative(observation.seat),
        observation.street as u8,
    ]);
    let mut live = 0;
    let mut all_in = 0;
    for (p, s) in observation.players.iter().enumerate() {
        if !s.folded {
            live |= 1 << relative(p);
            if s.stack == 0 {
                all_in |= 1 << relative(p);
            }
        }
    }
    out.extend_from_slice(&[live, all_in]);
    out.extend_from_slice(&observation.config.small_blind().to_le_bytes());
    out.extend_from_slice(&observation.config.big_blind().to_le_bytes());
    for i in 0..n {
        let p = (observation.button + i) % n;
        let s = observation.players[p];
        for chips in [
            observation.config.stacks()[p],
            s.stack,
            s.street_bet,
            s.contributed,
        ] {
            out.extend_from_slice(&chips.to_le_bytes());
        }
    }
    out.push(cards.len() as u8);
    out.extend_from_slice(cards);
    out.extend_from_slice(&(observation.history.len() as u64).to_le_bytes());
    for event in observation.history {
        match event {
            Event::Board(street) => out.extend_from_slice(&[255, *street as u8]),
            Event::Action {
                street,
                actor,
                action,
                paid,
            } => {
                out.extend_from_slice(&[*street as u8, relative(*actor), kind_code(action.kind)]);
                out.extend_from_slice(&action.raise_to.to_le_bytes());
                out.extend_from_slice(&paid.to_le_bytes());
            }
        }
    }
    out.push(choices.len() as u8);
    for (label, action) in choices {
        out.push(*label);
        out.extend_from_slice(&action.raise_to.to_le_bytes());
    }
    out
}

fn varint(out: &mut Vec<u8>, mut value: u64) {
    while value >= 128 {
        out.push(value as u8 | 128);
        value >>= 7;
    }
    out.push(value as u8);
}

/// Complete legal history reconstructs live/all-in flags, contributions and menu.
/// Initial stacks remain button-relative: omitting them would alias unequal-stack
/// hands when the button rotates, even within one fixed physical configuration.
fn compact_payload(observation: &Observation<'_>, cards: &[u8]) -> Vec<u8> {
    let n = observation.config.players();
    let relative = |seat: usize| ((seat + n - observation.button) % n) as u8;
    let mut out = Vec::with_capacity(64);
    // Fixed domain includes menu/card abstraction version; schemas distinguish hashes.
    out.extend_from_slice(b"NP\x02");
    out.extend_from_slice(&[
        n as u8,
        relative(observation.seat),
        observation.street as u8,
    ]);
    varint(&mut out, observation.config.small_blind());
    varint(&mut out, observation.config.big_blind());
    for i in 0..n {
        varint(
            &mut out,
            observation.config.stacks()[(observation.button + i) % n],
        );
    }
    out.push(cards.len() as u8);
    out.extend_from_slice(cards);
    varint(&mut out, observation.history.len() as u64);
    for event in observation.history {
        match event {
            Event::Board(street) => out.extend_from_slice(&[255, *street as u8]),
            Event::Action { actor, action, .. } => {
                out.push((relative(*actor) << 2) | kind_code(action.kind));
                if action.kind == Kind::Raise {
                    varint(&mut out, action.raise_to);
                }
            }
        }
    }
    out
}


/// Bucket edges of the live-order summary, as exact fractions (numerator, denominator).
const POT_EDGES_BB: [u64; 7] = [2, 4, 8, 16, 32, 64, 128];
const SPR_EDGES: [(u64, u64); 6] = [(1, 2), (1, 1), (2, 1), (4, 1), (8, 1), (16, 1)];
const PRICE_EDGES: [(u64, u64); 4] = [(1, 10), (2, 10), (3, 10), (4, 10)];
const RAISE_CAP: u8 = 3;

/// How many `edges` are at most value / base, compared exactly in integers.
fn bucket(value: u64, base: u64, edges: &[(u64, u64)]) -> u8 {
    edges.iter().filter(|&&(num, den)| value as u128 * den as u128 >= num as u128 * base.max(1) as u128).count() as u8
}

/// Seats enter only by their order among the live players, counted from the button, so a key
/// doesn't record who folded before. Earlier streets keep their capped raise counts and the
/// previous street's last aggressor; the pot and each live stack enter as buckets at the
/// street's start. The current street keeps its capped raise count, last raiser, number of
/// actions and the price to call. The card class and action labels are as in `History`.
fn live_order_payload(observation: &Observation<'_>, cards: &[u8], code: u16) -> (Vec<u8>, usize) {
    let n = observation.config.players();
    let by_button = |i: usize| (observation.button + i) % n;
    let live: Vec<usize> = (0..n).map(by_button).filter(|&p| !observation.players[p].folded).collect();
    let order = |seat: usize| live.iter().position(|&p| p == seat).map_or(u8::MAX, |i| i as u8);
    let street = observation.street as usize;
    let hero = order(observation.seat);
    let mut out = LIVE_ORDER_SCHEMA.as_bytes().to_vec();
    out.push(0);
    let all_in = live.iter().filter(|&&p| observation.players[p].stack == 0).count();
    out.extend_from_slice(&[n as u8, live.len() as u8, hero, street as u8, all_in as u8]);
    let pot: u64 = observation.players.iter().map(|p| p.contributed - p.street_bet).sum();
    out.push(bucket(pot, observation.config.big_blind(), &POT_EDGES_BB.map(|e| (e, 1))));
    let mut spr: Vec<u8> = live.iter().map(|&p| {
        let s = observation.players[p];
        bucket(s.stack + s.street_bet, pot, &SPR_EDGES)
    }).collect();
    spr.sort_unstable();
    out.extend_from_slice(&spr);
    let mut raises = [0u8; 4];
    let mut last_raiser = [None; 4];
    let mut actions = 0u8;
    for event in observation.history {
        if let Event::Action { street: s, actor, action, .. } = event {
            let s = *s as usize;
            if action.kind == Kind::Raise {
                raises[s] = (raises[s] + 1).min(RAISE_CAP);
                last_raiser[s] = Some(*actor);
            }
            if s == street {
                actions = actions.saturating_add(1);
            }
        }
    }
    out.extend_from_slice(&raises[..=street]);
    let previous = street.checked_sub(1).and_then(|s| last_raiser[s]);
    out.extend_from_slice(&[previous.map_or(u8::MAX, order), last_raiser[street].map_or(u8::MAX, order), actions]);
    let legal = observation.legal.expect("only the acting seat has a key");
    let after_call: u64 = observation.players.iter().map(|p| p.contributed).sum::<u64>() + legal.call_amount;
    out.push(bucket(legal.call_amount, after_call, &PRICE_EDGES));
    out.push(cards.len() as u8);
    out.extend_from_slice(cards);
    out.extend_from_slice(&code.to_le_bytes());
    (out, hero as usize)
}

fn card_class(observation: &Observation<'_>, tables: Option<&EquityTables>) -> Vec<u8> {
    if observation.board.is_empty() {
        let [a, b] = observation.hole;
        let hi = (a / 4).max(b / 4);
        let lo = (a / 4).min(b / 4);
        vec![
            0,
            hi,
            lo,
            if hi == lo {
                0
            } else if a % 4 == b % 4 {
                1
            } else {
                2
            },
        ]
    } else {
        let bucket = tables
            .expect("postflop requires pinned K50 tables")
            .bucket(observation.hole, observation.board);
        let mut out = vec![observation.street as u8];
        out.extend_from_slice(&bucket.to_le_bytes());
        out
    }
}

/// The policy boundary accepts only the acting seat's immutable observation. Released `History`
/// keys; models with another schema look up through `observation_decision_for`.
pub fn observation_decision(observation: &Observation<'_>, tables: &EquityTables) -> Decision {
    observation_decision_with_tables(KeySchema::History, observation, Some(tables))
}
pub fn observation_decision_for(schema: KeySchema, observation: &Observation<'_>, tables: &EquityTables) -> Decision {
    observation_decision_with_tables(schema, observation, Some(tables))
}
/// `owner` is a stable identity inside the key: the button-relative seat for `History`, the
/// order among live players for `LiveOrder`.
fn observation_decision_with_tables(
    schema: KeySchema,
    observation: &Observation<'_>,
    tables: Option<&EquityTables>,
) -> Decision {
    let choices = menu(observation);
    let cards = card_class(observation, tables);
    decision_from_cards(schema, observation, &cards, &choices)
}
fn decision_from_cards(schema: KeySchema, observation: &Observation<'_>, cards: &[u8], choices: &[(u8, Action)]) -> Decision {
    let code = choices.iter().fold(0, |c, (label, _)| c | 1 << label);
    let n = observation.config.players();
    let mut owner = (observation.seat + n - observation.button) % n;
    let key = match schema {
        KeySchema::History => crate::key::digest16(&payload(observation, cards, choices)),
        KeySchema::LiveOrder => {
            let (bytes, live_owner) = live_order_payload(observation, cards, code);
            owner = live_owner;
            crate::key::digest16(&bytes)
        },
        KeySchema::CompactBlake => crate::key::digest16(&compact_payload(observation, cards)),
        KeySchema::CompactXxh3 => xxhash_rust::xxh3::xxh3_128(&compact_payload(observation, cards)).to_le_bytes(),
    };
    Decision { key, actor: observation.seat, owner, street: observation.street as usize, code }
}
/// Legacy compact benchmark API. Production readers dispatch through observation_decision_for.
pub fn observation_decision_schema(observation: &Observation<'_>, tables: &EquityTables, schema: KeySchema) -> Decision {
    observation_decision_for(schema, observation, tables)
}
/// Untimed audit only: all exact-history encodings share the same decision builder.
pub fn observation_key_variants(observation: &Observation<'_>, tables: &EquityTables) -> [Decision; 3] {
    let cards = card_class(observation, Some(tables));
    let choices = menu(observation);
    KeySchema::EXACT_HISTORY.map(|schema| decision_from_cards(schema, observation, &cards, &choices))
}
/// Compact-only header witness. No policy row is required, so empty/sparse tables remain valid.
/// Synthetic abstract card labels exercise all street framing without loading K50.
pub fn key_encoding_binding(schema: KeySchema) -> Value {
    let mut bytes = Vec::new();
    for n in [2, 3, 6] {
        let config = Config::new(&vec![2000; n], 50, 100).unwrap();
        let mut hand = Hand::from_deck(config, n-1, &(0..52).collect::<Vec<_>>()).unwrap();
        while let Some(actor) = hand.actor() {
            let obs = hand.observe(actor).unwrap();
            let cards = if obs.board.is_empty() { card_class(&obs, None) } else { vec![obs.street as u8, 17, 0] };
            let choices = menu(&obs);
            bytes.extend_from_slice(&decision_from_cards(schema, &obs, &cards, &choices).key);
            let action = choices.iter().find(|(_, a)| matches!(a.kind, Kind::Call | Kind::Check)).unwrap().1;
            hand.apply_mut(action).unwrap();
        }
    }
    json!({"schema":schema.name(), "probe":"nplayer-passive-key-selftest-v1", "digest":crate::multi_checkpoint::key_hex(&crate::key::digest16(&bytes))})
}
pub fn validate_key_encoding(identity: &Value) -> Result<(), String> {
    let Some(schema) = KeySchema::from_identity(identity) else { return Err("unsupported key schema".into()); };
    match identity.get("key_encoding") {
        Some(binding) if *binding == key_encoding_binding(schema) => Ok(()),
        None if !schema.is_compact() => Ok(()),
        _ => Err("key encoding binding/schema mismatch (unbound prototype compact files are unsupported)".into()),
    }
}

pub struct CashGame {
    pub config: Config,
    pub tables: &'static EquityTables,
    pub schema: KeySchema,
}
#[derive(Clone)]
pub struct CashState {
    pub hand: Hand,
    tables: Option<&'static EquityTables>,
    schema: KeySchema,
}
impl Game for CashGame {
    type State = CashState;
    fn players(&self) -> usize {
        self.config.players()
    }
    fn identity(&self) -> Value {
        let mut identity = json!({"schema":self.schema.name(),"game":"nlhe-cash","players":self.players(),"stacks":self.config.stacks(),
            "small_blind":self.config.small_blind(),"big_blind":self.config.big_blind(),"menu":MENU,
            "card_tables":self.tables.sha256,"utility_unit":"big-blind"});
        if self.schema.is_compact() { identity["key_encoding"] = key_encoding_binding(self.schema); }
        identity
    }
    fn sample(&self, rng: &mut rand::rngs::StdRng) -> CashState {
        let mut deck: Vec<u8> = (0..52).collect();
        deck.shuffle(rng);
        let button = rng.gen_range(0..self.players());
        CashState {
            hand: Hand::from_deck(self.config, button, &deck).unwrap(),
            tables: Some(self.tables),
            schema: self.schema,
        }
    }
}
impl CashState {
    pub fn new(hand: Hand, tables: &'static EquityTables) -> Self {
        Self {
            hand,
            tables: Some(tables),
            schema: KeySchema::History,
        }
    }
}
impl State for CashState {
    type Saved = Saved;
    fn players(&self) -> usize {
        self.hand.config().players()
    }
    fn decision(&self) -> Option<Decision> {
        let actor = self.hand.actor()?;
        let observation = self.hand.observe(actor).unwrap();
        Some(observation_decision_with_tables(self.schema, &observation, self.tables))
    }
    fn payoff(&self, player: usize) -> f64 {
        self.hand
            .settlement()
            .expect("utility requires a terminal")
            .rewards[player] as f64
            / self.hand.config().big_blind() as f64
    }
    fn save(&self) -> Saved {
        self.hand.save()
    }
    fn restore(&mut self, saved: Saved) {
        self.hand.restore(saved);
    }
    fn apply(&mut self, action_index: usize) {
        let actor = self.hand.actor().unwrap();
        let action = menu(&self.hand.observe(actor).unwrap())[action_index].1;
        self.hand.apply_mut(action).unwrap();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn seat_rotation_keys_and_menus_use_only_the_observation() {
        for n in 2..=6 {
            let config = Config::new(&vec![2000; n], 50, 100).unwrap();
            // Same deck deals the same relative hands when the button rotates.
            let mut reference = None;
            for button in 0..n {
                let hand = Hand::from_deck(config, button, &(0..52).collect::<Vec<_>>()).unwrap();
                let mut state = CashState { hand, tables: None, schema: KeySchema::History };
                let d = state.decision().unwrap();
                let identity = (d.key, d.owner, d.code);
                if let Some(old) = reference {
                    assert_eq!(identity, old);
                } else {
                    reference = Some(identity);
                }
                let saved = state.save();
                state.apply(0);
                state.restore(saved);
                assert_eq!(state.decision().unwrap(), d);
                let mut table = crate::multi_cfr::Table::default();
                table.insert(d.key, crate::multi_cfr::Entry::new(d, 3));
                table.get(&d.key).unwrap().check(d);
            }
        }
    }
    #[test]
    fn pressure_takes_the_menus_pot_size_raise_whenever_one_is_legal() {
        use crate::multi_cfr::pressure_action;
        use rand::SeedableRng;
        let mut rng = rand::rngs::StdRng::seed_from_u64(7);
        let mut checked = 0;
        for n in [3, 6] {
            for stack in [500, 2000, 10000] {
                let config = Config::new(&vec![stack; n], 50, 100).unwrap();
                for _ in 0..200 {
                    let mut deck: Vec<u8> = (0..52).collect();
                    deck.shuffle(&mut rng);
                    let mut state = CashState { hand: Hand::from_deck(config, rng.gen_range(0..n), &deck).unwrap(), tables: None, schema: KeySchema::History };
                    // Postflop keys need the K50 tables; the menu rule is the same on every street.
                    while let Some(d) = state.hand.board().is_empty().then(|| state.decision()).flatten() {
                        let observation = state.hand.observe(state.hand.actor().unwrap()).unwrap();
                        let legal = observation.legal.unwrap();
                        let choices = menu(&observation);
                        match (legal.raise_to, pressure_action(d)) {
                            (None, None) => {}
                            (Some((low, high)), Some(i)) => {
                                let matched = observation.players[observation.seat].street_bet + legal.call_amount;
                                let pot: u64 = observation.players.iter().map(|p| p.contributed).sum();
                                let target = (matched + pot + legal.call_amount).clamp(low, high);
                                assert_eq!(choices[i].1, Action { kind: Kind::Raise, raise_to: target });
                                checked += 1;
                            }
                            other => panic!("raise legality and pressure disagree: {other:?}"),
                        }
                        state.apply(rng.gen_range(0..d.len()));
                    }
                }
            }
        }
        assert!(checked > 500, "{checked} raise decisions checked");
    }

    /// Preflop only: the hand stops at the flop, scored zero, so no K50 lookup is needed.
    #[derive(Clone)]
    struct Preflop(CashState);
    impl State for Preflop {
        type Saved = Saved;
        fn players(&self) -> usize {
            self.0.players()
        }
        fn decision(&self) -> Option<Decision> {
            self.0.hand.board().is_empty().then(|| self.0.decision()).flatten()
        }
        fn payoff(&self, player: usize) -> f64 {
            if self.0.hand.finished() { self.0.payoff(player) } else { 0. }
        }
        fn save(&self) -> Saved {
            self.0.save()
        }
        fn restore(&mut self, saved: Saved) {
            self.0.restore(saved)
        }
        fn apply(&mut self, action_index: usize) {
            self.0.apply(action_index)
        }
    }

    #[test]
    fn pressure_changes_opponent_draws_but_not_the_recorded_policy() {
        use crate::multi_cfr::{Counts, Deltas, PathSampler, Table, Traversal};
        let config = Config::new(&[500; 3], 50, 100).unwrap();
        let deck: Vec<u8> = (0..52).rev().collect();
        let run = |pressure| {
            let (mut deltas, mut counts) = (Deltas::default(), Counts::default());
            let mut state = Preflop(CashState { hand: Hand::from_deck(config, 0, &deck).unwrap(), tables: None, schema: KeySchema::History });
            Traversal { table: &Table::default(), deltas: &mut deltas, sampler: PathSampler(11), traverser: 0, weight: 2.,
                last_average_street: 3, counts: &mut counts, fork_depth: 0, prune_below: None, pressure }.run(&mut state);
            (deltas, counts)
        };
        let (plain, plain_counts) = run(None);
        let (forced, forced_counts) = run(Some(1.));
        assert_eq!(plain_counts.pressured, 0);
        assert!(forced_counts.pressured > 0);
        assert_ne!(plain_counts.nodes, forced_counts.nodes, "forced raises reach other histories");
        // Opponent rows still accumulate weight times the table policy (uniform here), never the forced raise.
        for deltas in [&plain, &forced] {
            for delta in deltas.values().filter(|d| d.actor != 0) {
                let average = delta.average().unwrap();
                let mass: f64 = average.iter().sum();
                assert!(average.iter().all(|a| (a - mass / average.len() as f64).abs() < 1e-9));
            }
        }
    }

    #[test]
    fn three_player_200bb_depth_is_part_of_the_key() {
        let deck: Vec<_> = (0..52).collect();
        let mut keys = Vec::new();
        for depth in [10000, 20000] {
            let config = Config::new(&[depth; 3], 50, 100).unwrap();
            let mut rotated = None;
            for button in 0..3 {
                let hand = Hand::from_deck(config, button, &deck).unwrap();
                let state = CashState { hand, tables: None, schema: KeySchema::History };
                let d = state.decision().unwrap();
                if let Some(key) = rotated { assert_eq!(d.key, key); }
                rotated = Some(d.key);
            }
            keys.push(rotated.unwrap());
        }
        assert_ne!(keys[0], keys[1]);
    }

    #[test]
    fn n_stacks_live_set_and_actor_label_are_in_the_key() {
        let config = Config::new(&[2000, 2000, 2000], 50, 100).unwrap();
        let hand = Hand::from_deck(config, 0, &(0..52).collect::<Vec<_>>()).unwrap();
        let mut observation = hand.observe(hand.actor().unwrap()).unwrap();
        let choices = menu(&observation);
        let cards = card_class(&observation, None);
        let original = payload(&observation, &cards, &choices);
        let mut players = observation.players.to_vec();
        players[1].folded = true;
        observation.players = &players;
        assert_ne!(original, payload(&observation, &cards, &choices));
        observation.players = hand.players();
        observation.config = Config::new(&[2000, 3000, 2000], 50, 100).unwrap();
        assert_ne!(original, payload(&observation, &cards, &choices));
        observation.config = config;
        let event = Event::Action {
            street: observation.street,
            actor: 0,
            action: Action {
                kind: Kind::Call,
                raise_to: 0,
            },
            paid: 100,
        };
        let history = [event];
        observation.history = &history;
        let first = payload(&observation, &cards, &choices);
        let second_history = [Event::Action {
            street: observation.street,
            actor: 1,
            action: Action {
                kind: Kind::Call,
                raise_to: 0,
            },
            paid: 100,
        }];
        observation.history = &second_history;
        assert_ne!(first, payload(&observation, &cards, &choices));
    }

    fn decide(hand: &Hand, schema: KeySchema) -> Decision {
        CashState { hand: hand.clone(), tables: None, schema }.decision().unwrap()
    }
    fn play(config: Config, button: usize, deck: &[u8], actions: &[Action]) -> Hand {
        let mut hand = Hand::from_deck(config, button, deck).unwrap();
        for &a in actions {
            hand.apply_mut(a).unwrap();
        }
        hand
    }
    const FOLD: Action = Action { kind: Kind::Fold, raise_to: 0 };
    const CALL: Action = Action { kind: Kind::Call, raise_to: 0 };
    const MIN_RAISE: Action = Action { kind: Kind::Raise, raise_to: 200 };

    #[test]
    fn live_order_keys_forget_which_earlier_seat_folded() {
        let config = Config::new(&[10000; 5], 50, 100).unwrap();
        let deck: Vec<u8> = (0..52).collect();
        // Button 0 acts after UTG (3) and MP (4); the same raise comes from a different seat.
        let a = play(config, 0, &deck, &[FOLD, MIN_RAISE]);
        let b = play(config, 0, &deck, &[MIN_RAISE, FOLD]);
        assert_eq!((a.actor(), b.actor()), (Some(0), Some(0)));
        assert_ne!(decide(&a, KeySchema::History).key, decide(&b, KeySchema::History).key);
        let (da, db) = (decide(&a, KeySchema::LiveOrder), decide(&b, KeySchema::LiveOrder));
        assert_eq!(da, db);
        assert_eq!(da.owner, 0, "the button is first among live players from the button");
        // Rows are keyed by (owner, street, actions), so merged decisions share one identity.
        let mut table = crate::multi_cfr::Table::default();
        table.insert(da.key, crate::multi_cfr::Entry::new(da, 3));
        table.get(&db.key).unwrap().check(db);
    }

    #[test]
    fn live_order_keys_keep_raises_price_cards_and_rotate_with_the_button() {
        let config = Config::new(&[10000; 5], 50, 100).unwrap();
        let deck: Vec<u8> = (0..52).collect();
        let key = |hand: &Hand| decide(hand, KeySchema::LiveOrder).key;
        let raised = play(config, 0, &deck, &[FOLD, MIN_RAISE]);
        let called = play(config, 0, &deck, &[FOLD, CALL]);
        let reraised = play(config, 0, &deck, &[MIN_RAISE, Action { kind: Kind::Raise, raise_to: 300 }, FOLD]);
        assert_ne!(key(&raised), key(&called), "a raise changes the raise count and price");
        assert_ne!(key(&raised), key(&reraised));
        // Seat button+1+i is dealt deck[i] and deck[n+i], so the button holds deck[4] and deck[9].
        let mut other_cards = deck.clone();
        other_cards.swap(4, 51);
        assert_ne!(key(&raised), key(&play(config, 0, &other_cards, &[FOLD, MIN_RAISE])));
        // A deck deals by seat relative to the button, so every button sees the same spot.
        let keys: std::collections::HashSet<_> = (0..5).map(|button| key(&play(config, button, &deck, &[FOLD, MIN_RAISE]))).collect();
        assert_eq!(keys.len(), 1);
        assert_eq!(KeySchema::from_name(LIVE_ORDER_SCHEMA), Some(KeySchema::LiveOrder));
        assert_eq!(KeySchema::from_name(SCHEMA), Some(KeySchema::History));
        assert_eq!(KeySchema::from_name("other"), None);
    }

    #[test]
    fn live_order_preflop_traversal_merges_keys_with_consistent_identities() {
        use crate::multi_cfr::{Counts, Deltas, PathSampler, Table, Traversal};
        use rand::SeedableRng;
        let config = Config::new(&[10000; 6], 50, 100).unwrap();
        let mut deck: Vec<u8> = (0..52).collect();
        deck.shuffle(&mut rand::rngs::StdRng::seed_from_u64(3));
        // One deal, so keys differ only by history; each root samples other opponent actions.
        let keys = |schema| {
            let mut keys = std::collections::HashSet::new();
            for root in 0..40 {
                let (mut deltas, mut counts) = (Deltas::default(), Counts::default());
                let hand = Hand::from_deck(config, 0, &deck).unwrap();
                let mut state = Preflop(CashState { hand, tables: None, schema });
                // Absorbing deltas checks owner, street and actions on every merged key.
                Traversal { table: &Table::default(), deltas: &mut deltas, sampler: PathSampler(root as u64), traverser: root % 6,
                    weight: 1., last_average_street: 3, counts: &mut counts, fork_depth: 0, prune_below: None, pressure: None }
                    .run(&mut state);
                keys.extend(deltas.into_keys());
            }
            keys.len()
        };
        let (history, live_order) = (keys(KeySchema::History), keys(KeySchema::LiveOrder));
        assert!(live_order < history, "{live_order} live-order keys against {history} history keys");
    }
    #[test]
    fn compact_records_biject_on_legal_multiway_histories() {
        use rand::{Rng, SeedableRng};
        use std::collections::HashMap;
        let mut forward = HashMap::new();
        let mut reverse = HashMap::new();
        let mut rng = rand::rngs::StdRng::seed_from_u64(327);
        let mut decisions = 0;
        for n in 2..=6 {
            for uneven in [false, true] {
                for depth in [2000, 10000] {
                    let stacks: Vec<u64> = (0..n)
                        .map(|i| if uneven { 50 + i as u64 * depth } else { depth })
                        .collect();
                    let config = Config::new(&stacks, 50, 100).unwrap();
                    for button in 0..n {
                        for _ in 0..20 {
                            let mut deck: Vec<u8> = (0..52).collect();
                            deck.shuffle(&mut rng);
                            let mut hand = Hand::from_deck(config, button, &deck).unwrap();
                            while let Some(actor) = hand.actor() {
                                let observation = hand.observe(actor).unwrap();
                                // Abstract card labels stand in for the pinned table in this byte-framing test.
                                let cards = if observation.board.is_empty() {
                                    card_class(&observation, None)
                                } else {
                                    vec![observation.street as u8, observation.hole[0] / 4, 0]
                                };
                                let actions = menu(&observation);
                                let old = payload(&observation, &cards, &actions);
                                let new = compact_payload(&observation, &cards);
                                if let Some(previous) = forward.insert(old.clone(), new.clone()) {
                                    assert_eq!(previous, new);
                                }
                                if let Some(previous) = reverse.insert(new, old.clone()) {
                                    assert_eq!(previous, old);
                                }
                                decisions += 1;
                                hand.apply_mut(actions[rng.gen_range(0..actions.len())].1)
                                    .unwrap();
                            }
                        }
                    }
                }
            }
        }
        assert!(decisions > 10_000);
    }

    #[test]
    fn compact_keys_retain_initial_configuration_and_schema_domains() {
        let deck: Vec<u8> = (0..52).collect();
        let mut keys = std::collections::HashSet::new();
        for stacks in [vec![2000; 3], vec![2000, 3000, 2000]] {
            let config = Config::new(&stacks, 50, 100).unwrap();
            for button in 0..3 {
                let hand = Hand::from_deck(config, button, &deck).unwrap();
                let view = hand.observe(hand.actor().unwrap()).unwrap();
                let cards = card_class(&view, None);
                let bytes = compact_payload(&view, &cards);
                if stacks[0] != stacks[1] {
                    assert!(keys.insert(bytes));
                }
                for schema in KeySchema::EXACT_HISTORY {
                    assert_eq!(KeySchema::from_name(schema.name()).unwrap(), schema);
                    assert_eq!(KeySchema::parse(schema.option()).unwrap(), schema);
                    let d = observation_decision_with_tables(schema, &view, None);
                    assert_eq!(
                        (d.owner, d.street, d.code),
                        (
                            (view.seat + 3 - button) % 3,
                            0,
                            menu(&view).iter().fold(0, |c, (label, _)| c | 1 << label)
                        )
                    );
                }
            }
        }
        assert!(KeySchema::from_name("v1").is_none());
        assert!(KeySchema::parse("compact-v99").is_err());
        let mut bytes = Vec::new();
        for number in [0, 127, 128, 16383, 16384, u64::MAX] {
            varint(&mut bytes, number);
        }
        let mut offset = 0;
        for expected in [0, 127, 128, 16383, 16384, u64::MAX] {
            let (mut actual, mut shift) = (0u64, 0);
            loop {
                let b = bytes[offset];
                offset += 1;
                actual |= ((b & 127) as u64) << shift;
                if b & 128 == 0 {
                    break;
                }
                shift += 7;
            }
            assert_eq!(actual, expected);
        }
        assert_eq!(offset, bytes.len());
    }
}


#[cfg(test)]
#[path = "multi_key_tests.rs"]
mod key_tests;
