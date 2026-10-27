//! Bounded research qualification. No release/default or strength entry point.
use hu20_trainer::{
    cards::EquityTables,
    cfr::Key,
    gz::Gzip,
    multi_binary,
    multi_cfr::{Deltas, Game, Sampling, Table, Trainer},
    multi_checkpoint,
    multi_holdem::{self, KeySchema},
    multi_policy::{self, Mode, Policy, PolicyTable},
    multi_stacks::{self, StackMixtureGame},
    nplayer::{Event, Hand},
};
use rand::{seq::SliceRandom, Rng, SeedableRng};
use serde_json::{json, Value};
use std::{
    collections::{BTreeMap, BTreeSet},
    io::Write,
    path::Path,
    sync::Arc,
    time::Instant,
};
const SEED: u64 = 20261026441001;
const PANEL_SEED: u64 = 20261026441002;
const PILOT_SEED: u64 = 20261026441011;
fn write(path: &Path, value: Value) -> Result<(), String> {
    let mut f = std::fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(path)
        .map_err(|e| e.to_string())?;
    writeln!(f, "{value}").map_err(|e| e.to_string())
}
pub(crate) fn hash(path: &Path) -> Result<String, String> {
    multi_binary::sha_file(path)
}
#[derive(Clone, Default)]
struct Learning {
    roots: u64,
    visits: u64,
    nonzero_aggregate: u64,
    zero_aggregate: u64,
    opponent_only: u64,
    unseen_before_merge: u64,
    declined_at_frozen_table: u64,
    retained_nonzero_aggregate: u64,
}
#[derive(Default)]
struct Watch {
    roots: u64,
    nonzero: u64,
    sum_w: f64,
    sum_w2: f64,
    retained_roots: u64,
    retained_nonzero: u64,
    declined_roots: u64,
}
pub(crate) struct Ledger {
    cells: Vec<Vec<Vec<Learning>>>,
    watch: BTreeMap<Key, Watch>,
}
impl Ledger {
    fn new(panel: &[(usize, Hand)], tables: &EquityTables) -> Self {
        Self::new_for(panel, tables, KeySchema::StackOwner)
    }
    pub(crate) fn new_for(
        panel: &[(usize, Hand)],
        tables: &EquityTables,
        schema: KeySchema,
    ) -> Self {
        Self {
            cells: vec![vec![vec![Learning::default(); 4]; 3]; 27],
            watch: panel
                .iter()
                .map(|(_, h)| {
                    let o = h.observe(h.actor().unwrap()).unwrap();
                    (
                        multi_holdem::observation_decision_for(schema, &o, tables).key,
                        Watch::default(),
                    )
                })
                .collect(),
        }
    }
    fn record(
        &mut self,
        label: Option<u64>,
        weight: f64,
        table: &Table,
        deltas: &Deltas,
        frozen: bool,
    ) {
        let label = label.expect("mixture root context") as usize;
        assert!(label < 81 && weight > 0. && weight.is_finite());
        let context = label / 3;
        let button = label % 3;
        for (key, d) in deltas {
            let seat = (d.actor as usize + button) % 3;
            let c = &mut self.cells[context][seat][d.street as usize];
            let nonzero = d.regrets().iter().any(|r| *r != 0.);
            c.roots += 1;
            c.visits += d.visits;
            c.nonzero_aggregate += u64::from(d.visits > 0 && nonzero);
            c.zero_aggregate += u64::from(d.visits > 0 && !nonzero);
            c.opponent_only += u64::from(d.visits == 0);
            let missing = !table.contains_key(key);
            c.unseen_before_merge += u64::from(missing);
            c.declined_at_frozen_table += u64::from(missing && frozen);
            let accepted = !missing || !frozen;
            c.retained_nonzero_aggregate += u64::from(accepted && d.visits > 0 && nonzero);
            if d.visits > 0 {
                if let Some(w) = self.watch.get_mut(key) {
                    let mass = weight * d.visits as f64;
                    w.roots += 1;
                    w.nonzero += u64::from(nonzero);
                    w.retained_roots += u64::from(accepted);
                    w.retained_nonzero += u64::from(accepted && nonzero);
                    w.declined_roots += u64::from(!accepted);
                    w.sum_w += mass;
                    w.sum_w2 += mass * mass;
                }
            }
        }
    }
    pub(crate) fn value(&self) -> Value {
        let mut cells = Vec::new();
        for (tuple, seats) in self.cells.iter().enumerate() {
            for (seat, ss) in seats.iter().enumerate() {
                for (street, c) in ss.iter().enumerate() {
                    cells.push(json!({"tuple":tuple,"stacks":multi_stacks::config(tuple).unwrap().stacks(),"seat":seat,
            "hero_starting_depth_bb":multi_stacks::config(tuple).unwrap().stacks()[seat]/100,"street":street,
            "root_key_contributions":c.roots,"traverser_visits":c.visits,"nonzero_regret_root_aggregates":c.nonzero_aggregate,
            "zero_regret_root_aggregates_with_visits":c.zero_aggregate,"opponent_only_root_aggregates":c.opponent_only,
            "unseen_before_merge":c.unseen_before_merge,"declined_at_frozen_table":c.declined_at_frozen_table,"retained_nonzero_regret_root_aggregates":c.retained_nonzero_aggregate}));
                }
            }
        }
        let watch: Vec<_> = self
            .watch
            .iter()
            .map(|(key, w)| {
                json!({"key":multi_checkpoint::key_hex(key),
            "positive_weight_root_contributions":w.roots,"nonzero_regret_root_aggregates":w.nonzero,
            "retained_root_contributions":w.retained_roots,"retained_nonzero_regret_root_aggregates":w.retained_nonzero,"declined_root_contributions":w.declined_roots,"weight_sum":w.sum_w,"weight_square_sum":w.sum_w2,
            "nominal_weight_ess":if w.sum_w2>0.{w.sum_w*w.sum_w/w.sum_w2}else{0.}})
            })
            .collect();
        json!({"cells":cells,"watch":watch,"limits":"Immutable pre-merge root aggregates, not individual path updates. Opponent-only is not zero reach. Net-zero regrets can hide cancelling updates. Nominal weight ESS is a concentration proxy, not independent statistical sample size; policy is adaptive. Watch keys fixed before training; never reached keys retained. Declined counts are root-key aggregates, not unique new rows."})
    }
}
fn panel(tables: &EquityTables) -> Result<Vec<(usize, Hand)>, String> {
    panel_for(tables, PANEL_SEED)
}
pub(crate) fn panel_for(tables: &EquityTables, seed: u64) -> Result<Vec<(usize, Hand)>, String> {
    let mut rng = rand::rngs::StdRng::seed_from_u64(seed);
    let mut out = Vec::new();
    for tuple in 0..27 {
        for button in 0..3 {
            for style in 0..2 {
                for _ in 0..2 {
                    let mut deck: Vec<u8> = (0..52).collect();
                    deck.shuffle(&mut rng);
                    let mut hand = Hand::from_deck(multi_stacks::config(tuple)?, button, &deck)?;
                    let mut steps = 0;
                    while let Some(actor) = hand.actor() {
                        if steps >= 10000 {
                            return Err("panel action bound".into());
                        }
                        steps += 1;
                        out.push((tuple, hand.clone()));
                        let observation = hand.observe(actor)?;
                        let choices = multi_holdem::menu(&observation);
                        // Exercise all three encoders on exactly the same legal observation.
                        for schema in [
                            KeySchema::History,
                            KeySchema::LiveOrder,
                            KeySchema::StackOwner,
                        ] {
                            let _ = multi_holdem::observation_decision_for(
                                schema,
                                &observation,
                                tables,
                            );
                        }
                        let a = if style == 0 {
                            rng.gen_range(0..choices.len())
                        } else {
                            choices
                                .iter()
                                .position(|(_, a)| {
                                    matches!(
                                        a.kind,
                                        hu20_trainer::game::Kind::Check
                                            | hu20_trainer::game::Kind::Call
                                    )
                                })
                                .unwrap()
                        };
                        hand.apply_mut(choices[a].1)?;
                    }
                }
            }
        }
    }
    Ok(out)
}
fn audit_panel(panel: &[(usize, Hand)], trainer: &Trainer, tables: &EquityTables) -> Value {
    let mut cells = vec![vec![vec![[0u64; 4]; 4]; 3]; 27];
    let mut signatures: BTreeMap<(usize, usize, usize), BTreeSet<String>> = BTreeMap::new();
    let mut side_exposure = vec![vec![vec![0u64; 4]; 3]; 27];
    let mut all_in_exposure = side_exposure.clone();
    let mut strata_keys: BTreeMap<(usize, usize, usize), [BTreeSet<Key>; 3]> = BTreeMap::new();
    let mut aliases: BTreeMap<Key, BTreeSet<Key>> = BTreeMap::new();
    let mut merges: BTreeMap<Key, BTreeSet<Key>> = BTreeMap::new();
    for (tuple, h) in panel {
        let o = h.observe(h.actor().unwrap()).unwrap();
        let old = multi_holdem::observation_decision_for(KeySchema::LiveOrder, &o, tables);
        let new = multi_holdem::observation_decision_for(
            KeySchema::from_identity(&trainer.identity).unwrap(),
            &o,
            tables,
        );
        let exact = multi_holdem::observation_decision_for(KeySchema::History, &o, tables);
        aliases.entry(old.key).or_default().insert(new.key);
        merges.entry(new.key).or_default().insert(exact.key);
        let status = match trainer.table.get(&new.key) {
            None => 0,
            Some(e) if e.average.is_some_and(|a| a.iter().any(|v| *v > 0.)) => 2,
            _ => 1,
        };
        let seat = o.seat;
        let street = o.street as usize;
        cells[*tuple][seat][street][status] += 1;
        cells[*tuple][seat][street][3] += 1;
        // Provisional layers are public accounting, not necessarily final side pots.
        let levels: BTreeSet<_> = o
            .players
            .iter()
            .map(|p| p.contributed)
            .filter(|v| *v > 0)
            .collect();
        let contested = levels
            .iter()
            .filter(|&&level| o.players.iter().filter(|p| p.contributed >= level).count() > 1)
            .count();
        side_exposure[*tuple][seat][street] += u64::from(contested > 1);
        all_in_exposure[*tuple][seat][street] +=
            u64::from(o.players.iter().any(|p| !p.folded && p.stack == 0));
        let sets = strata_keys.entry((*tuple, seat, street)).or_default();
        for (set, key) in sets.iter_mut().zip([old.key, new.key, exact.key]) {
            set.insert(key);
        }
        let signature=json!({"button":o.button,"actor":o.actor,"stacks":o.config.stacks(),"street":street,
          "players":o.players.iter().map(|p|(p.stack,p.street_bet,p.contributed,p.folded)).collect::<Vec<_>>(),
          "board":o.board,"history":o.history.iter().map(|e|format!("{e:?}")).collect::<Vec<_>>()}).to_string();
        signatures
            .entry((*tuple, seat, street))
            .or_default()
            .insert(signature);
    }
    json!({"seed":PANEL_SEED,"hands":324,"observations":panel.len(),"cells":cells,
       "cell_axes":["tuple","physical_seat","street"],"all_in_player_observations":all_in_exposure,
       "key_counts_by_stratum":strata_keys.iter().map(|(&(tuple,seat,street),v)|json!({"tuple":tuple,"seat":seat,"street":street,"legacy_keys":v[0].len(),"stack_owner_keys":v[1].len(),"history_keys":v[2].len()})).collect::<Vec<_>>(),"provisional_multiple_contribution_layer_observations":side_exposure,
       "distinct_concrete_public_signatures":signatures.iter().map(|(&(tuple,seat,street),s)|json!({"tuple":tuple,"seat":seat,"hero_starting_depth_bb":multi_stacks::config(tuple).unwrap().stacks()[seat]/100,"street":street,"signatures":s.len()})).collect::<Vec<_>>(),
       "cell_columns":["missing","zero_average_mass","positive_average_mass","observations"],
       "legacy_keys":aliases.len(),"stack_owner_keys":merges.len(),
       "legacy_keys_split_by_stack_owner":aliases.values().filter(|v|v.len()>1).count(),
       "stack_owner_keys_merging_exact_history":merges.values().filter(|v|v.len()>1).count(),
       "scope":"Same324fixed synthetic hands/observations at every endpoint; balanced tuples/buttons and uniform-menu/check-call continuations, not population or strength estimates."})
}
pub(crate) fn trainer(game: &StackMixtureGame, cap: usize, seed: u64) -> Trainer {
    Trainer {
        sampling: Sampling::Path,
        roots_per_seat: 8,
        ..Trainer::new(game, seed, 3, cap, true)
    }
}
pub(crate) fn train_steps(
    game: &StackMixtureGame,
    t: &mut Trainer,
    ledger: &mut Ledger,
    steps: usize,
) {
    for _ in 0..steps {
        let frozen = t.frozen_at.is_some();
        t.step_fast_observed(game, |label, w, table, d| {
            ledger.record(label, w, table, d, frozen)
        });
    }
}
fn snapshot(h: &Hand) -> Value {
    let legal = h
        .legal()
        .map(|l| json!({"check":l.check,"call":l.call_amount,"raise_to":l.raise_to}));
    json!({"actor":h.actor(),"finished":h.finished(),"board":h.board(),"street":if h.finished(){None}else{Some(h.street().name())},
      "pot":h.pot(),"wager":if h.finished(){None}else{Some(h.wager())},"min_raise":if h.finished(){None}else{Some(h.min_raise())},
      "players":h.players().iter().map(|p|json!([p.stack,p.street_bet,p.contributed,p.folded])).collect::<Vec<_>>(),
      "holes":(0..3).map(|s|h.observe(s).unwrap().hole).collect::<Vec<_>>(),"legal":legal,"rewards":h.settlement().map(|s|s.rewards[..3].to_vec())})
}
pub(crate) fn play(
    path: &Path,
    model: Arc<PolicyTable>,
    t: &Trainer,
    tables: &EquityTables,
) -> Result<Value, String> {
    let mut out = std::io::BufWriter::new(
        std::fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(path)
            .map_err(|e| e.to_string())?,
    );
    writeln!(out,"{}",json!({"format":"nplayer-privileged-policy-replay-v1","identity":model.identity,"hands":81,"distinct_policy_instances":3})).map_err(|e|e.to_string())?;
    let mut rng = rand::rngs::StdRng::seed_from_u64(PANEL_SEED + 1);
    let mut exposure = vec![vec![[0u64; 3]; 4]; 27];
    let mut side_pot_hands = 0;
    for tuple in 0..27 {
        for button in 0..3 {
            let id = tuple * 3 + button;
            let mut policies: Vec<_> = (0..3)
                .map(|s| Policy::new(model.clone(), PANEL_SEED + 100 + id as u64 * 3 + s))
                .collect();
            let mut deck: Vec<u8> = (0..52).collect();
            deck.shuffle(&mut rng);
            let c = multi_stacks::config(tuple)?;
            let mut h = Hand::from_deck(c, button, &deck)?;
            let mut actions = Vec::new();
            let mut actors = Vec::new();
            let mut states = vec![snapshot(&h)];
            while let Some(actor) = h.actor() {
                if actions.len() >= 10000 {
                    return Err("play action bound".into());
                }
                let o = h.observe(actor)?;
                let d = model.decision(&o, tables);
                let status = match t.table.get(&d.key) {
                    None => 0,
                    Some(e) if e.average.is_some_and(|a| a.iter().any(|v| *v > 0.)) => 2,
                    _ => 1,
                };
                exposure[tuple][o.street as usize][status] += 1;
                let action = policies[actor].choose(&o, tables)?;
                actors.push(actor);
                actions.push(json!([action.kind.name(), action.raise_to]));
                h.apply_mut(action)?;
                states.push(snapshot(&h));
            }
            let s = h.settlement().unwrap();
            assert_eq!(s.rewards[..3].iter().sum::<i64>(), 0);
            side_pot_hands += usize::from(s.pots().len() > 1);
            let history: Vec<_> = h
                .history()
                .iter()
                .map(|e| match e {
                    Event::Board(street) => json!([street.name(), "board"]),
                    Event::Action {
                        street,
                        actor,
                        action,
                        paid,
                    } => json!([
                        street.name(),
                        actor,
                        action.kind.name(),
                        action.raise_to,
                        paid
                    ]),
                })
                .collect();
            writeln!(out,"{}",json!({"hand":id,"stacks":c.stacks(),"button":button,"sb":50,"bb":100,"deck":deck,
          "actors":actors,"actions":actions,"states":states,"history":history,"settlement":{"contributions":s.contributions[..3],"refunds":s.refunds[..3],"pots":s.pots().iter().map(|p|json!([p.amount,p.eligible])).collect::<Vec<_>>()}})).map_err(|e|e.to_string())?;
        }
    }
    out.flush().map_err(|e| e.to_string())?;
    Ok(
        json!({"hands":81,"side_pot_hands":side_pot_hands,"lookup_cells":exposure,"columns":["missing","zero_average_mass","positive_average_mass"],"sha256":hash(path)?}),
    )
}
pub(crate) fn retained_rows(t: &Trainer) -> Value {
    let mut row_audit = vec![[0u64; 5]; 4];
    for e in t.table.values() {
        let c = &mut row_audit[e.street as usize];
        c[0] += 1;
        c[1] += u64::from(e.visits == 0);
        c[2] += u64::from(e.visits >= 2);
        c[3] += u64::from(e.regrets.iter().all(|r| *r == 0.));
        c[4] += u64::from(e.average.is_none_or(|v| v.iter().all(|p| *p == 0.)));
    }
    json!({"by_street":row_audit,"columns":["retained_rows","no_traverser_visit","two_or_more_traverser_visits","all_zero_final_regrets","zero_average_mass"],"limits":"Final-row audit; cancellation can zero regrets. Visits are update opportunities, not proof of nonzero learning. Pathwise zero target reach/underflow is not implemented."})
}
fn qualify(tables: &'static EquityTables, out: &Path) -> Result<(), String> {
    qualify_for(tables, out, KeySchema::StackOwner, SEED)
}
pub(crate) fn qualify_for(
    tables: &'static EquityTables,
    out: &Path,
    schema: KeySchema,
    seed: u64,
) -> Result<(), String> {
    let started = Instant::now();
    let game = StackMixtureGame::with_schema(tables, schema)?;
    let panel = panel(tables)?;
    let mut a = trainer(&game, 100000, seed);
    let mut ledger = Ledger::new_for(&panel, tables, schema);
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(2)
        .build()
        .map_err(|e| e.to_string())?;
    pool.install(|| train_steps(&game, &mut a, &mut ledger, 6));
    multi_checkpoint::save(&a, &out.join("mid.gz"), Gzip::Compatible)?;
    let mut resumed = multi_checkpoint::load(&out.join("mid.gz"))?;
    assert_eq!(resumed.identity, game.identity());
    pool.install(|| train_steps(&game, &mut a, &mut ledger, 6));
    let single = rayon::ThreadPoolBuilder::new()
        .num_threads(1)
        .build()
        .map_err(|e| e.to_string())?;
    single.install(|| {
        for _ in 0..6 {
            resumed.step_fast(&game);
        }
    });
    multi_checkpoint::save(&a, &out.join("full.gz"), Gzip::Compatible)?;
    multi_checkpoint::save(&resumed, &out.join("resumed.gz"), Gzip::Compatible)?;
    assert_eq!(hash(&out.join("full.gz"))?, hash(&out.join("resumed.gz"))?);
    let source = hash(&out.join("full.gz"))?;
    multi_policy::write_trainer(
        &a,
        &source,
        Mode::Average,
        &out.join("average.gz"),
        Gzip::Compatible,
    )?;
    let avsha = hash(&out.join("average.gz"))?;
    multi_binary::convert(
        &out.join("average.gz"),
        &avsha,
        &out.join("policy.bin"),
        None,
    )?;
    let binsha = hash(&out.join("policy.bin"))?;
    let proof = multi_binary::verify(
        &out.join("average.gz"),
        &avsha,
        &out.join("policy.bin"),
        &binsha,
        None,
    )?;
    let table = Arc::new(PolicyTable::load(&out.join("policy.bin"), &binsha)?);
    assert!(table.config().is_err());
    for i in 0..27 {
        assert!(table.supports_config(multi_stacks::config(i)?));
    }
    let bad = hu20_trainer::nplayer::Config::new(&[2000, 5000, 9000], 50, 100)?;
    let h = Hand::from_deck(bad, 0, &(0..52).collect::<Vec<_>>())?;
    if table
        .distribution(&h.observe(h.actor().unwrap())?, tables)
        .is_ok()
    {
        return Err("undeclared tuple accepted at inference".into());
    }
    let mut rows = 0;
    for (key, e) in a.table.iter() {
        let row = table.rows.get(&key).ok_or("export key absent")?;
        let p = e.policy(true);
        if row
            .probabilities
            .iter()
            .zip(&p[..row.probabilities.len()])
            .any(|(x, y)| x.to_bits() != y.to_bits())
        {
            return Err("full-row float64 parity".into());
        }
        rows += 1;
    }
    let initial = play(&out.join("initial.jsonl"), table.clone(), &a, tables)?;
    let repeat = play(&out.join("repeat.jsonl"), table, &a, tables)?;
    assert_eq!(initial, repeat);
    write(&out.join("retained-rows.json"), retained_rows(&a))?;
    write(&out.join("learning.json"), ledger.value())?;
    write(
        &out.join("common-panel.json"),
        audit_panel(&panel, &a, tables),
    )?;
    write(
        &out.join("verified.json"),
        json!({"status":"passed","fixture_only":true,"iterations":12,"checkpoint":source,
      "thread_resume_and_observer_byte_parity":true,"rows_audited":rows,"binary_verified":proof,"play":initial,
      "root_counts_include_both_continuation_paths":game.counts(),"root_button_counts_include_both_paths":game.buttons(),"nodes":a.counts.nodes,"wall_seconds":started.elapsed().as_secs_f64(),"no_pilot_started":true,"effective_global_threads":rayon::current_num_threads()}),
    )
}
fn pilot(manifest: &Path) -> Result<(), String> {
    let m: Value = serde_json::from_slice(&std::fs::read(manifest).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    if m["mode"] != "pilot"
        || m["seed"] != PILOT_SEED
        || m["targets"] != json!([5000000, 25000000, 100000000])
        || m["max_entries"] != 10000000
        || m["threads"] != 2
    {
        return Err("fixed pilot scope differs".into());
    }
    let owner: Value = serde_json::from_slice(
        &std::fs::read(m["owner_admission"].as_str().ok_or("owner receipt")?)
            .map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;
    if owner["status"] != "owner-approved"
        || owner["study"] != "PR441"
        || owner["targets"] != m["targets"]
        || owner["seed"] != PILOT_SEED
        || owner["max_entries"] != 10000000
    {
        return Err("pilot allocation has not been accepted".into());
    }
    let out = Path::new(m["out"].as_str().ok_or("output")?);
    std::fs::create_dir(out).map_err(|e| e.to_string())?;
    let tables = EquityTables::load(Path::new(m["tables"].as_str().ok_or("K50")?), false)?;
    let game = StackMixtureGame::new(tables);
    let panel = panel(tables)?;
    let mut ledger = Ledger::new(&panel, tables);
    let mut t = trainer(&game, 10000000, PILOT_SEED);
    let mut endpoints = Vec::new();
    for target in [5000000, 25000000, 100000000] {
        let root = out.join(target.to_string());
        std::fs::create_dir(&root).map_err(|e| e.to_string())?;
        let clock = Instant::now();
        while t.counts.nodes < target {
            if out.join("STOP").exists() {
                return Err("ownerSTOP".into());
            }
            train_steps(&game, &mut t, &mut ledger, 1);
            if t.iteration % 100 == 0 {
                write(
                    &root.join(format!("progress-{}.json", t.iteration)),
                    json!({"nodes":t.counts.nodes,"entries":t.table.len(),"frozen_at":t.frozen_at,"elapsed_seconds":clock.elapsed().as_secs_f64()}),
                )?;
            }
        }
        let training_seconds = clock.elapsed().as_secs_f64();
        let save = Instant::now();
        multi_checkpoint::save(&t, &root.join("checkpoint.gz"), Gzip::Parallel)?;
        let save_seconds = save.elapsed().as_secs_f64();
        let export = Instant::now();
        let source = hash(&root.join("checkpoint.gz"))?;
        multi_policy::write_trainer(
            &t,
            &source,
            Mode::Average,
            &root.join("average.gz"),
            Gzip::Parallel,
        )?;
        let export_seconds = export.elapsed().as_secs_f64();
        let convert = Instant::now();
        let avsha = hash(&root.join("average.gz"))?;
        multi_binary::convert(
            &root.join("average.gz"),
            &avsha,
            &root.join("policy.bin"),
            None,
        )?;
        let conversion_seconds = convert.elapsed().as_secs_f64();
        let audit = Instant::now();
        let binsha = hash(&root.join("policy.bin"))?;
        let verified = multi_binary::verify(
            &root.join("average.gz"),
            &avsha,
            &root.join("policy.bin"),
            &binsha,
            None,
        )?;
        let audit_seconds = audit.elapsed().as_secs_f64();
        let load = Instant::now();
        let policy = Arc::new(PolicyTable::load(&root.join("policy.bin"), &binsha)?);
        let load_seconds = load.elapsed().as_secs_f64();
        let play_clock = Instant::now();
        let initial = play(&root.join("initial.jsonl"), policy.clone(), &t, tables)?;
        let repeat = play(&root.join("repeat.jsonl"), policy, &t, tables)?;
        if initial != repeat {
            return Err("pilot play/reproduction differ".into());
        }
        write(&root.join("retained-rows.json"), retained_rows(&t))?;
        write(&root.join("learning.json"), ledger.value())?;
        write(
            &root.join("common-panel.json"),
            audit_panel(&panel, &t, tables),
        )?;
        let endpoint = json!({"target_nodes":target,"actual_nodes":t.counts.nodes,"entries":t.table.len(),"frozen_at":t.frozen_at,
          "counts":multi_checkpoint::counts_json(&t.counts),"roots_cumulative":game.counts(),"buttons_cumulative":game.buttons(),
          "training_seconds":training_seconds,"save_seconds":save_seconds,"export_seconds":export_seconds,
          "conversion_seconds":conversion_seconds,"audit_seconds":audit_seconds,"load_seconds":load_seconds,
          "play_repeat_readout_seconds":play_clock.elapsed().as_secs_f64(),"binary_verification":verified,"initial_repeat":initial,
          "independent_replay_pending":true,"strength_claim":false});
        write(&root.join("endpoint.json"), endpoint.clone())?;
        endpoints.push(endpoint);
    }
    write(
        &out.join("native-complete.json"),
        json!({"status":"native-complete-proof-pending","endpoints":endpoints,"no_strength_readout":true}),
    )
}
fn main() {
    let a: Vec<String> = std::env::args().collect();
    let result = (|| -> Result<(), String> {
        rayon::ThreadPoolBuilder::new()
            .num_threads(2)
            .build_global()
            .map_err(|e| e.to_string())?;
        assert_eq!(rayon::current_num_threads(), 2);
        match a.get(1).map(String::as_str) {
            Some("qualify") if a.len() == 4 => {
                let out = Path::new(&a[3]);
                std::fs::create_dir(out).map_err(|e| e.to_string())?;
                let tables = EquityTables::load(Path::new(&a[2]), false)?;
                qualify(tables, out)
            }
            Some("pilot") if a.len() == 3 => pilot(Path::new(&a[2])),
            _ => Err("qualify K50 NEW_OUTPUT | pilot APPROVED_MANIFEST".into()),
        }
    })();
    if let Err(e) = result {
        eprintln!("variable-stack: {e}");
        std::process::exit(2);
    }
}
