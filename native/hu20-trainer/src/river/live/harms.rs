//! Offline exact-law diagnostics of a fixed strategy. Never calls advance().
use super::*;

fn monotone(large: f64, small: f64) -> Result<f64, String> {
    let delta = large - small;
    if !delta.is_finite() || delta < -1e-8 {
        return Err("invalid response restriction value ordering".into());
    }
    Ok(delta)
}

fn quality_metrics(q: &Value, hero: usize) -> Value {
    json!({"profile_value_bb":q["profile_values_bb"][hero],
        "opponent_gain_bb":q["best_response_gains_bb"][1-hero],
        "hero_worst_case_bb":q["profile_values_bb"][hero].as_f64().unwrap()-q["best_response_gains_bb"][1-hero].as_f64().unwrap(),
        "quality":q})
}

fn restricted_responses(
    solver: &mut Solver,
    profile: &[Vec<f64>],
    opponent: usize,
    mask: &[Vec<bool>],
    id: usize,
    j: usize,
    best: f64,
    cap_best: f64,
) -> Result<(f64, Option<f64>), String> {
    let mut without = vec![Vec::new(); mask.len()];
    without[id] = vec![true; mask[id].len()];
    without[id][j] = false;
    if !without[id].iter().any(|b| *b) {
        return Err("cannot remove only legal response".into());
    }
    let restricted = solver.value(profile, opponent, true, Some(without))?;
    monotone(best, restricted)?;
    let add_one = if !mask[id][j] {
        let mut one = mask.to_vec();
        one[id][j] = true;
        let value = solver.value(profile, opponent, true, Some(one))?;
        monotone(value, cap_best)?;
        monotone(best, value)?;
        Some(value)
    } else {
        None
    };
    Ok((restricted, add_one))
}

fn audit_policy(
    f: &mut FullMenu,
    capped: &Tree,
    root: &PublicRoot,
    profile: &[Vec<f64>],
) -> Result<Value, String> {
    let hero = root.live.iter().position(|s| *s == root.seat).unwrap();
    let opponent = 1 - hero;
    let q = f.solver.quality(profile)?;
    let value = q["profile_values_bb"][opponent].as_f64().unwrap();
    let best = f.solver.value(profile, opponent, true, None)?;
    let worst = -best;
    if (worst
        - (q["profile_values_bb"][hero].as_f64().unwrap()
            - q["best_response_gains_bb"][opponent].as_f64().unwrap()))
    .abs()
        > 1e-8
    {
        return Err("zero-sum worst-case accounting differs".into());
    }
    let nodes = f.capped_of.len();
    let mut mask = vec![Vec::new(); nodes];
    let mut entries = Vec::new();
    for id in 0..nodes {
        let Some(c) = f.capped_of[id] else { continue };
        if actor_of(f, id) != opponent {
            continue;
        }
        mask[id] = f.tree.menus[id]
            .iter()
            .map(|a| capped.menus[c].contains(a))
            .collect();
        if !mask[id].iter().any(|b| *b) {
            return Err("empty capped response mask".into());
        }
        if f.tree.menus[id].len() > 1 {
            for j in 0..f.tree.menus[id].len() {
                entries.push((id, j));
            }
        }
    }
    let cap_best = f
        .solver
        .value(profile, opponent, true, Some(mask.clone()))?;
    monotone(best, cap_best)?;
    let mut rows = Vec::new();
    for (id, j) in entries {
        let omitted = !mask[id][j];
        let (restricted, add_one) = restricted_responses(
            &mut f.solver,
            profile,
            opponent,
            &mask,
            id,
            j,
            best,
            cap_best,
        )?;
        let removal = monotone(best, restricted)?;
        let action = f.tree.menus[id][j];
        let mut hand = root.hand.clone();
        for a in &f.tree.paths[id] {
            hand.apply_mut(*a)?;
        }
        let obs = hand.observe(root.live[opponent])?;
        let label = multi_holdem::menu(&obs)
            .into_iter()
            .find(|(_, a)| *a == action)
            .ok_or("response outside production menu")?
            .0;
        let mut branch = f.tree.paths[id].clone();
        branch.push(action);
        let mut hybrid = profile.to_vec();
        let mut changed_rows = 0;
        for n in 0..nodes {
            if actor_of(f, n) == hero
                && f.tree.paths[n].starts_with(&branch)
                && hybrid[n] != f.blueprint[n]
            {
                hybrid[n] = f.blueprint[n].clone();
                changed_rows += 1;
            }
        }
        let hybrid_worst = if changed_rows == 0 {
            worst
        } else {
            -f.solver.value(&hybrid, opponent, true, None)?
        };
        rows.push(json!({"node":id,"path":f.tree.paths[id].iter().map(|a|json!([a.kind.name(),a.raise_to])).collect::<Vec<_>>(),
            "action":[action.kind.name(),action.raise_to],"label":label,"omitted":omitted,
            "facing_bet":obs.legal.ok_or("response legal bounds missing")?.call_amount>0,
            "full_without_response_opponent_gain_bb":restricted-value,
            "leave_one_out_wc_improvement_bb":removal,
            "capped_plus_entry_opponent_gain_bb":add_one.map(|v|v-value),
            "add_one_increment_bb":add_one.map(|v|v-cap_best),
            "hero_blueprint_after_entry_wc_bb":hybrid_worst,
            "hero_blueprint_after_entry_wc_change_bb":hybrid_worst-worst,
            "hero_blueprint_after_entry_changed_rows":changed_rows}));
    }
    Ok(
        json!({"metrics":quality_metrics(&q,hero),"capped_response_only_opponent_gain_bb":cap_best-value,
        "omitted_responses_joint_increment_bb":best-cap_best,"responses":rows,
        "scope":"root reach-weighted exact-law restrictions; entries overlap and are not additive; branch blueprint replacement is a fixed-policy counterfactual"}),
    )
}

pub(super) fn diagnose(
    root: &PublicRoot,
    pairs: &[[u8; 2]],
    capped: &Tree,
    profile: &[Vec<f64>],
    installed: bool,
    table: &PolicyTable,
    tables: &EquityTables,
) -> Result<Value, String> {
    let started = Instant::now();
    let digest = retained::profile_digest(profile);
    let (weights, _) = likelihoods(root, pairs, |obs| blueprint_row(obs, table, tables))?;
    let (ranges, _, _) = project_with_joint(pairs, &weights, root.live, false)?;
    let mut full = full_menu(root, pairs, ranges, capped, profile, table, tables)?;
    full.solver.game = exact::make(
        root,
        pairs,
        &weights,
        full.solver.game.nodes.clone(),
        exact::Backend::Prefix,
    )?;
    let hero = root.live.iter().position(|s| *s == root.seat).unwrap();
    let baseline = full.solver.quality(&full.blueprint)?;
    let deployed = full.deployed.clone();
    let produced = audit_policy(&mut full, capped, root, &deployed)?;
    let actual = if installed {
        produced.clone()
    } else {
        let bp = full.blueprint.clone();
        audit_policy(&mut full, capped, root, &bp)?
    };
    if digest != retained::profile_digest(profile) {
        return Err("diagnostic changed saved profile".into());
    }
    Ok(
        json!({"format":"river-fixed-profile-harms-v1","law":exact::EXACT_LAW,"profile_sha256":digest,
        "profile_unchanged":true,"solver_advances":0,"installed_search":installed,
        "hero_game_seat":hero,"pot_bb":root.hand.pot() as f64/100.,"full_menu_nodes":full.capped_of.len(),
        "blueprint":quality_metrics(&baseline,hero),"produced":produced,"actual":actual,
        "actual_policy":if installed{"retained-search-with-off-tree-blueprint"}else{"blueprint-fallback"},
        "seconds":started.elapsed().as_secs_f64()}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn restriction_ordering_never_turns_negative_or_nonfinite_into_a_gain() {
        assert_eq!(monotone(3., 1.).unwrap(), 2.);
        assert!(monotone(1., 3.).is_err());
        assert!(monotone(f64::NAN, 1.).is_err());
    }
    #[test]
    fn interchangeable_exposing_responses_have_overlapping_nonadditive_gains() {
        let holding = |cards| Holding { cards, weight: 1. };
        let game = Game::new(
            [32, 36, 40, 44, 48],
            [vec![holding([0, 1])], vec![holding([2, 3])]],
            vec![
                Node::Decision {
                    actor: 1,
                    children: vec![1, 2, 3],
                },
                Node::Leaf(Terminal {
                    base: 0.,
                    win0: 0.,
                    tie0: 0.,
                }),
                Node::Leaf(Terminal {
                    base: -5.,
                    win0: 0.,
                    tie0: 0.,
                }),
                Node::Leaf(Terminal {
                    base: -5.,
                    win0: 0.,
                    tie0: 0.,
                }),
            ],
            10.,
        )
        .unwrap();
        let mut solver = Solver::new(game, vec![None; 4]).unwrap();
        let profile = vec![vec![1., 0., 0.], vec![], vec![], vec![]];
        let mask = vec![vec![true, false, false], vec![], vec![], vec![]];
        let best = solver.value(&profile, 1, true, None).unwrap();
        let cap = solver.value(&profile, 1, true, Some(mask.clone())).unwrap();
        assert_eq!((best, cap), (5., 0.));
        for j in [1, 2] {
            let (without, add) =
                restricted_responses(&mut solver, &profile, 1, &mask, 0, j, best, cap).unwrap();
            assert_eq!(without, 5.);
            assert_eq!(add, Some(5.));
        }
        assert_eq!(
            solver.quality(&profile).unwrap()["profile_values_bb"][0],
            0.
        );
        assert_eq!(solver.timing()["sweeps"], 0);
    }
}
