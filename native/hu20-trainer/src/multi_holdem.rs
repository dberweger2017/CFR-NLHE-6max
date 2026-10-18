//! Public-only cash-game adapter to the same traversal used by Kuhn and Leduc.
use crate::cards::EquityTables;
use crate::game::Kind;
use crate::multi_cfr::{Decision, Game, State};
use crate::nplayer::{Action, Config, Event, Hand, Observation, Saved};
use rand::{seq::SliceRandom, Rng};
use serde_json::{json, Value};

pub const SCHEMA: &str = "nplayer-button-live-actor-history-equity-k50-v1";
pub const MENU: &str = "min-pot-conditional-jam-v1";

/// Key bytes are versioned separately from sampling and checkpoint framing.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum KeySchema {
    #[default]
    V1,
    CompactBlake,
    CompactXxh3,
}
impl KeySchema {
    pub const ALL: [Self; 3] = [Self::V1, Self::CompactBlake, Self::CompactXxh3];
    pub fn option(self) -> &'static str {
        match self {
            Self::V1 => "v1",
            Self::CompactBlake => "compact-blake2b-v2",
            Self::CompactXxh3 => "compact-xxh3-v2",
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            Self::V1 => SCHEMA,
            Self::CompactBlake => "nplayer-button-history-equity-k50-compact-blake2b-v2",
            Self::CompactXxh3 => "nplayer-button-history-equity-k50-compact-xxh3-v2",
        }
    }
    pub fn from_name(value: &str) -> Result<Self, String> {
        Self::ALL
            .into_iter()
            .find(|s| s.name() == value)
            .ok_or_else(|| format!("unsupported n-player schema identity: {value}"))
    }
    pub fn parse(value: &str) -> Result<Self, String> {
        Self::ALL
            .into_iter()
            .find(|s| s.option() == value || s.name() == value)
            .ok_or_else(|| format!("unsupported n-player key schema: {value}"))
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

/// The policy boundary accepts only the acting seat's immutable observation.
pub fn observation_decision(observation: &Observation<'_>, tables: &EquityTables) -> Decision {
    observation_decision_schema(observation, tables, KeySchema::V1)
}
pub fn observation_decision_schema(
    observation: &Observation<'_>,
    tables: &EquityTables,
    schema: KeySchema,
) -> Decision {
    decision_with_schema(observation, Some(tables), schema)
}

/// Diagnostic path only; the benchmark never uses this extra encoding work.
pub fn observation_key_variants(
    observation: &Observation<'_>,
    tables: &EquityTables,
) -> [Decision; 3] {
    let choices = menu(observation);
    let cards = card_class(observation, Some(tables));
    let legacy = crate::key::digest16(&payload(observation, &cards, &choices));
    let compact = compact_payload(observation, &cards);
    let keys = [
        legacy,
        crate::key::digest16(&compact),
        xxhash_rust::xxh3::xxh3_128(&compact).to_le_bytes(),
    ];
    keys.map(|key| make_decision(observation, &choices, key))
}

fn decision_with_schema(
    observation: &Observation<'_>,
    tables: Option<&EquityTables>,
    schema: KeySchema,
) -> Decision {
    let choices = menu(observation);
    let cards = card_class(observation, tables);
    let key = match schema {
        KeySchema::V1 => crate::key::digest16(&payload(observation, &cards, &choices)),
        KeySchema::CompactBlake => crate::key::digest16(&compact_payload(observation, &cards)),
        KeySchema::CompactXxh3 => {
            xxhash_rust::xxh3::xxh3_128(&compact_payload(observation, &cards)).to_le_bytes()
        }
    };
    make_decision(observation, &choices, key)
}
fn make_decision(
    observation: &Observation<'_>,
    choices: &[(u8, Action)],
    key: crate::cfr::Key,
) -> Decision {
    let n = observation.config.players();
    Decision {
        key,
        actor: observation.seat,
        owner: (observation.seat + n - observation.button) % n,
        street: observation.street as usize,
        code: choices.iter().fold(0, |c, (label, _)| c | 1 << label),
    }
}

pub struct CashGame {
    pub config: Config,
    pub tables: &'static EquityTables,
    pub key_schema: KeySchema,
}
#[derive(Clone)]
pub struct CashState {
    pub hand: Hand,
    tables: Option<&'static EquityTables>,
    key_schema: KeySchema,
}
impl Game for CashGame {
    type State = CashState;
    fn players(&self) -> usize {
        self.config.players()
    }
    fn identity(&self) -> Value {
        json!({"schema":self.key_schema.name(),"game":"nlhe-cash","players":self.players(),"stacks":self.config.stacks(),
            "small_blind":self.config.small_blind(),"big_blind":self.config.big_blind(),"menu":MENU,
            "card_tables":self.tables.sha256,"utility_unit":"big-blind"})
    }
    fn sample(&self, rng: &mut rand::rngs::StdRng) -> CashState {
        let mut deck: Vec<u8> = (0..52).collect();
        deck.shuffle(rng);
        let button = rng.gen_range(0..self.players());
        CashState {
            hand: Hand::from_deck(self.config, button, &deck).unwrap(),
            tables: Some(self.tables),
            key_schema: self.key_schema,
        }
    }
}
impl CashState {
    pub fn new(hand: Hand, tables: &'static EquityTables) -> Self {
        Self {
            hand,
            tables: Some(tables),
            key_schema: KeySchema::V1,
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
        Some(decision_with_schema(
            &observation,
            self.tables,
            self.key_schema,
        ))
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
                let mut state = CashState {
                    hand,
                    tables: None,
                    key_schema: KeySchema::V1,
                };
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
                for schema in KeySchema::ALL {
                    assert_eq!(KeySchema::from_name(schema.name()).unwrap(), schema);
                    assert_eq!(KeySchema::parse(schema.option()).unwrap(), schema);
                    let d = decision_with_schema(&view, None, schema);
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
        assert!(KeySchema::from_name("v1").is_err());
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
