//! Public-only cash-game adapter to the same traversal used by Kuhn and Leduc.
use crate::cards::EquityTables;
use crate::game::Kind;
use crate::multi_cfr::{Decision, Game, State};
use crate::nplayer::{Action, Config, Event, Hand, Observation, Saved};
use rand::{seq::SliceRandom, Rng};
use serde_json::{json, Value};

pub const SCHEMA: &str = "nplayer-button-live-actor-history-equity-k50-v1";
pub const MENU: &str = "min-pot-conditional-jam-v1";

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
    observation_decision_with_tables(observation, Some(tables))
}
fn observation_decision_with_tables(
    observation: &Observation<'_>,
    tables: Option<&EquityTables>,
) -> Decision {
    let choices = menu(observation);
    let card_class = card_class(observation, tables);
    let bytes = payload(observation, &card_class, &choices);
    let key = crate::key::digest16(&bytes);
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
}
#[derive(Clone)]
pub struct CashState {
    pub hand: Hand,
    tables: Option<&'static EquityTables>,
}
impl Game for CashGame {
    type State = CashState;
    fn players(&self) -> usize {
        self.config.players()
    }
    fn identity(&self) -> Value {
        json!({"schema":SCHEMA,"game":"nlhe-cash","players":self.players(),"stacks":self.config.stacks(),
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
        }
    }
}
impl CashState {
    pub fn new(hand: Hand, tables: &'static EquityTables) -> Self {
        Self {
            hand,
            tables: Some(tables),
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
        Some(observation_decision_with_tables(&observation, self.tables))
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
                let mut state = CashState { hand, tables: None };
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
                    let mut state = CashState { hand: Hand::from_deck(config, rng.gen_range(0..n), &deck).unwrap(), tables: None };
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
            let mut state = Preflop(CashState { hand: Hand::from_deck(config, 0, &deck).unwrap(), tables: None });
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
                let state = CashState { hand, tables: None };
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
}
