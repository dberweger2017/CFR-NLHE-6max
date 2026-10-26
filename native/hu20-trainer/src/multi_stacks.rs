//! A declared root chance law for research; fixed cash identities are unchanged.
use crate::{
    cards::{EquityTables, EQUITY_K50_SHA256},
    multi_cfr::Game,
    multi_holdem::{self, CashGame, CashState, KeySchema, MENU},
    nplayer::Config,
};
use rand::Rng;
use serde_json::{json, Value};
use std::sync::atomic::{AtomicU64, Ordering};

pub const DEPTHS: [u64; 3] = [2000, 5000, 10000];
pub fn declaration() -> Value {
    json!({"rule":"iid-uniform-depth-grid-v1","depths_chips":DEPTHS,
           "button":"independent-uniform","tuple_probability":"1/27"})
}
pub fn config(index: usize) -> Result<Config, String> {
    if index >= 27 {
        return Err("stack tuple index outside0..27".into());
    }
    Config::new(
        &[DEPTHS[index / 9], DEPTHS[index / 3 % 3], DEPTHS[index % 3]],
        50,
        100,
    )
}
pub fn tuple_index(c: Config) -> Option<usize> {
    if c.players() != 3 || c.small_blind() != 50 || c.big_blind() != 100 {
        return None;
    }
    let mut index = 0;
    for s in c.stacks() {
        index = index * 3 + DEPTHS.iter().position(|x| x == s)?;
    }
    Some(index)
}
#[derive(Clone, Debug)]
pub enum CashIdentity {
    Fixed(Config),
    Mixture,
}
impl CashIdentity {
    pub fn parse(i: &Value) -> Result<Self, String> {
        multi_holdem::validate_key_encoding(i)?;
        let n = i["players"].as_u64().ok_or("missing N")?;
        if !(2..=6).contains(&n)
            || KeySchema::from_identity(i).is_none()
            || i["game"] != "nlhe-cash"
            || i["menu"] != MENU
            || i["utility_unit"] != "big-blind"
            || i["card_tables"] != json!(EQUITY_K50_SHA256)
        {
            return Err("unsupported cash identity".into());
        }
        if let Some(d) = i.get("stack_distribution") {
            if d != &declaration()
                || i.get("stacks").is_some()
                || n != 3
                || i["small_blind"] != 50
                || i["big_blind"] != 100
                || i["schema"] != multi_holdem::STACK_OWNER_SCHEMA
            {
                return Err("unsupported stack distribution/schema".into());
            }
            return Ok(Self::Mixture);
        }
        let stacks = i["stacks"]
            .as_array()
            .ok_or("missing stacks")?
            .iter()
            .map(|s| s.as_u64().ok_or("invalid stack".to_string()))
            .collect::<Result<Vec<_>, _>>()?;
        if stacks.len() != n as usize {
            return Err("stack count differs from N".into());
        }
        Ok(Self::Fixed(Config::new(
            &stacks,
            i["small_blind"].as_u64().ok_or("invalid SB")?,
            i["big_blind"].as_u64().ok_or("invalid BB")?,
        )?))
    }
    pub fn players(&self) -> usize {
        match self {
            Self::Fixed(c) => c.players(),
            Self::Mixture => 3,
        }
    }
    pub fn fixed(&self) -> Result<Config, String> {
        match self {
            Self::Fixed(c) => Ok(*c),
            Self::Mixture => Err("fixed-only consumer cannot use a variable-stack policy".into()),
        }
    }
    pub fn accepts(&self, c: Config) -> bool {
        match self {
            Self::Fixed(expected) => *expected == c,
            Self::Mixture => tuple_index(c).is_some(),
        }
    }
}
pub struct StackMixtureGame {
    pub tables: &'static EquityTables,
    pub root_counts: [AtomicU64; 27],
    pub button_counts: [[AtomicU64; 3]; 27],
}
impl StackMixtureGame {
    pub fn new(tables: &'static EquityTables) -> Self {
        Self {
            tables,
            root_counts: std::array::from_fn(|_| AtomicU64::new(0)),
            button_counts: std::array::from_fn(|_| std::array::from_fn(|_| AtomicU64::new(0))),
        }
    }
    pub fn buttons(&self) -> [[u64; 3]; 27] {
        std::array::from_fn(|i| {
            std::array::from_fn(|b| self.button_counts[i][b].load(Ordering::Relaxed))
        })
    }
    pub fn counts(&self) -> [u64; 27] {
        std::array::from_fn(|i| self.root_counts[i].load(Ordering::Relaxed))
    }
}
impl Game for StackMixtureGame {
    type State = CashState;
    fn players(&self) -> usize {
        3
    }
    fn identity(&self) -> Value {
        json!({"schema":multi_holdem::STACK_OWNER_SCHEMA,"game":"nlhe-cash","players":3,
          "stack_distribution":declaration(),"small_blind":50,"big_blind":100,"menu":MENU,
          "card_tables":self.tables.sha256,"utility_unit":"big-blind"})
    }
    fn root_label(&self, state: &CashState) -> Option<u64> {
        tuple_index(state.hand.config()).map(|i| (i * 3 + state.hand.button()) as u64)
    }
    fn sample(&self, rng: &mut rand::rngs::StdRng) -> CashState {
        let index = rng.gen_range(0..27);
        self.root_counts[index].fetch_add(1, Ordering::Relaxed);
        let state = CashGame {
            config: config(index).unwrap(),
            tables: self.tables,
            schema: KeySchema::StackOwner,
        }
        .sample(rng);
        self.button_counts[index][state.hand.button()].fetch_add(1, Ordering::Relaxed);
        state
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn tuples_and_distribution_are_strict() {
        for i in 0..27 {
            assert_eq!(tuple_index(config(i).unwrap()), Some(i));
        }
        assert!(config(27).is_err());
        let mut identity = json!({"schema":multi_holdem::STACK_OWNER_SCHEMA,"game":"nlhe-cash","players":3,
          "stack_distribution":declaration(),"small_blind":50,"big_blind":100,"menu":MENU,
          "card_tables":EQUITY_K50_SHA256,"utility_unit":"big-blind"});
        let law = CashIdentity::parse(&identity).unwrap();
        assert!(law.fixed().is_err());
        for i in 0..27 {
            assert!(law.accepts(config(i).unwrap()));
        }
        assert!(!law.accepts(Config::new(&[2000, 5000, 9000], 50, 100).unwrap()));
        identity["stack_distribution"]["tuple_probability"] = json!("1/26");
        assert!(CashIdentity::parse(&identity).is_err());
        identity["stack_distribution"] = declaration();
        identity["stacks"] = json!([2000, 2000, 2000]);
        assert!(CashIdentity::parse(&identity).is_err());
    }
}
