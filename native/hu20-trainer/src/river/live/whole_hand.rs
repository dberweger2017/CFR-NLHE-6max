//! Acting-observation-only bridge to the frozen retained river solver.
use super::*;
use rand::{Rng, SeedableRng};
use std::sync::Arc;

pub const MENU: &str = "pot-jam-cap3-root-min-responses-v1";

/// Serializes exactly the legal own-seat information accepted by the solver.
pub fn observation_request(o: &Observation<'_>) -> Result<Value, String> {
    if o.actor != Some(o.seat) {
        return Err("search requires acting observation".into());
    }
    let legal = o.legal.ok_or("acting legal bounds missing")?;
    let mut hole = o.hole;
    hole.sort_unstable();
    Ok(
        json!({"format":"nplayer-live-river-v1","button":o.button,"board":o.board,
        "seat":o.seat,"hole":hole,"actions":o.history.iter().filter_map(|e|match e {
            Event::Action{street,actor,action,paid}=>Some(json!([actor,*street as u64,action.kind.name(),action.raise_to,paid])),
            _=>None}).collect::<Vec<_>>(),
        "players":o.players.iter().map(|p|json!([p.stack,p.street_bet,p.contributed,p.folded])).collect::<Vec<_>>(),
        "legal":{"check":legal.check,"call_amount":legal.call_amount,"raise_to":legal.raise_to}}),
    )
}

pub fn eligibility(o: &Observation<'_>) -> &'static str {
    if o.street != Street::River {
        return "not-river";
    }
    if o.history.iter().any(|e| {
        matches!(
            e,
            Event::Action {
                street: Street::River,
                ..
            }
        )
    }) {
        return "later-first-entry";
    }
    let live: Vec<_> = o.players.iter().filter(|p| !p.folded).collect();
    if live.len() != 2 {
        return "three-live";
    }
    if live.iter().any(|p| p.stack == 0) {
        return "all-in";
    }
    "eligible"
}

fn sample(actions: &[Action], p: &[f64], draw: f64) -> Result<Action, String> {
    if actions.len() != p.len()
        || p.iter().any(|x| !x.is_finite() || *x < 0.)
        || (p.iter().sum::<f64>() - 1.).abs() > 1e-9
    {
        return Err("invalid played distribution".into());
    }
    let mut chosen = p.iter().rposition(|x| *x > 0.).ok_or("empty support")?;
    let mut sum = 0.;
    for (i, x) in p.iter().enumerate() {
        sum += x;
        if draw < sum {
            chosen = i;
            break;
        }
    }
    Ok(actions[chosen])
}

/// New instance per hand, same one-uniform-per-decision RNG law as Policy.
/// The arena owns privileged Hand/deck data; neither enters this object.
pub struct WholeHandPolicy {
    table: Arc<PolicyTable>,
    rng: rand::rngs::StdRng,
    store: Option<SessionStore>,
    hand_id: String,
    context: Option<Value>,
    off_tree: bool,
}
impl WholeHandPolicy {
    pub fn new(
        table: Arc<PolicyTable>,
        model: &str,
        seed: u64,
        hand_id: String,
        enabled: bool,
    ) -> Result<Self, String> {
        Ok(Self {
            table,
            rng: rand::rngs::StdRng::seed_from_u64(seed),
            store: if enabled {
                Some(SessionStore::new(model)?)
            } else {
                None
            },
            hand_id,
            context: None,
            off_tree: false,
        })
    }
    pub fn choose(
        &mut self,
        o: &Observation<'_>,
        tables: &EquityTables,
    ) -> Result<(Action, Value, f64), String> {
        let tick = Instant::now();
        let (bp, found) = self.table.distribution(o, tables)?;
        let bp_actions: Vec<_> = multi_holdem::menu(o).iter().map(|(_, a)| *a).collect();
        let mut p = bp.clone();
        let mut actions = bp_actions.clone();
        let eligible = eligibility(o);
        let mut mode = "blueprint";
        let mut info = Value::Null;
        if let Some(store) = &mut self.store {
            if self.context.is_none() && eligible == "eligible" {
                let mut request = observation_request(o)?;
                request["mode"] = json!("solve");
                request["search_menu"] = json!(MENU);
                request["algorithm"] = json!("dcfr-1.5-0-2");
                request["sweeps"] = json!(2048);
                request["checkpoints"] = json!([8, 16, 32, 64, 128, 256, 512, 1024, 2048]);
                request["stop_at_target"] = json!(true);
                request["omitted"] = json!(false);
                request["target"] = json!({"pot_fraction":0.01,"cap_bb":0.1});
                let r = store.request(
                    &json!({"mode":"retained-begin","hand_id":self.hand_id,"observation":request}),
                    &self.table,
                    tables,
                )?;
                self.context =
                    Some(json!({"hand_id":self.hand_id,"handle":r["session"]["handle"]}));
                mode = "root";
                info = json!({"installed":r["session"]["installed_search"],"fallback_reason":r["session"]["fallback_reason"],
                    "profile_sha256":r["session"]["binding"]["profile_sha256"],"sweeps":r["sweeps"],
                    "nodes":r["nodes"],"quality":r["quality"],"timings":r["timings"],"solver_memory_bytes":r["solver_memory_bytes"]});
                p = serde_json::from_value(r["probabilities"].clone())
                    .map_err(|e| e.to_string())?;
                actions = parse_actions(&r["actions"])?;
            } else if o.street == Street::River && self.context.is_some() {
                let mut req = self.context.clone().unwrap();
                req["mode"] = json!("retained-continue");
                req["observation"] = observation_request(o)?;
                let r = store.request(&req, &self.table, tables)?;
                if r["solver_advances"] != 0 {
                    return Err("continuation advanced solver".into());
                }
                mode = "continuation";
                let off = r["fallback_reason"] == "off-tree action; blueprint for rest of river";
                info = json!({"installed":r["installed_search"],"fallback_reason":r["fallback_reason"],
                    "profile_sha256":r["profile_sha256"],"first_off_tree":off&&!self.off_tree,"off_tree_entry":r["off_tree_entry"],"solver_advances":0});
                self.off_tree |= off;
                p = serde_json::from_value(r["probabilities"].clone())
                    .map_err(|e| e.to_string())?;
                actions = parse_actions(&r["actions"])?;
            }
        }
        if actions.iter().any(|a| !bp_actions.contains(a)) {
            return Err("search produced nonproduction action".into());
        }
        let draw: f64 = self.rng.gen();
        let action = sample(&actions, &p, draw)?;
        let blueprint = sample(&bp_actions, &bp, draw)?;
        // Timings are kept separately from the deterministic replay stream.
        let seconds = tick.elapsed().as_secs_f64();
        let timing = info
            .as_object_mut()
            .and_then(|m| m.remove("timings"))
            .unwrap_or(Value::Null);
        Ok((
            action,
            json!({"mode":mode,"eligibility":eligible,"blueprint_found":found,"draw":draw,
            "actions":actions.iter().map(|a|json!([a.kind.name(),a.raise_to])).collect::<Vec<_>>(),
            "probabilities":p,"blueprint_action":[blueprint.kind.name(),blueprint.raise_to],"changed_same_draw":action!=blueprint,
            "search":info,"timings":timing}),
            seconds,
        ))
    }
    pub fn finish(&mut self, tables: &EquityTables) -> Result<(), String> {
        if let (Some(store), Some(mut context)) = (&mut self.store, self.context.take()) {
            context["mode"] = json!("retained-release");
            store.request(&context, &self.table, tables)?;
        }
        Ok(())
    }
}
fn parse_actions(v: &Value) -> Result<Vec<Action>, String> {
    array(v)?
        .iter()
        .map(|a| {
            Ok(Action {
                kind: kind(&a[0])?,
                raise_to: uint(&a[1])?,
            })
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn sample_keeps_blueprint_uniform_boundary_rule_and_rejects_bad_rows() {
        let a = [
            Action {
                kind: Kind::Fold,
                raise_to: 0,
            },
            Action {
                kind: Kind::Call,
                raise_to: 0,
            },
        ];
        assert_eq!(sample(&a, &[0.25, 0.75], 0.25).unwrap(), a[1]);
        assert_eq!(sample(&a, &[0.25, 0.75], 0.1).unwrap(), a[0]);
        assert!(sample(&a, &[f64::NAN, 1.], 0.2).is_err());
        assert!(sample(&a, &[0., 0.], 0.2).is_err());
    }
    #[test]
    fn request_contains_own_cards_and_public_history_only() {
        let root = super::super::tests::root();
        let o = root.hand.observe(root.hand.actor().unwrap()).unwrap();
        assert_eq!(eligibility(&o), "eligible");
        let v = observation_request(&o).unwrap();
        assert_eq!(v.as_object().unwrap().len(), 8);
        assert!(v.get("deck").is_none() && v.get("holes").is_none() && v.get("seed").is_none());
        assert_eq!(v["hole"].as_array().unwrap().len(), 2);
        let mut h = root.hand.clone();
        h.apply_mut(Action {
            kind: Kind::Check,
            raise_to: 0,
        })
        .unwrap();
        assert_eq!(
            eligibility(&h.observe(h.actor().unwrap()).unwrap()),
            "later-first-entry"
        );
    }
}
