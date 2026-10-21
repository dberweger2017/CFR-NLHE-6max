//! Opt-in exact modeled beliefs and offline auditing of an unchanged profile.
use super::*;

pub(super) const EXACT_LAW: &str = "three-product-action-posterior-exact-folded-v1";
#[derive(Clone, Copy, PartialEq)]
pub(super) enum Backend {
    Projected,
    Prefix,
    Dense,
}
impl Backend {
    pub(super) fn parse(v: Option<&Value>) -> Result<Self, String> {
        match v {
            None => Ok(Self::Projected),
            Some(v) => match v.as_str() {
                Some("projected-product-v1") => Ok(Self::Projected),
                Some("exact-folded-prefix-v1") => Ok(Self::Prefix),
                Some("exact-dense-v1") => Ok(Self::Dense),
                _ => Err("invalid belief_backend".into()),
            },
        }
    }
}
fn original_ranges(
    pairs: &[[u8; 2]],
    weights: &[Vec<f64>; 3],
    live: [usize; 2],
) -> [Vec<Holding>; 2] {
    std::array::from_fn(|s| {
        pairs
            .iter()
            .zip(&weights[live[s]])
            .map(|(&cards, &weight)| Holding { cards, weight })
            .collect()
    })
}
pub(super) fn prefix(
    game: Game,
    pairs: &[[u8; 2]],
    weights: &[Vec<f64>; 3],
    live: [usize; 2],
) -> Result<Game, String> {
    let folded = (0..3).find(|s| !live.contains(s)).unwrap();
    game.with_folded_range(
        pairs
            .iter()
            .zip(&weights[folded])
            .map(|(&cards, &weight)| Holding { cards, weight })
            .collect(),
    )
}
pub(super) fn ranges(
    pairs: &[[u8; 2]],
    weights: &[Vec<f64>; 3],
    live: [usize; 2],
) -> [Vec<Holding>; 2] {
    original_ranges(pairs, weights, live)
}
pub(super) fn make(
    root: &PublicRoot,
    pairs: &[[u8; 2]],
    weights: &[Vec<f64>; 3],
    nodes: Vec<Node>,
    backend: Backend,
) -> Result<Game, String> {
    let pot = root.hand.pot() as f64 / 100.;
    let (ranges, _, joint) =
        project_with_joint(pairs, weights, root.live, backend == Backend::Dense)?;
    match backend {
        Backend::Projected => Game::with_limits(
            root.board,
            ranges,
            nodes,
            pot,
            EVALUATION_NODES,
            EVALUATION_CELLS,
        ),
        Backend::Dense => Game::with_limits(
            root.board,
            ranges,
            nodes,
            pot,
            EVALUATION_NODES,
            EVALUATION_CELLS,
        )?
        .with_joint(joint.unwrap()),
        Backend::Prefix => prefix(
            Game::with_limits(
                root.board,
                original_ranges(pairs, weights, root.live),
                nodes,
                pot,
                EVALUATION_NODES,
                EVALUATION_CELLS,
            )?,
            pairs,
            weights,
            root.live,
        ),
    }
}
fn difference(a: &Value, b: &Value) -> Result<f64, String> {
    let mut error = 0f64;
    for key in ["profile_values_bb", "best_response_gains_bb"] {
        for (x, y) in a[key]
            .as_array()
            .ok_or("oracle quality shape")?
            .iter()
            .zip(b[key].as_array().ok_or("oracle quality shape")?)
        {
            let d =
                (x.as_f64().ok_or("oracle numeric")? - y.as_f64().ok_or("oracle numeric")?).abs();
            if !d.is_finite() {
                return Err("nonfinite oracle disagreement".into());
            }
            error = error.max(d);
        }
    }
    if error > 1e-8 {
        return Err(format!("exact oracle disagreement {error}"));
    }
    Ok(error)
}
pub(super) fn qualify(
    root: &PublicRoot,
    pairs: &[[u8; 2]],
    weights: &[Vec<f64>; 3],
    menu: SearchMenu,
) -> Result<Value, String> {
    let mut tree = Tree::new(&root.hand, root.live, menu, SUPPORTED_NODES);
    tree.compile(&mut root.hand.clone())?;
    let n = tree.nodes.len();
    let tick = Instant::now();
    let fast = make(root, pairs, weights, tree.nodes.clone(), Backend::Prefix)?;
    let prefix_preparation = tick.elapsed().as_secs_f64();
    let tick = Instant::now();
    let dense = make(root, pairs, weights, tree.nodes, Backend::Dense)?;
    let dense_preparation = tick.elapsed().as_secs_f64();
    let mut max_leaf = 0f64;
    let tick = Instant::now();
    for seat in 0..2 {
        for pattern in 0..3 {
            let reach: Vec<_> = (0..pairs.len())
                .map(|i| match pattern {
                    0 => 1.,
                    1 => ((i * 17) % 23) as f64 / 23.,
                    _ => 0.,
                })
                .collect();
            for terminal in [
                Terminal {
                    base: 1.,
                    win0: 0.,
                    tie0: 0.,
                },
                Terminal {
                    base: 0.,
                    win0: 1.,
                    tie0: 0.,
                },
                Terminal {
                    base: 0.,
                    win0: 0.,
                    tie0: 1.,
                },
            ] {
                let a = fast.leaf(terminal, seat, &reach)?;
                let b = dense.leaf(terminal, seat, &reach)?;
                for (&x, &y) in a.iter().zip(&b) {
                    let d = (x - y).abs();
                    if d > 1e-10 + 1e-10 * y.abs() {
                        return Err(format!("exact leaf oracle disagreement {d}"));
                    }
                    max_leaf = max_leaf.max(d);
                }
            }
        }
    }
    let leaves = tick.elapsed().as_secs_f64();
    let mut a = Solver::new(fast, vec![None; n])?;
    let mut b = Solver::new(dense, vec![None; n])?;
    a.set_algorithm(DCFR)?;
    b.set_algorithm(DCFR)?;
    let uniform = a.average();
    let mut max_quality = difference(&a.quality(&uniform)?, &b.quality(&uniform)?)?;
    let tick = Instant::now();
    a.advance(64)?;
    let prefix_solve = tick.elapsed().as_secs_f64();
    let tick = Instant::now();
    b.advance(64)?;
    let dense_solve = tick.elapsed().as_secs_f64();
    let pa = a.average();
    let pb = b.average();
    for p in [&pa, &pb] {
        max_quality = max_quality.max(difference(&a.quality(p)?, &b.quality(p)?)?);
    }
    Ok(
        json!({"format":"exact-river-qualification-v1","law":EXACT_LAW,"nodes":n,"fixed_sweeps":64,
        "max_leaf_error_bb":max_leaf,"max_quality_error_bb":max_quality,"chance":a.game.chance_stats(),
        "prefix_profile_sha256":retained::profile_digest(&pa),"dense_profile_sha256":retained::profile_digest(&pb),
        "timings":{"prefix_preparation_seconds":prefix_preparation,"dense_preparation_seconds":dense_preparation,
            "leaf_checks_seconds":leaves,"prefix_fixed_solve_seconds":prefix_solve,"dense_fixed_solve_seconds":dense_solve}}),
    )
}
fn metrics(q: Value, blueprint: &Value, hero: usize) -> Value {
    let value = q["profile_values_bb"][hero].as_f64().unwrap();
    let worst = value - q["best_response_gains_bb"][1 - hero].as_f64().unwrap();
    let bp_worst = blueprint["profile_values_bb"][hero].as_f64().unwrap()
        - blueprint["best_response_gains_bb"][1 - hero]
            .as_f64()
            .unwrap();
    json!({"quality":q,"hero_worst_case_bb":worst,"blueprint_hero_worst_case_bb":bp_worst,
        "hero_worst_case_change_bb":worst-bp_worst})
}
/// Does not advance either solver. This is deliberately a separate request
/// after retained-begin, so offline work never enters decision latency.
pub(super) fn audit(
    root: &PublicRoot,
    pairs: &[[u8; 2]],
    tree: &Tree,
    profile: &[Vec<f64>],
    original: &Value,
    installed: bool,
    table: &PolicyTable,
    tables: &EquityTables,
) -> Result<Value, String> {
    if pairs.is_empty() || profile.is_empty() {
        return Err("unsupported root has no solver profile to audit".into());
    }
    let started = Instant::now();
    let hero = root.live.iter().position(|s| *s == root.seat).unwrap();
    let digest = retained::profile_digest(profile);
    let (weights, _) = likelihoods(root, pairs, |obs| blueprint_row(obs, table, tables))?;
    let (projected, _, _) = project_with_joint(pairs, &weights, root.live, false)?;
    let mut full = full_menu(root, pairs, projected, tree, profile, table, tables)?;
    let mut laws = serde_json::Map::new();
    for backend in [Backend::Projected, Backend::Prefix] {
        let tick = Instant::now();
        full.solver.game = make(
            root,
            pairs,
            &weights,
            full.solver.game.nodes.clone(),
            backend,
        )?;
        let blueprint = full.solver.quality(&full.blueprint)?;
        let candidate = full.solver.quality(&full.deployed)?;
        let actual = if installed {
            candidate.clone()
        } else {
            blueprint.clone()
        };
        let key = if backend == Backend::Projected {
            "projected"
        } else {
            "exact_modeled"
        };
        laws.insert(
            key.into(),
            json!({"candidate_profile":metrics(candidate,&blueprint,hero),
            "actual_deployed_policy":metrics(actual,&blueprint,hero),"blueprint_quality":blueprint,
            "seconds":tick.elapsed().as_secs_f64()}),
        );
    }
    // Check the capped candidate profile with the independent dense operator.
    let tick = Instant::now();
    let mut dense = Solver::new(
        make(root, pairs, &weights, tree.nodes.clone(), Backend::Dense)?,
        vec![None; tree.nodes.len()],
    )?;
    let dense_quality = dense.quality(profile)?;
    let mut prefix = Solver::new(
        make(root, pairs, &weights, tree.nodes.clone(), Backend::Prefix)?,
        vec![None; tree.nodes.len()],
    )?;
    let prefix_quality = prefix.quality(profile)?;
    let error = difference(&prefix_quality, &dense_quality)?;
    if digest != retained::profile_digest(profile) {
        return Err("offline audit changed profile".into());
    }
    Ok(
        json!({"format":"river-deployment-profile-audit-v1","law":EXACT_LAW,"hero_game_seat":hero,
        "profile_sha256":digest,"profile_unchanged":true,"solver_advances":0,"installed_search":installed,
        "actual_policy":if installed{"retained-search-with-off-tree-blueprint"}else{"blueprint-fallback"},
        "requested_belief_backend":original.get("belief_backend"),"full_menu_nodes":full.capped_of.len(),"laws":laws,
        "capped_exact_oracle":{"prefix_quality":prefix_quality,"dense_quality":dense_quality,"max_error_bb":error,
            "seconds":tick.elapsed().as_secs_f64()},"seconds":started.elapsed().as_secs_f64()}),
    )
}
