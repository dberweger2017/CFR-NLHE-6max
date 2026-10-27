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
/// Live-order mixture: every seat's starting depth is drawn independently and uniformly from
/// a log-spaced grid, so one table can mix short and deep stacks. Live-order keys never read
/// initial stacks; training only changes which chip situations reach each row.
pub const LIVE_DEPTHS_BB: [u64; 13] = [10, 15, 20, 30, 40, 50, 65, 80, 100, 125, 150, 200, 250];
/// Phantom seats under a projected view hold this depth; they fold before acting.
pub const LIVE_NOMINAL_BB: u64 = 100;
pub fn live_declaration() -> Value {
    json!({"rule":"iid-uniform-depth-grid-v1","depths_bb":LIVE_DEPTHS_BB,
           "button":"independent-uniform","seat_probability":format!("1/{}", LIVE_DEPTHS_BB.len())})
}
pub fn live_supports(c: Config) -> bool {
    (2..=6).contains(&c.players())
        && (c.small_blind(), c.big_blind()) == (50, 100)
        && c.stacks().iter().all(|s| s % 100 == 0 && LIVE_DEPTHS_BB.contains(&(s / 100)))
}
#[derive(Clone, Debug)]
pub enum CashIdentity {
    Fixed(Config),
    Mixture,
    LiveMixture(usize),
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
            if d == &live_declaration() {
                if i.get("stacks").is_some()
                    || !(2..=6).contains(&n)
                    || i["small_blind"] != 50
                    || i["big_blind"] != 100
                    || KeySchema::from_identity(i) != Some(KeySchema::LiveOrder)
                {
                    return Err("unsupported live-order stack distribution".into());
                }
                return Ok(Self::LiveMixture(n as usize));
            }
            if d != &declaration()
                || i.get("stacks").is_some()
                || n != 3
                || i["small_blind"] != 50
                || i["big_blind"] != 100
                || !matches!(
                    KeySchema::from_identity(i),
                    Some(KeySchema::StackOwner | KeySchema::StackBuckets)
                )
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
            Self::LiveMixture(n) => *n,
        }
    }
    pub fn fixed(&self) -> Result<Config, String> {
        match self {
            Self::Fixed(c) => Ok(*c),
            Self::Mixture | Self::LiveMixture(_) => {
                Err("fixed-only consumer cannot use a variable-stack policy".into())
            }
        }
    }
    /// The configuration a projected view builds phantom seats from: a fixed model's own, or
    /// equal nominal depths for a live-order mixture. Real seats always keep their real chips.
    pub fn projection(&self) -> Result<Config, String> {
        match self {
            Self::Fixed(c) => Ok(*c),
            Self::LiveMixture(n) => Config::new(&vec![LIVE_NOMINAL_BB * 100; *n], 50, 100),
            Self::Mixture => Err("projection needs a live-order policy".into()),
        }
    }
    pub fn accepts(&self, c: Config) -> bool {
        match self {
            Self::Fixed(expected) => *expected == c,
            Self::Mixture => tuple_index(c).is_some(),
            Self::LiveMixture(n) => c.players() == *n && live_supports(c),
        }
    }
}
pub struct StackMixtureGame {
    pub tables: &'static EquityTables,
    schema: KeySchema,
    pub root_counts: [AtomicU64; 27],
    pub button_counts: [[AtomicU64; 3]; 27],
}
impl StackMixtureGame {
    pub fn new(tables: &'static EquityTables) -> Self {
        Self {
            tables,
            schema: KeySchema::StackOwner,
            root_counts: std::array::from_fn(|_| AtomicU64::new(0)),
            button_counts: std::array::from_fn(|_| std::array::from_fn(|_| AtomicU64::new(0))),
        }
    }
    pub fn with_schema(tables: &'static EquityTables, schema: KeySchema) -> Result<Self, String> {
        if !matches!(schema, KeySchema::StackOwner | KeySchema::StackBuckets) {
            return Err("unsupported mixture key schema".into());
        }
        let mut game = Self::new(tables);
        game.schema = schema;
        Ok(game)
    }
    pub fn schema(&self) -> KeySchema {
        self.schema
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
        json!({"schema":self.schema.name(),"game":"nlhe-cash","players":3,
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
            schema: self.schema,
        }
        .sample(rng);
        self.button_counts[index][state.hand.button()].fetch_add(1, Ordering::Relaxed);
        state
    }
}

/// One root's stacks under `live_declaration`; `drawn` sees each seat's grid index.
pub fn live_draw(players: usize, rng: &mut impl Rng, mut drawn: impl FnMut(usize)) -> Config {
    let stacks: Vec<u64> = (0..players)
        .map(|_| {
            let i = rng.gen_range(0..LIVE_DEPTHS_BB.len());
            drawn(i);
            LIVE_DEPTHS_BB[i] * 100
        })
        .collect();
    Config::new(&stacks, 50, 100).unwrap()
}
pub struct LiveMixtureGame {
    pub tables: &'static EquityTables,
    players: usize,
    /// Seat-depth draws per grid index, for the run report.
    pub depth_counts: [AtomicU64; LIVE_DEPTHS_BB.len()],
}
impl LiveMixtureGame {
    pub fn new(tables: &'static EquityTables, players: usize) -> Result<Self, String> {
        if !(2..=6).contains(&players) {
            return Err("live-order mixture needs 2..6 players".into());
        }
        Ok(Self { tables, players, depth_counts: std::array::from_fn(|_| AtomicU64::new(0)) })
    }
    pub fn depths(&self) -> [u64; LIVE_DEPTHS_BB.len()] {
        std::array::from_fn(|i| self.depth_counts[i].load(Ordering::Relaxed))
    }
}
impl Game for LiveMixtureGame {
    type State = CashState;
    fn players(&self) -> usize {
        self.players
    }
    fn identity(&self) -> Value {
        json!({"schema":KeySchema::LiveOrder.name(),"game":"nlhe-cash","players":self.players,
          "stack_distribution":live_declaration(),"small_blind":50,"big_blind":100,"menu":MENU,
          "card_tables":self.tables.sha256,"utility_unit":"big-blind"})
    }
    fn sample(&self, rng: &mut rand::rngs::StdRng) -> CashState {
        let config = live_draw(self.players, rng, |i| {
            self.depth_counts[i].fetch_add(1, Ordering::Relaxed);
        });
        CashGame {
            config,
            tables: self.tables,
            schema: KeySchema::LiveOrder,
        }
        .sample(rng)
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
    #[test]
    fn bucketed_mixture_is_versioned_and_fixed_only_refuses_it() {
        for schema in [
            multi_holdem::STACK_OWNER_SCHEMA,
            multi_holdem::STACK_BUCKETS_SCHEMA,
        ] {
            let mut i = json!({"schema":schema,"game":"nlhe-cash","players":3,"stack_distribution":declaration(),"small_blind":50,"big_blind":100,"menu":MENU,"card_tables":EQUITY_K50_SHA256,"utility_unit":"big-blind"});
            let identity = CashIdentity::parse(&i).unwrap();
            assert!(identity.fixed().is_err());
            for n in 0..27 {
                assert!(identity.accepts(config(n).unwrap()));
            }
            i["schema"] = json!(multi_holdem::LIVE_ORDER_SCHEMA);
            assert!(CashIdentity::parse(&i).is_err());
        }
    }
    fn live_identity(n: usize) -> Value {
        json!({"schema":multi_holdem::LIVE_ORDER_SCHEMA,"game":"nlhe-cash","players":n,
          "stack_distribution":live_declaration(),"small_blind":50,"big_blind":100,"menu":MENU,
          "card_tables":EQUITY_K50_SHA256,"utility_unit":"big-blind"})
    }
    #[test]
    fn live_mixture_identity_is_strict_and_projects_at_nominal_depth() {
        for n in 2..=6 {
            let law = CashIdentity::parse(&live_identity(n)).unwrap();
            assert_eq!(law.players(), n);
            assert!(law.fixed().is_err());
            assert_eq!(law.projection().unwrap(), Config::new(&vec![10000; n], 50, 100).unwrap());
            let mut stacks = vec![1000u64; n];
            stacks[0] = 25000;
            assert!(law.accepts(Config::new(&stacks, 50, 100).unwrap()));
            stacks[0] = 9900;
            assert!(!law.accepts(Config::new(&stacks, 50, 100).unwrap()));
            assert!(!law.accepts(Config::new(&vec![10000; n], 25, 50).unwrap()));
            let other = if n == 6 { 5 } else { n + 1 };
            assert!(!law.accepts(Config::new(&vec![10000; other], 50, 100).unwrap()));
        }
        assert!(CashIdentity::parse(&live_identity(1)).is_err());
        assert!(CashIdentity::parse(&live_identity(7)).is_err());
        let mut i = live_identity(6);
        i["schema"] = json!(multi_holdem::STACK_OWNER_SCHEMA);
        assert!(CashIdentity::parse(&i).is_err());
        let mut i = live_identity(6);
        i["stacks"] = json!(vec![10000; 6]);
        assert!(CashIdentity::parse(&i).is_err());
        let mut i = live_identity(6);
        i["stack_distribution"]["depths_bb"][0] = json!(5);
        assert!(CashIdentity::parse(&i).is_err());
        let mut i = live_identity(6);
        i["big_blind"] = json!(200);
        assert!(CashIdentity::parse(&i).is_err());
        assert!(CashIdentity::Mixture.projection().is_err());
    }
    #[test]
    fn live_draw_is_seeded_and_covers_the_grid() {
        use rand::SeedableRng;
        let mut counts = [0u64; LIVE_DEPTHS_BB.len()];
        let mut a = rand::rngs::StdRng::seed_from_u64(7);
        let mut b = rand::rngs::StdRng::seed_from_u64(7);
        let mut unequal = 0;
        for _ in 0..20_000 {
            let c = live_draw(6, &mut a, |i| counts[i] += 1);
            assert_eq!(c, live_draw(6, &mut b, |_| {}));
            assert!(live_supports(c));
            unequal += c.stacks().iter().any(|&s| s != c.stacks()[0]) as u32;
        }
        let expected = 120_000. / LIVE_DEPTHS_BB.len() as f64;
        assert!(counts.iter().all(|&k| (k as f64 - expected).abs() < 0.06 * expected), "{counts:?}");
        assert!(unequal > 19_900);
    }
}
