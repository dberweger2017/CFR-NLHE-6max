//! Strict prepared JSON boundary, separate from evaluator and solver.
use super::{finite, Game, Holding, Node, Solver, Terminal};
use serde_json::{json, Value};
use std::time::Instant;

fn array(v: &Value) -> Result<&Vec<Value>, String> {
    v.as_array().ok_or("expected array".into())
}
fn number(v: &Value) -> Result<f64, String> {
    finite(v.as_f64().ok_or("expected float64 number")?)
}
fn index(v: &Value) -> Result<usize, String> {
    usize::try_from(v.as_u64().ok_or("expected unsigned integer")?)
        .map_err(|_| "index overflow".into())
}
fn terminal(v: &Value) -> Result<Terminal, String> {
    let a = array(v)?;
    if a.len() != 3 {
        return Err("terminal needs base/win0/tie0".into());
    }
    Ok(Terminal {
        base: number(&a[0])?,
        win0: number(&a[1])?,
        tie0: number(&a[2])?,
    })
}
fn fields(v: &Value, allowed: &[&str]) -> Result<(), String> {
    let o = v.as_object().ok_or("expected object")?;
    if o.keys().any(|k| !allowed.contains(&k.as_str())) {
        return Err("unexpected field in prepared request".into());
    }
    Ok(())
}

/// One complete prepared request. The CLI can handle many in one process.
pub fn request(v: &Value) -> Result<Value, String> {
    fields(
        v,
        &[
            "format",
            "game",
            "sweeps",
            "fixed",
            "leaf_queries",
            "include_profiles",
            "strategy_queries",
        ],
    )?;
    if v["format"] != "river-prepared-v1" {
        return Err("unsupported prepared format".into());
    }
    let started = Instant::now();
    let g = &v["game"];
    fields(g, &["board", "ranges", "nodes", "root_pot_bb"])?;
    let b = array(&g["board"])?;
    if b.len() != 5 {
        return Err("board count differs".into());
    }
    let mut board = [0; 5];
    for (i, c) in b.iter().enumerate() {
        board[i] = u8::try_from(index(c)?).map_err(|_| "card index overflow")?;
    }
    let r = array(&g["ranges"])?;
    if r.len() != 2 {
        return Err("two prepared ranges required".into());
    }
    let mut ranges: [Vec<Holding>; 2] = [Vec::new(), Vec::new()];
    for s in 0..2 {
        for row in array(&r[s])? {
            let a = array(row)?;
            if a.len() != 3 {
                return Err("holding needs two cards and weight".into());
            }
            ranges[s].push(Holding {
                cards: [
                    u8::try_from(index(&a[0])?).map_err(|_| "card index overflow")?,
                    u8::try_from(index(&a[1])?).map_err(|_| "card index overflow")?,
                ],
                weight: number(&a[2])?,
            });
        }
    }
    let mut nodes = Vec::new();
    for n in array(&g["nodes"])? {
        if !n["terminal"].is_null() {
            fields(n, &["terminal"])?;
            nodes.push(Node::Leaf(terminal(&n["terminal"])?));
        } else {
            fields(n, &["actor", "children"])?;
            nodes.push(Node::Decision {
                actor: index(&n["actor"])?,
                children: array(&n["children"])?
                    .iter()
                    .map(index)
                    .collect::<Result<_, _>>()?,
            });
        }
    }
    let game = Game::new(board, ranges, nodes, number(&g["root_pot_bb"])?)?;
    let mut fixed = vec![None; game.nodes.len()];
    if let Some(rows) = v.get("fixed") {
        for (key, p) in rows.as_object().ok_or("fixed profiles must be an object")? {
            let id: usize = key.parse().map_err(|_| "invalid fixed node")?;
            if id >= fixed.len() || id.to_string() != *key {
                return Err("fixed node outside tree".into());
            }
            fixed[id] = Some(array(p)?.iter().map(number).collect::<Result<_, _>>()?);
        }
    }
    let mut solver = Solver::new(game, fixed)?;
    let prepare = started.elapsed().as_secs_f64();
    let leaf_started = Instant::now();
    let mut leaves = Vec::new();
    if let Some(queries) = v.get("leaf_queries") {
        for q in array(queries)? {
            fields(q, &["terminal", "seat", "reach"])?;
            leaves.push(
                solver.game.leaf(
                    terminal(&q["terminal"])?,
                    index(&q["seat"])?,
                    &array(&q["reach"])?
                        .iter()
                        .map(number)
                        .collect::<Result<Vec<_>, _>>()?,
                )?,
            );
        }
    }
    let leaf_seconds = leaf_started.elapsed().as_secs_f64();
    let leaf_count = leaves.len();
    let sweeps = v["sweeps"]
        .as_u64()
        .ok_or("fixed positive sweep count required")?;
    let tick = Instant::now();
    solver.advance(sweeps)?;
    let solve = tick.elapsed().as_secs_f64();
    let average = solver.average();
    let tick = Instant::now();
    let quality = solver.quality(&average)?;
    let quality_seconds = tick.elapsed().as_secs_f64();
    let mut selected = Vec::new();
    if let Some(queries) = v.get("strategy_queries") {
        for q in array(queries)? {
            fields(q, &["node", "holding"])?;
            let id = index(&q["node"])?;
            let h = index(&q["holding"])?;
            let Some(Node::Decision { actor, children }) = solver.game.nodes.get(id) else {
                return Err("strategy query requires a decision node".into());
            };
            if h >= solver.game.holdings(*actor) {
                return Err("strategy query holding outside range".into());
            }
            let k = children.len();
            selected.push(json!({"node":id,"holding":h,"probabilities":average[id][h*k..(h+1)*k]}));
        }
    }
    let mut out = json!({"format":"river-prepared-result-v1","sweeps":solver.sweeps,"leaf_evaluation_mode":if solver.game.z<1e-4 {"scalar-ill-conditioned-chance"} else {"sorted-linear"},"strategy_rows":selected,"quality":quality,"ranks":solver.game.ranks(),"leaf_values":leaves,"nodes":solver.game.nodes.len(),"holdings":[solver.game.holdings(0),solver.game.holdings(1)],"leaf_query_seconds":leaf_seconds,"leaf_query_count":leaf_count,"preparation_seconds":prepare,"solve_seconds":solve,"quality_seconds":quality_seconds,"native_seconds_before_serialization":started.elapsed().as_secs_f64()});
    let profiles = match v.get("include_profiles") {
        None => true,
        Some(p) => p.as_bool().ok_or("include_profiles must be boolean")?,
    };
    if profiles {
        out["average"] = json!(average);
        out["current"] = json!(solver.profile);
        out["regrets"] = json!(solver.regrets);
        out["last_deltas"] = json!(solver.deltas);
        out["average_numer"] = json!(solver.numer);
        out["average_denom"] = json!(solver.denom);
    }
    out["native_seconds_before_serialization"] = json!(started.elapsed().as_secs_f64());
    Ok(out)
}
