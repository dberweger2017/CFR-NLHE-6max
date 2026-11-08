//! Deep CFR traversals over the menu abstraction (docs/neural-deep-cfr.md).
//!
//! One traversal deals a root (a player count from the run's list, wide-grid stacks, a shuffled
//! deck, a button and a traverser), then walks the hand by external sampling:
//! - at the traverser's decisions every menu action is explored, and the sampled regrets
//!   `v(a) − v` become one advantage sample;
//! - at other seats' decisions one action is drawn from the current strategy, which becomes one
//!   strategy sample.
//!
//! The current strategy is regret matching on the advantage network's outputs at the acting seat's
//! `policy_features` (quantized, as the networks train on them). Samples carry the iteration, which
//! is their linear-CFR weight. Everything is a function of (seed, iteration, traversal index).
use crate::cards::EquityTables;
use crate::multi_arena::stream_seed;
use crate::multi_holdem::menu;
use crate::multi_stacks::{live_draw, DepthGrid};
use crate::nplayer::Hand;
use crate::policy_features::{self as features, ACTIONS};
use crate::policy_network::Fast;
use rand::{seq::SliceRandom, Rng, SeedableRng};

pub const MAGIC: &[u8; 8] = b"NPDCF001";
pub const FORMAT: &str = "nplayer-deep-cfr-samples-v1";
pub const ADVANTAGE: u8 = 0;
pub const STRATEGY: u8 = 1;
/// A traversal that runs past this many nodes is an error, not a silent truncation.
pub const NODE_LIMIT: u64 = 50_000_000;

/// kind u8, players u8, street u8, legal mask u8, iteration u32, six f32 targets, features u8.
pub fn record_bytes() -> usize {
    8 + 4 * ACTIONS + features::len()
}
pub fn record_layout() -> serde_json::Value {
    serde_json::json!(["kind u8 (0 advantage: sampled regrets; 1 strategy: current strategy)", "players u8", "street u8",
        "legal_mask u8", "iteration u32 (linear weight)", "targets 6 f32 by menu label", "features u8 (x/255)"])
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Counts {
    pub traversals: u64,
    pub nodes: u64,
    pub terminals: u64,
    pub advantage: u64,
    pub strategy: u64,
}
impl Counts {
    pub fn add(&mut self, o: &Counts) {
        self.traversals += o.traversals;
        self.nodes += o.nodes;
        self.terminals += o.terminals;
        self.advantage += o.advantage;
        self.strategy += o.strategy;
    }
}

/// A traversal root: the dealt hand, the traverser and the traversal's own random stream.
pub fn root(seed: u64, iteration: u64, index: u64, players: &[usize]) -> Result<(Hand, usize, rand::rngs::StdRng), String> {
    if players.is_empty() || players.iter().any(|n| !(2..=6).contains(n)) {
        return Err("player counts are 2..=6".into());
    }
    let mut rng = rand::rngs::StdRng::seed_from_u64(stream_seed(seed, b"deep-cfr", iteration, index));
    let n = players[rng.gen_range(0..players.len())];
    let config = live_draw(n, DepthGrid::Wide, &mut rng, |_| {});
    let mut deck: Vec<u8> = (0..52).collect();
    deck.shuffle(&mut rng);
    let button = rng.gen_range(0..n);
    let traverser = rng.gen_range(0..n);
    Ok((Hand::from_deck(config, button, &deck)?, traverser, rng))
}

pub struct Traversal<'a> {
    pub net: &'a Fast,
    pub tables: &'a EquityTables,
    pub iteration: u32,
    pub out: Vec<u8>,
    pub counts: Counts,
    scratch: [Vec<f32>; 2],
}
impl<'a> Traversal<'a> {
    pub fn new(net: &'a Fast, tables: &'a EquityTables, iteration: u32) -> Self {
        Self { net, tables, iteration, out: Vec::new(), counts: Counts::default(), scratch: [Vec::new(), Vec::new()] }
    }
    /// Runs traversal `index` of `iteration`; returns the traverser's value in big blinds.
    pub fn run(&mut self, seed: u64, index: u64, players: &[usize]) -> Result<f64, String> {
        let (mut hand, traverser, mut rng) = root(seed, self.iteration as u64, index, players)?;
        self.counts.traversals += 1;
        self.visit(&mut hand, traverser, &mut rng)
    }
    fn record(&mut self, kind: u8, players: usize, street: usize, legal: u8, targets: &[f64; ACTIONS], bytes: &[u8]) {
        self.out.extend_from_slice(&[kind, players as u8, street as u8, legal]);
        self.out.extend_from_slice(&self.iteration.to_le_bytes());
        for t in targets {
            self.out.extend_from_slice(&(*t as f32).to_le_bytes());
        }
        self.out.extend_from_slice(bytes);
    }
    fn visit(&mut self, hand: &mut Hand, traverser: usize, rng: &mut rand::rngs::StdRng) -> Result<f64, String> {
        self.counts.nodes += 1;
        if self.counts.nodes > NODE_LIMIT {
            return Err("traversal node limit".into());
        }
        let Some(actor) = hand.actor() else {
            self.counts.terminals += 1;
            let s = hand.settlement().ok_or("finished hand without settlement")?;
            return Ok(s.rewards[traverser] as f64 / hand.config().big_blind() as f64);
        };
        let view = hand.observe(actor)?;
        let choices = menu(&view);
        let legal = features::legal_mask(&view);
        let bytes = features::quantize(&features::encode(&view, Some(self.tables))?);
        let sigma = self.net.strategy(&bytes, legal, &mut self.scratch);
        let players = hand.config().players();
        let street = view.street as usize;
        if actor != traverser {
            self.record(STRATEGY, players, street, legal, &sigma, &bytes);
            self.counts.strategy += 1;
            let draw: f64 = rng.gen();
            let mut sum = 0.;
            let mut pick = None;
            for (i, (label, _)) in choices.iter().enumerate() {
                let p = sigma[*label as usize];
                if p > 0. {
                    pick = Some(i);
                    sum += p;
                    if draw < sum {
                        break;
                    }
                }
            }
            let action = choices[pick.ok_or("empty strategy")?].1;
            let saved = hand.save();
            hand.apply_mut(action)?;
            let value = self.visit(hand, traverser, rng)?;
            hand.restore(saved);
            return Ok(value);
        }
        let mut values = [0.; ACTIONS];
        for (label, action) in &choices {
            let saved = hand.save();
            hand.apply_mut(*action)?;
            values[*label as usize] = self.visit(hand, traverser, rng)?;
            hand.restore(saved);
        }
        let value: f64 = choices.iter().map(|(l, _)| sigma[*l as usize] * values[*l as usize]).sum();
        let mut regrets = [0.; ACTIONS];
        for (label, _) in &choices {
            regrets[*label as usize] = values[*label as usize] - value;
        }
        self.record(ADVANTAGE, players, street, legal, &regrets, &bytes);
        self.counts.advantage += 1;
        Ok(value)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::policy_network::PolicyNetwork;

    fn tables() -> Option<&'static EquityTables> {
        let dir = std::env::var("HU20_K50_TABLES").ok()?;
        Some(EquityTables::load(std::path::Path::new(&dir), false).unwrap())
    }

    /// A one-layer advantage network whose regrets are its biases.
    fn constant(biases: [f32; ACTIONS]) -> PolicyNetwork {
        let n = features::len();
        let header = serde_json::to_vec(&serde_json::json!({"format":crate::policy_network::FORMAT,"layout_sha256":features::layout_sha256(),
            "features":n,"layers":[{"in":n,"out":ACTIONS}],"activation":"relu","output":"advantage-6"})).unwrap();
        let mut f = crate::policy_network::MAGIC.to_vec();
        f.extend_from_slice(&(header.len() as u64).to_le_bytes());
        f.extend_from_slice(&header);
        for _ in 0..n * ACTIONS {
            f.extend_from_slice(&0f32.to_le_bytes());
        }
        for b in biases {
            f.extend_from_slice(&b.to_le_bytes());
        }
        PolicyNetwork::parse(&f).unwrap()
    }

    #[test]
    fn roots_are_a_function_of_seed_iteration_and_index() {
        let (a, ta, _) = root(5, 3, 7, &[3, 4, 5, 6]).unwrap();
        let (b, tb, _) = root(5, 3, 7, &[3, 4, 5, 6]).unwrap();
        assert_eq!((a.config().stacks(), a.button(), ta), (b.config().stacks(), b.button(), tb));
        let counts: std::collections::BTreeSet<usize> = (0..200).map(|i| root(5, 3, i, &[3, 6]).unwrap().0.config().players()).collect();
        assert_eq!(counts.into_iter().collect::<Vec<_>>(), vec![3, 6]);
        assert!(root(5, 3, 7, &[7]).is_err() && root(5, 3, 7, &[]).is_err());
    }

    #[test]
    fn traversals_are_deterministic_and_regrets_are_centred() {
        let Some(t) = tables() else { return };
        // Regrets favor calling and the pot raise: a mixed current strategy everywhere they're legal.
        let net = constant([0.1, 0.2, 1.0, -1.0, 0.5, -0.3]);
        let fast = net.fast();
        let mut a = Traversal::new(&fast, t, 4);
        let mut b = Traversal::new(&fast, t, 4);
        for i in 0..20 {
            assert_eq!(a.run(11, i, &[3, 6]).unwrap(), b.run(11, i, &[3, 6]).unwrap());
        }
        assert_eq!(a.out, b.out);
        assert_eq!(a.counts, b.counts);
        assert_eq!(a.out.len() as u64, (a.counts.advantage + a.counts.strategy) * record_bytes() as u64);
        assert!(a.counts.advantage > 0 && a.counts.strategy > 0);
        let r = record_bytes();
        for rec in a.out.chunks_exact(r) {
            assert_eq!(u32::from_le_bytes(rec[4..8].try_into().unwrap()), 4);
            let legal = rec[3];
            let targets: Vec<f64> = (0..ACTIONS).map(|k| f32::from_le_bytes(rec[8 + 4 * k..12 + 4 * k].try_into().unwrap()) as f64).collect();
            let mut regrets = [0.; ACTIONS];
            for k in 0..ACTIONS {
                regrets[k] = [0.1, 0.2, 1.0, -1.0, 0.5, -0.3][k];
            }
            let sigma = crate::policy_network::regret_match(&regrets, legal);
            for k in 0..ACTIONS {
                if legal >> k & 1 == 0 {
                    assert_eq!(targets[k], 0., "illegal labels carry no target");
                }
            }
            if rec[0] == STRATEGY {
                for k in 0..ACTIONS {
                    assert!((targets[k] - sigma[k]).abs() < 1e-6);
                }
            } else {
                // The strategy-weighted regret is zero: v = sum of sigma(a) v(a).
                let centred: f64 = (0..ACTIONS).map(|k| sigma[k] * targets[k]).sum();
                assert!(centred.abs() < 1e-3, "{centred}");
            }
        }
    }
}
