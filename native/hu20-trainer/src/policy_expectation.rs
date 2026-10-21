//! Chance-free offline evaluation. Only the evaluator owns the privileged Hand.
use crate::{
    game::Street,
    nplayer::{Action, Hand, Observation},
};
use std::collections::BTreeMap;

pub struct Row {
    pub actions: Vec<Action>,
    pub probabilities: Vec<f64>,
    pub source: &'static str,
}

#[derive(Debug, PartialEq)]
pub struct Evaluation {
    pub complete: bool,
    /// No point estimate is returned if any positive-support branch is missing.
    pub expected_chips: Option<f64>,
    pub visited: u64,
    pub terminals: u64,
    pub policy_rows: BTreeMap<&'static str, u64>,
}

enum Failure {
    Limit,
    Invalid(String),
}
impl From<String> for Failure {
    fn from(value: String) -> Self {
        Self::Invalid(value)
    }
}

struct Walker<'a, F> {
    seat: usize,
    limit: u64,
    row: &'a F,
    result: Evaluation,
}

impl<F> Walker<'_, F>
where
    F: Fn(&Observation<'_>) -> Result<Row, String>,
{
    fn visit(&mut self, hand: &Hand) -> Result<f64, Failure> {
        if self.result.visited == self.limit {
            return Err(Failure::Limit);
        }
        self.result.visited += 1;
        if let Some(settled) = hand.settlement() {
            if settled.rewards.iter().sum::<i64>() != 0 {
                return Err(Failure::Invalid("non-zero-sum terminal".into()));
            }
            self.result.terminals += 1;
            return Ok(settled.rewards[self.seat] as f64);
        }
        if hand.street() != Street::River || hand.board().len() != 5 {
            return Err(Failure::Invalid(
                "expectation requires a chance-free river".into(),
            ));
        }
        let actor = hand
            .actor()
            .ok_or("unsettled state without actor".to_string())?;
        let observation = hand.observe(actor)?;
        let row = (self.row)(&observation)?;
        if row.actions.is_empty()
            || row.actions.len() != row.probabilities.len()
            || row
                .probabilities
                .iter()
                .any(|p| !p.is_finite() || *p < 0. || *p > 1.)
            || (row.probabilities.iter().sum::<f64>() - 1.).abs() > 1e-9
        {
            return Err(Failure::Invalid(
                "invalid continuation probability row".into(),
            ));
        }
        for i in 0..row.actions.len() {
            if row.actions[..i].contains(&row.actions[i]) {
                return Err(Failure::Invalid("duplicate continuation action".into()));
            }
        }
        *self.result.policy_rows.entry(row.source).or_default() += 1;
        let mut value = 0.;
        let mut compensation = 0.;
        for (action, probability) in row.actions.iter().zip(&row.probabilities) {
            let mut next = hand.clone();
            next.apply_mut(*action)?;
            if *probability == 0. {
                continue;
            }
            let term = probability * self.visit(&next)? - compensation;
            let sum = value + term;
            compensation = (sum - value) - term;
            value = sum;
        }
        if !value.is_finite() {
            return Err(Failure::Invalid("nonfinite expected value".into()));
        }
        Ok(value)
    }
}

/// Policies receive an actor's legal observation, never Hand/deck/other holdings.
/// The callback is a pure row query, so callers must isolate mutable sessions.
pub fn evaluate<F>(hand: &Hand, seat: usize, max_nodes: u64, row: &F) -> Result<Evaluation, String>
where
    F: Fn(&Observation<'_>) -> Result<Row, String>,
{
    let config = hand.config();
    if config.players() != 3
        || config.small_blind() != 50
        || config.big_blind() != 100
        || config.stacks().iter().any(|s| *s > 10000)
        || (!hand.finished() && hand.players().iter().filter(|p| !p.folded).count() != 2)
    {
        return Err(
            "unsupported expectation game: two-live three-player river, <=100BB, 50/100 blinds"
                .into(),
        );
    }
    if max_nodes == 0 || seat >= hand.config().players() {
        return Err("invalid expectation seat or work limit".into());
    }
    if !hand.finished() && (hand.street() != Street::River || hand.board().len() != 5) {
        return Err("expectation requires a chance-free river".into());
    }
    let mut walker = Walker {
        seat,
        limit: max_nodes,
        row,
        result: Evaluation {
            complete: false,
            expected_chips: None,
            visited: 0,
            terminals: 0,
            policy_rows: BTreeMap::new(),
        },
    };
    match walker.visit(hand) {
        Ok(value) => {
            walker.result.complete = true;
            walker.result.expected_chips = Some(value);
        }
        Err(Failure::Limit) => (),
        Err(Failure::Invalid(error)) => return Err(error),
    }
    Ok(walker.result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{game::Kind, multi_holdem::menu, nplayer::Config};

    fn river(stacks: [u64; 3], tied: bool) -> Hand {
        let mut deck: Vec<u8> = (0..52).collect();
        if tied {
            for (i, card) in [32, 36, 40, 44, 48].iter().enumerate() {
                let index = deck.iter().position(|c| c == card).unwrap();
                deck.swap(6 + i, index);
            }
        }
        let mut h = Hand::from_deck(Config::new(&stacks, 50, 100).unwrap(), 0, &deck).unwrap();
        while h.street() != Street::River {
            let actor = h.actor().unwrap();
            let o = h.observe(actor).unwrap();
            h.apply_mut(Action {
                kind: if actor == 0 && o.street == Street::Preflop {
                    Kind::Fold
                } else if o.legal.unwrap().check {
                    Kind::Check
                } else {
                    Kind::Call
                },
                raise_to: 0,
            })
            .unwrap();
        }
        h
    }
    fn uniform(o: &Observation<'_>) -> Result<Row, String> {
        assert_eq!(o.actor, Some(o.seat));
        assert_eq!(o.board.len(), 5);
        let actions: Vec<_> = menu(o).into_iter().map(|(_, a)| a).collect();
        let probabilities = vec![1. / actions.len() as f64; actions.len()];
        Ok(Row {
            actions,
            probabilities,
            source: "fixture",
        })
    }
    // Independent breadth-first terminal list, not the expectation recursion.
    fn terminal_list(root: &Hand, seat: usize) -> (f64, bool) {
        let mut queue = std::collections::VecDeque::from([(root.clone(), 1.)]);
        let mut leaves = Vec::new();
        let mut refund = false;
        while let Some((h, mass)) = queue.pop_front() {
            if let Some(s) = h.settlement() {
                assert_eq!(s.rewards.iter().sum::<i64>(), 0);
                refund |= s.refunds.iter().any(|x| *x > 0);
                leaves.push((mass, s.rewards[seat] as f64));
                continue;
            }
            let o = h.observe(h.actor().unwrap()).unwrap();
            let choices = menu(&o);
            for (_, a) in &choices {
                let mut next = h.clone();
                next.apply_mut(*a).unwrap();
                queue.push_back((next, mass / choices.len() as f64));
            }
            assert!(queue.len() < 100000);
        }
        assert!((leaves.iter().map(|x| x.0).sum::<f64>() - 1.).abs() < 1e-12);
        (leaves.iter().map(|(p, v)| p * v).sum(), refund)
    }
    #[test]
    fn complete_values_match_independent_exhaustion_with_folds_ties_and_refunds() {
        let mut observed_refund = false;
        for (stacks, tied) in [([400, 400, 400], false), ([400, 300, 500], true)] {
            let h = river(stacks, tied);
            let mut total = 0.;
            for seat in 0..3 {
                let result = evaluate(&h, seat, 200000, &uniform).unwrap();
                let (oracle, refund) = terminal_list(&h, seat);
                observed_refund |= refund;
                assert!(result.complete && result.terminals > 3);
                assert!((result.expected_chips.unwrap() - oracle).abs() < 1e-8);
                total += result.expected_chips.unwrap();
                assert_eq!(result, evaluate(&h, seat, 200000, &uniform).unwrap());
            }
            assert!(total.abs() < 1e-8);
        }
        assert!(observed_refund);
    }
    #[test]
    fn work_limit_never_returns_a_partial_estimate() {
        let h = river([400; 3], false);
        let r = evaluate(&h, 1, 2, &uniform).unwrap();
        assert!(!r.complete && r.expected_chips.is_none());
        assert_eq!(r.visited, 2);
        assert!(evaluate(&h, 1, 0, &uniform).is_err());
    }
    #[test]
    fn malformed_rows_and_earlier_streets_are_rejected() {
        let h = river([400; 3], false);
        for p in [vec![f64::NAN], vec![0.], vec![-1.], vec![1.1]] {
            assert!(evaluate(&h, 1, 100, &|o| Ok(Row {
                actions: vec![menu(o)[0].1],
                probabilities: p.clone(),
                source: "bad"
            }))
            .is_err());
        }
        assert!(evaluate(&h, 1, 100, &|o| Ok(Row {
            actions: vec![menu(o)[0].1; 2],
            probabilities: vec![0.5; 2],
            source: "bad"
        }))
        .is_err());
        let pre = Hand::from_deck(
            Config::new(&[400; 3], 50, 100).unwrap(),
            0,
            &(0..52).collect::<Vec<_>>(),
        )
        .unwrap();
        assert!(evaluate(&pre, 1, 100, &uniform).is_err());
    }
    #[test]
    fn zero_mass_actions_do_not_create_policy_queries_or_change_value() {
        let h = river([400; 3], false);
        let row = |o: &Observation<'_>| {
            let actions: Vec<_> = menu(o).into_iter().map(|(_, a)| a).collect();
            let mut probabilities = vec![0.; actions.len()];
            let i = actions
                .iter()
                .position(|a| a.kind == Kind::Check || a.kind == Kind::Call)
                .unwrap();
            probabilities[i] = 1.;
            Ok(Row {
                actions,
                probabilities,
                source: "passive",
            })
        };
        let r = evaluate(&h, 1, 100, &row).unwrap();
        assert!(r.complete);
        assert_eq!(r.terminals, 1);
        assert_eq!(r.visited, 3);
    }
}
