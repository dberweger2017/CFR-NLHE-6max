//! How a live-order model sees a table it was not trained at: docs/openpoker-phantom-depth.md.
//!
//! A table with fewer players than the model's becomes the model's table after phantom early
//! positions fold preflop: blinds, pot, positions and action order are then identical, so the
//! projected observation equals the one a real hand with those folds would show. The model's own
//! configuration replaces the table's, while every live stack stays real; live-order keys read
//! only the player count and big blind from the configuration, never the initial stacks, so the
//! key is computed from the real chips. Heads-up is not a folded-to-the-blinds hand (the button
//! posts the small blind and acts last after the flop) and is refused.
use crate::game::{Kind, Street};
use crate::multi_holdem::KeySchema;
use crate::nplayer::{Action, Config, Event, Legal, Observation, Player, MAX_PLAYERS};

/// An owned observation in the model's frame.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Projected {
    config: Config,
    seat: usize,
    button: usize,
    hole: [u8; 2],
    board: Vec<u8>,
    street: Street,
    players: [Player; MAX_PLAYERS],
    actor: Option<usize>,
    legal: Option<Legal>,
    history: Vec<Event>,
}

impl Projected {
    pub fn observation(&self) -> Observation<'_> {
        Observation {
            config: self.config,
            seat: self.seat,
            button: self.button,
            hole: self.hole,
            board: &self.board,
            street: self.street,
            players: &self.players[..self.config.players()],
            actor: self.actor,
            legal: self.legal,
            history: &self.history,
        }
    }
}

/// Only schemas whose keys ignore initial stacks may be projected.
pub fn supports(schema: KeySchema) -> bool {
    schema == KeySchema::LiveOrder
}

/// Checks a model configuration against a table once, before play.
pub fn compatible(model: Config, table: Config) -> Result<(), String> {
    let (m, n) = (model.players(), table.players());
    if (model.small_blind(), model.big_blind()) != (table.small_blind(), table.big_blind()) {
        return Err("projection keeps the blinds".into());
    }
    if m < n || (m > n && n < 3) {
        return Err("projection adds phantom early positions to three or more players only".into());
    }
    if model.stacks().iter().any(|&s| s != model.stacks()[0]) {
        return Err("projection needs an equal-stack model".into());
    }
    Ok(())
}

/// The model-frame observation of the table's `view`. Model frame: button at seat 0, the
/// table's button, blinds and early seats in order, phantom seats at the first positions after
/// the big blind, each folding preflop before any real action.
pub fn project(view: &Observation<'_>, model: Config) -> Result<Projected, String> {
    compatible(model, view.config)?;
    let (m, n) = (model.players(), view.config.players());
    let phantoms = m - n;
    let frame = |seat: usize| {
        let position = (seat + n - view.button) % n;
        if position < 3 { position } else { position + phantoms }
    };
    let mut players = [Player::default(); MAX_PLAYERS];
    for seat in 0..n {
        players[frame(seat)] = view.players[seat];
    }
    let mut history = Vec::with_capacity(view.history.len() + phantoms);
    for p in 3..3 + phantoms {
        players[p] = Player { stack: model.stacks()[p], street_bet: 0, contributed: 0, folded: true };
        history.push(Event::Action {
            street: Street::Preflop,
            actor: p,
            action: Action { kind: Kind::Fold, raise_to: 0 },
            paid: 0,
        });
    }
    history.extend(view.history.iter().map(|event| match *event {
        Event::Action { street, actor, action, paid } => Event::Action { street, actor: frame(actor), action, paid },
        board => board,
    }));
    Ok(Projected {
        config: model,
        seat: frame(view.seat),
        button: 0,
        hole: view.hole,
        board: view.board.to_vec(),
        street: view.street,
        players,
        actor: view.actor.map(frame),
        legal: view.legal,
        history,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::multi_holdem::menu;
    use crate::nplayer::Hand;
    use rand::{seq::SliceRandom, Rng, SeedableRng};

    /// Plays the table hand and, alongside, a real model-size hand whose phantom seats fold
    /// first; every table decision's projection must equal the real hand's observation, apart
    /// from the private cards and board, which come from the table.
    fn compare(table: Config, model: Config, button: usize, seed: u64) -> usize {
        let mut rng = rand::rngs::StdRng::seed_from_u64(seed);
        let mut deck: Vec<u8> = (0..52).collect();
        deck.shuffle(&mut rng);
        let mut small = Hand::from_deck(table, button, &deck).unwrap();
        let mut large = Hand::from_deck(model, 0, &deck).unwrap();
        let (n, m) = (table.players(), model.players());
        for _ in 0..m - n {
            large.apply_mut(Action { kind: Kind::Fold, raise_to: 0 }).unwrap();
        }
        let mut decisions = 0;
        while let Some(actor) = small.actor() {
            let view = small.observe(actor).unwrap();
            let projected = project(&view, model).unwrap();
            let truth = large.observe(large.actor().unwrap()).unwrap();
            let mut expected = truth;
            expected.hole = view.hole;
            expected.board = view.board;
            assert_eq!(projected.observation(), expected, "decision {decisions}");
            let choices = menu(&view);
            assert_eq!(menu(&projected.observation()), choices);
            let action = choices[rng.gen_range(0..choices.len())].1;
            small.apply_mut(action).unwrap();
            large.apply_mut(action).unwrap();
            decisions += 1;
        }
        assert!(large.finished());
        decisions
    }

    #[test]
    fn projection_equals_a_real_hand_with_phantom_folds() {
        let mut decisions = 0;
        for n in 3..=6 {
            for stack in [2000, 10000] {
                let table = Config::new(&vec![stack; n], 50, 100).unwrap();
                let model = Config::new(&[stack; 6], 50, 100).unwrap();
                for button in 0..n {
                    for seed in 0..40 {
                        decisions += compare(table, model, button, seed * 7 + n as u64);
                    }
                }
            }
        }
        assert!(decisions > 5000);
    }

    #[test]
    fn unequal_and_other_depth_tables_keep_their_real_chips() {
        // Equal stacks only in the model; the table's real chips must cross unchanged.
        let table = Config::new(&[2500, 10000, 15000, 7000], 50, 100).unwrap();
        let model = Config::new(&[10000; 6], 50, 100).unwrap();
        let deck: Vec<u8> = (0..52).collect();
        let hand = Hand::from_deck(table, 1, &deck).unwrap();
        let view = hand.observe(hand.actor().unwrap()).unwrap();
        let p = project(&view, model).unwrap();
        let o = p.observation();
        assert_eq!(o.config, model);
        let live: Vec<u64> = o.players.iter().filter(|q| !q.folded).map(|q| q.stack + q.contributed).collect();
        let mut real: Vec<u64> = table.stacks().to_vec();
        let mut seen = live.clone();
        real.sort_unstable();
        seen.sort_unstable();
        assert_eq!(seen, real);
        assert_eq!(o.legal, view.legal);
    }

    #[test]
    fn live_order_keys_ignore_configured_initial_stacks() {
        let table = Config::new(&[5000; 6], 50, 100).unwrap();
        let other = Config::new(&[20000; 6], 50, 100).unwrap();
        let mut rng = rand::rngs::StdRng::seed_from_u64(3);
        let mut checked = 0;
        for seed in 0..60 {
            let mut deck: Vec<u8> = (0..52).collect();
            deck.shuffle(&mut rand::rngs::StdRng::seed_from_u64(seed));
            let mut hand = Hand::from_deck(table, seed as usize % 6, &deck).unwrap();
            while let Some(actor) = hand.actor() {
                let view = hand.observe(actor).unwrap();
                let mut moved = hand.observe(actor).unwrap();
                moved.config = other;
                let key = |schema, o: &Observation<'_>| crate::multi_holdem::decision_with_cards(schema, o, &[7, 1]).key;
                assert_eq!(key(KeySchema::LiveOrder, &view), key(KeySchema::LiveOrder, &moved));
                assert_ne!(key(KeySchema::History, &view), key(KeySchema::History, &moved));
                let choices = menu(&view);
                hand.apply_mut(choices[rng.gen_range(0..choices.len())].1).unwrap();
                checked += 1;
            }
        }
        assert!(checked > 300);
    }

    #[test]
    fn heads_up_mismatched_blinds_and_unequal_models_refuse() {
        let model = Config::new(&[10000; 6], 50, 100).unwrap();
        assert!(compatible(model, Config::new(&[10000; 2], 50, 100).unwrap()).is_err());
        assert!(compatible(model, Config::new(&[10000; 4], 25, 50).unwrap()).is_err());
        assert!(compatible(Config::new(&[10000; 4], 50, 100).unwrap(), Config::new(&[10000; 5], 50, 100).unwrap()).is_err());
        assert!(compatible(Config::new(&[10000, 5000, 10000], 50, 100).unwrap(), Config::new(&[10000; 3], 50, 100).unwrap()).is_err());
        assert!(compatible(Config::new(&[10000; 2], 50, 100).unwrap(), Config::new(&[5000; 2], 50, 100).unwrap()).is_ok());
        assert!(supports(KeySchema::LiveOrder) && !supports(KeySchema::History));
    }
}
