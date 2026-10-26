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
pub const STACK_BUCKETS_SCHEMA: &str = "nplayer-stack-owner-buckets-equity-k50-v1";
pub const STACK_OWNER_SCHEMA: &str = "nplayer-stack-owner-summary-equity-k50-v1";
pub const MENU: &str = "min-pot-conditional-jam-v1";

/// How a decision's public history enters its information key. Released models use `History`.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum KeySchema {
    /// Every public action with its amounts, and every seat's chips.
    #[default]
    History,
    /// The live players' order and a capped summary of the betting (`live_order_payload`).
    LiveOrder,
    StackOwner,
    StackBuckets,
    CompactBlake,
    CompactXxh3,
    /// `LiveOrder` plus the hero's button-relative seat.
    LiveOrderSeat,
    /// `LiveOrder` with the current street's exact actions instead of its summary.
    LiveOrderStreet,
}
impl KeySchema {
    pub const ALL: [Self; 6] = [Self::History, Self::LiveOrder, Self::StackOwner, Self::StackBuckets, Self::CompactBlake, Self::CompactXxh3];
    /// Finer live-order keys; not part of the golden `ALL` set.
    pub const LIVE_ORDER_VARIANTS: [Self; 2] = [Self::LiveOrderSeat, Self::LiveOrderStreet];
    pub const EXACT_HISTORY: [Self; 3] = [Self::History, Self::CompactBlake, Self::CompactXxh3];
    pub fn option(self) -> &'static str {
        match self {
            Self::History => "v1", Self::LiveOrder => "live-order", Self::StackOwner => "stack-owner", Self::StackBuckets => "stack-buckets",
            Self::CompactBlake => "compact-blake2b-v2", Self::CompactXxh3 => "compact-xxh3-v2",
            Self::LiveOrderSeat => "live-order-seat", Self::LiveOrderStreet => "live-order-street",
        }
    }
    pub fn parse(value: &str) -> Result<Self, String> {
        if value == "history" { return Ok(Self::History); }
        Self::ALL.into_iter().chain(Self::LIVE_ORDER_VARIANTS).find(|s| s.option() == value || s.name() == value)
            .ok_or_else(|| format!("unsupported n-player key schema: {value}"))
    }
    pub fn is_compact(self) -> bool { matches!(self, Self::CompactBlake | Self::CompactXxh3) }

    pub fn name(self) -> &'static str {
        match self {
            KeySchema::History => SCHEMA,
            KeySchema::LiveOrder => LIVE_ORDER_SCHEMA,
            Self::StackOwner => STACK_OWNER_SCHEMA,
            Self::StackBuckets => STACK_BUCKETS_SCHEMA,
            Self::CompactBlake => "nplayer-button-history-equity-k50-compact-blake2b-v2",
            Self::CompactXxh3 => "nplayer-button-history-equity-k50-compact-xxh3-v2",
            Self::LiveOrderSeat => "nplayer-live-order-seat-summary-equity-k50-v1",
            Self::LiveOrderStreet => "nplayer-live-order-street-exact-equity-k50-v1",
        }
    }
    pub fn from_name(name: &str) -> Option<Self> {
        Self::ALL.into_iter().chain(Self::LIVE_ORDER_VARIANTS).find(|s| s.name() == name)
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
fn live_order_payload(observation: &Observation<'_>, cards: &[u8], code: u16, schema: KeySchema) -> (Vec<u8>, usize) {
    let n = observation.config.players();
    let by_button = |i: usize| (observation.button + i) % n;
    let live: Vec<usize> = (0..n).map(by_button).filter(|&p| !observation.players[p].folded).collect();
    let order = |seat: usize| live.iter().position(|&p| p == seat).map_or(u8::MAX, |i| i as u8);
    let street = observation.street as usize;
    let hero = order(observation.seat);
    let mut out = schema.name().as_bytes().to_vec();
    out.push(0);
    let all_in = live.iter().filter(|&&p| observation.players[p].stack == 0).count();
    out.extend_from_slice(&[n as u8, live.len() as u8, hero, street as u8, all_in as u8]);
    if schema == KeySchema::LiveOrderSeat {
        out.push(((observation.seat + n - observation.button) % n) as u8);
    }
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
    let mut exact = Vec::new();
    for event in observation.history {
        if let Event::Action { street: s, actor, action, .. } = event {
            let s = *s as usize;
            if action.kind == Kind::Raise {
                raises[s] = (raises[s] + 1).min(RAISE_CAP);
                last_raiser[s] = Some(*actor);
            }
            if s == street {
                actions = actions.saturating_add(1);
                exact.extend_from_slice(&[order(*actor), kind_code(action.kind)]);
                exact.extend_from_slice(&action.raise_to.to_le_bytes());
            }
        }
    }
    out.extend_from_slice(&raises[..=street]);
    let previous = street.checked_sub(1).and_then(|s| last_raiser[s]);
    out.push(previous.map_or(u8::MAX, order));
    if schema == KeySchema::LiveOrderStreet {
        // A folded actor's order is 255; the count frames the sequence.
        out.push(actions);
        out.extend_from_slice(&exact);
    } else {
        out.extend_from_slice(&[last_raiser[street].map_or(u8::MAX, order), actions]);
    }
    let legal = observation.legal.expect("only the acting seat has a key");
    let after_call: u64 = observation.players.iter().map(|p| p.contributed).sum::<u64>() + legal.call_amount;
    out.push(bucket(legal.call_amount, after_call, &PRICE_EDGES));
    out.push(cards.len() as u8);
    out.extend_from_slice(cards);
    out.extend_from_slice(&code.to_le_bytes());
    (out, hero as usize)
}

/// Conservative unequal-stack baseline. Preserve public chip ownership and
/// folded contributions; do not assume sorted SPR identifies side-pot exposure.
fn stack_owner_payload(o: &Observation<'_>, cards: &[u8], choices: &[(u8, Action)], code: u16) -> Vec<u8> {
    let (summary, _) = live_order_payload(o, cards, code, KeySchema::LiveOrder);
    let mut out = STACK_OWNER_SCHEMA.as_bytes().to_vec();
    out.push(0);
    out.extend_from_slice(&summary[LIVE_ORDER_SCHEMA.len()+1..]);
    let n = o.config.players();
    out.push(((o.seat+n-o.button)%n) as u8);
    out.extend_from_slice(&o.config.small_blind().to_le_bytes());
    out.extend_from_slice(&o.config.big_blind().to_le_bytes());
    for i in 0..n {
        let seat=(o.button+i)%n;
        let p=o.players[seat];
        for value in [o.config.stacks()[seat],p.stack,p.street_bet,p.contributed] {
            out.extend_from_slice(&value.to_le_bytes());
        }
        out.push(p.folded as u8);
    }
    out.push(choices.len() as u8);
    for (label,action) in choices {
        out.push(*label);
        out.push(kind_code(action.kind));
        out.extend_from_slice(&action.raise_to.to_le_bytes());
    }
    out
}

/// A zero tag plus positive ratio buckets; boundaries use exact integer comparisons.
const STACK_AMOUNT_EDGES: [(u64,u64);9] = [(1,16),(1,8),(1,4),(1,2),(1,1),(2,1),(4,1),(8,1),(16,1)];
fn stack_amount_bucket(value:u64, base:u64)->u8 {
    if value==0 {0} else {1+bucket(value,base,&STACK_AMOUNT_EDGES)}
}
fn comparison(a:u64,b:u64)->u8 { if a<b {0} else if a==b {1} else {2} }

/// Deliberately coarse public abstraction. Exact initial ownership and contribution
/// topology survive; numerical amounts/raise targets may differ inside a row.
fn stack_buckets_payload(o:&Observation<'_>,cards:&[u8],choices:&[(u8,Action)],code:u16)->Vec<u8> {
    let (summary,_)=live_order_payload(o,cards,code,KeySchema::LiveOrder);
    let mut out=STACK_BUCKETS_SCHEMA.as_bytes().to_vec();out.push(0);
    out.extend_from_slice(&summary[LIVE_ORDER_SCHEMA.len()+1..]);
    let n=o.config.players();let relative=|seat:usize|((seat+n-o.button)%n)as u8;
    out.extend_from_slice(&[n as u8,relative(o.seat)]);
    out.extend_from_slice(&o.config.small_blind().to_le_bytes());
    out.extend_from_slice(&o.config.big_blind().to_le_bytes());
    let pot:u64=o.players.iter().map(|p|p.contributed).sum();
    let base=pot.max(o.config.big_blind());
    out.push(bucket(pot,o.config.big_blind(),&POT_EDGES_BB.map(|e|(e,1))));
    for i in 0..n {
        let seat=(o.button+i)%n;let p=o.players[seat];
        out.extend_from_slice(&o.config.stacks()[seat].to_le_bytes());
        out.extend_from_slice(&[p.folded as u8,(p.stack==0) as u8]);
        for value in [p.stack,p.street_bet,p.contributed,p.contributed-p.street_bet] {
            out.push(stack_amount_bucket(value,base));
        }
    }
    for i in 0..n {for j in i+1..n {
        let a=o.players[(o.button+i)%n];let b=o.players[(o.button+j)%n];
        out.push(comparison(a.contributed,b.contributed));
        out.push(comparison(a.street_bet,b.street_bet));
    }}
    let mut aggressors=[u8::MAX;4];
    for event in o.history {
        if let Event::Action{street,actor,action,..}=event {
            if action.kind==Kind::Raise {aggressors[*street as usize]=relative(*actor);}
        }
    }
    out.extend_from_slice(&aggressors[..=o.street as usize]);
    let legal=o.legal.expect("acting observation");let hero=o.players[o.seat];
    out.push((legal.call_amount>0 && legal.call_amount==hero.stack)as u8);
    let matched=hero.street_bet+legal.call_amount;
    let after=(pot+legal.call_amount).max(o.config.big_blind());
    out.push(choices.len()as u8);
    for (label,action)in choices {
        out.extend_from_slice(&[*label,kind_code(action.kind),
            (action.kind==Kind::Raise && action.raise_to==hero.stack+hero.street_bet)as u8,
            stack_amount_bucket(action.raise_to.saturating_sub(matched),after)]);
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
        KeySchema::LiveOrder | KeySchema::LiveOrderSeat | KeySchema::LiveOrderStreet => {
            let (bytes, live_owner) = live_order_payload(observation, cards, code, schema);
            owner = live_owner;
            crate::key::digest16(&bytes)
        },
        KeySchema::StackOwner => crate::key::digest16(&stack_owner_payload(observation, cards, choices, code)),
        KeySchema::StackBuckets => crate::key::digest16(&stack_buckets_payload(observation,cards,choices,code)),
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
    pub fn with_schema(hand: Hand, tables: &'static EquityTables, schema: KeySchema) -> Self {
        Self { hand, tables: Some(tables), schema }
    }
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

    #[test]
    fn live_order_variants_add_the_seat_or_the_exact_street() {
        let config = Config::new(&[10000; 5], 50, 100).unwrap();
        let deck: Vec<u8> = (0..52).collect();
        let a = play(config, 0, &deck, &[FOLD, MIN_RAISE]);
        let b = play(config, 0, &deck, &[MIN_RAISE, FOLD]);
        let key = |h: &Hand, s| decide(h, s).key;
        for variant in KeySchema::LIVE_ORDER_VARIANTS {
            assert_ne!(key(&a, variant), key(&a, KeySchema::LiveOrder), "{variant:?} has its own domain");
            assert_eq!(decide(&a, variant).owner, decide(&a, KeySchema::LiveOrder).owner);
            let rotated: std::collections::HashSet<_> = (0..5).map(|button| key(&play(config, button, &deck, &[FOLD, MIN_RAISE]), variant)).collect();
            assert_eq!(rotated.len(), 1, "{variant:?} is button-relative");
            assert_eq!(KeySchema::parse(variant.option()), Ok(variant));
            assert_eq!(KeySchema::from_name(variant.name()), Some(variant));
        }
        // Same hero seat: the seat variant still merges who folded earlier; the exact street doesn't.
        assert_eq!(key(&a, KeySchema::LiveOrderSeat), key(&b, KeySchema::LiveOrderSeat));
        assert_ne!(key(&a, KeySchema::LiveOrderStreet), key(&b, KeySchema::LiveOrderStreet));
    }

    #[test]
    fn the_seat_variant_splits_exactly_the_live_order_keys_shared_by_different_seats() {
        use rand::SeedableRng;
        let config = Config::new(&[10000; 6], 50, 100).unwrap();
        let mut rng = rand::rngs::StdRng::seed_from_u64(9);
        let mut by_key: std::collections::HashMap<_, std::collections::HashSet<_>> = Default::default();
        let mut seat_keys = std::collections::HashMap::new();
        for _ in 0..3000 {
            let mut deck: Vec<u8> = (0..52).collect();
            deck.shuffle(&mut rng);
            let mut hand = Hand::from_deck(config, rng.gen_range(0..6), &deck).unwrap();
            while hand.board().is_empty() && hand.actor().is_some() {
                let seat = (hand.actor().unwrap() + 6 - hand.button()) % 6;
                let live = decide(&hand, KeySchema::LiveOrder);
                let with_seat = decide(&hand, KeySchema::LiveOrderSeat).key;
                by_key.entry(live.key).or_default().insert(seat);
                assert_eq!(*seat_keys.entry((live.key, seat)).or_insert(with_seat), with_seat);
                let observation = hand.observe(hand.actor().unwrap()).unwrap();
                let action = menu(&observation)[rng.gen_range(0..live.len())].1;
                hand.apply_mut(action).unwrap();
            }
        }
        assert!(by_key.values().any(|seats| seats.len() > 1), "live-order keys merge different hero seats");
        let distinct: std::collections::HashSet<_> = seat_keys.values().collect();
        assert_eq!(distinct.len(), seat_keys.len(), "one seat-variant key per live-order key and seat");
    }
}


#[cfg(test)]
#[path = "multi_key_tests.rs"]
mod key_tests;

#[cfg(test)]
mod stack_owner_tests {
    use super::*;
    fn key(h:&Hand,s:KeySchema)->Decision {
        let o=h.observe(h.actor().unwrap()).unwrap();
        observation_decision_with_tables(s,&o,None)
    }
    #[test]
    fn stack_ownership_and_hidden_worlds() {
        let deck:Vec<u8>=(0..52).collect();
        let a=Hand::from_deck(Config::new(&[2000,5000,10000],50,100).unwrap(),0,&deck).unwrap();
        let b=Hand::from_deck(Config::new(&[10000,5000,2000],50,100).unwrap(),0,&deck).unwrap();
        assert_eq!(key(&a,KeySchema::LiveOrder),key(&b,KeySchema::LiveOrder));
        assert_ne!(key(&a,KeySchema::StackOwner).key,key(&b,KeySchema::StackOwner).key);
        let mut hidden=deck.clone();hidden.swap(0,1);hidden.swap(6,51);
        let c=Hand::from_deck(a.config(),0,&hidden).unwrap();
        assert_eq!(key(&a,KeySchema::StackOwner),key(&c,KeySchema::StackOwner));
    }
    #[test]
    fn rotation_preserves_button_relative_chips_cards_and_menu() {
        let deck:Vec<u8>=(0..52).collect();
        let a=Hand::from_deck(Config::new(&[2000,5000,10000],50,100).unwrap(),0,&deck).unwrap();
        let b=Hand::from_deck(Config::new(&[10000,2000,5000],50,100).unwrap(),1,&deck).unwrap();
        let da=key(&a,KeySchema::StackOwner);let db=key(&b,KeySchema::StackOwner);
        assert_eq!(da.key,db.key);assert_eq!(da.owner,db.owner);assert_eq!(da.code,db.code);
        assert_eq!(crate::multi_checkpoint::key_hex(&da.key),"5c806ad4cb68fd3515ec4360cb6a3997");
        assert_ne!(da.actor,db.actor);
    }
    #[test]
    fn folded_contributions_and_menu_targets_are_not_lost() {
        let deck:Vec<u8>=(0..52).collect();
        let h=Hand::from_deck(Config::new(&[2000,5000,10000],50,100).unwrap(),0,&deck).unwrap();
        let o=h.observe(0).unwrap();let choices=menu(&o);let cards=card_class(&o,None);
        let code=choices.iter().fold(0,|c,(label,_)|c|1<<label);
        let base=stack_owner_payload(&o,&cards,&choices,code);
        let mut players=o.players.to_vec();players[1].folded=true;
        let mut changed=h.observe(0).unwrap();changed.players=&players;
        let folded=stack_owner_payload(&changed,&cards,&choices,code);
        let mut other=players.clone();other[1].contributed+=100;
        changed.players=&other;
        assert_ne!(folded,stack_owner_payload(&changed,&cards,&choices,code));
        let mut menu=choices.clone();menu.last_mut().unwrap().1.raise_to+=1;
        assert_ne!(base,stack_owner_payload(&o,&cards,&menu,code));
    }
}

#[cfg(test)]
mod stack_buckets_tests {
    use super::*;
    fn key(h: &Hand) -> Decision {
        observation_decision_with_tables(KeySchema::StackBuckets, &h.observe(h.actor().unwrap()).unwrap(), None)
    }
    fn hand(stacks: &[u64], button: usize, deck: &[u8]) -> Hand {
        Hand::from_deck(Config::new(stacks, 50, 100).unwrap(), button, deck).unwrap()
    }
    #[test]
    fn ratio_zero_boundaries_and_large_products() {
        assert_eq!(stack_amount_bucket(0,1600),0);
        assert_eq!(stack_amount_bucket(1,1600),1);
        for (i,(num,den)) in STACK_AMOUNT_EDGES.iter().enumerate() {
            let boundary=1600*num/den;
            assert_eq!(stack_amount_bucket(boundary-1,1600),i as u8+1);
            assert_eq!(stack_amount_bucket(boundary,1600),i as u8+2);
        }
        assert_eq!(stack_amount_bucket(u64::MAX,u64::MAX),6);
    }
    #[test]
    fn legal_nearby_raise_histories_share_but_targets_are_current() {
        let deck:Vec<_>=(0..52).collect();
        let mut a=hand(&[2000,5000,10000],0,&deck);let mut b=a.clone();
        a.apply_mut(Action{kind:Kind::Raise,raise_to:200}).unwrap();
        b.apply_mut(Action{kind:Kind::Raise,raise_to:201}).unwrap();
        assert_eq!(key(&a),key(&b));
        let oa=a.observe(a.actor().unwrap()).unwrap();let ob=b.observe(b.actor().unwrap()).unwrap();
        assert_ne!(menu(&oa),menu(&ob));
        assert_eq!(menu(&oa).iter().map(|(l,a)|(*l,a.kind)).collect::<Vec<_>>(),menu(&ob).iter().map(|(l,a)|(*l,a.kind)).collect::<Vec<_>>());
        assert_ne!(observation_decision_with_tables(KeySchema::StackOwner,&oa,None).key,
                   observation_decision_with_tables(KeySchema::StackOwner,&ob,None).key);
        for (_,action)in menu(&oa) {let mut branch=a.clone();branch.apply_mut(action).unwrap();}
        for (_,action)in menu(&ob) {let mut branch=b.clone();branch.apply_mut(action).unwrap();}
    }
    #[test]
    fn ownership_hidden_worlds_and_rotation() {
        let deck:Vec<_>=(0..52).collect();
        let a=hand(&[2000,5000,10000],0,&deck);
        let b=hand(&[10000,5000,2000],0,&deck);
        assert_ne!(key(&a).key,key(&b).key);
        let mut hidden=deck.clone();hidden.swap(0,1);hidden.swap(6,51);
        assert_eq!(key(&a),key(&hand(&[2000,5000,10000],0,&hidden)));
        let rotated=key(&hand(&[10000,2000,5000],1,&deck));
        assert_eq!((key(&a).key,key(&a).owner,key(&a).code),(rotated.key,rotated.owner,rotated.code));
    }
    #[test]
    fn contribution_equality_folded_context_and_menu_contract_do_not_merge() {
        let deck:Vec<_>=(0..52).collect();let h=hand(&[2000,5000,10000],0,&deck);
        let mut o=h.observe(0).unwrap();let cards=card_class(&o,None);
        let choices=menu(&o);let code=choices.iter().fold(0,|c,(l,_)|c|1<<l);
        let mut players=o.players.to_vec();players[1].folded=true;players[0].contributed=50;
        o.players=&players;
        let equal=stack_buckets_payload(&o,&cards,&choices,code);
        // A one-chip change is within the same ratio buckets but breaks contribution equality.
        let mut unequal=players.clone();unequal[0].contributed=51;
        o.players=&unequal;assert_ne!(equal,stack_buckets_payload(&o,&cards,&choices,code));
        o.players=&players;
        let mut live=players.clone();live[1].folded=false;
        o.players=&live;assert_ne!(equal,stack_buckets_payload(&o,&cards,&choices,code));
        let mut changed=choices.clone();changed[0].0=1;
        assert_ne!(stack_buckets_payload(&o,&cards,&choices,code),stack_buckets_payload(&o,&cards,&changed,code));
        let mut changed=choices.clone();changed.last_mut().unwrap().1.raise_to=o.players[0].stack+o.players[0].street_bet;
        assert_ne!(stack_buckets_payload(&o,&cards,&choices,code),stack_buckets_payload(&o,&cards,&changed,code));
    }
}
