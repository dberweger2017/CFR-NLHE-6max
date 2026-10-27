//! Line-oriented decision service for the 2–6 seat play stack.
//!
//! The caller is the dealer: each request carries the complete deck and the
//! action record, the native engine replays them as privileged state, checks
//! the caller's legal set and chip state against its own, and then hands the
//! agent only `Hand::observe(actor)`. Policies are loaded once and shared.
//!
//! serve [--card-buckets DIR] [--policy NAME PATH SHA256]...
//!
//! One JSON request per stdin line, one JSON response per stdout line:
//!   {"op":"decide","seat":S,"agent":"menu"|"policy:NAME"|"script:NAME","seed":U64,"view":"native"|"projected",
//!    "hand":{"stacks":[..],"sb":50,"bb":100,"button":B,"deck":[52 cards],"actions":[["raise",300],..]},
//!    "expect":{"legal":{"check":..,"call":..,"raise_to":[lo,hi]|null},"players":[[stack,street_bet,contributed,folded],..]}}
//!   {"op":"settle","hand":{..}}
//!   {"op":"state","hand":{..}}  (dealer view: actor, street, board, players, legal; for sandboxes)
//! `view: projected` shows a live-order policy the table through `multi_view::project`
//! (phantom early-position folds, other depths); the default is the native view.
//! Responses carry the native players as [stack,street_bet,contributed,folded].
//! Errors answer {"ok":false,"error":..} and the service keeps running.
use hu20_trainer::{
    cards::EquityTables,
    game::Kind,
    multi_arena::Bot,
    multi_holdem::{self, MENU, SCHEMA},
    multi_policy::{Policy, PolicyTable},
    multi_view,
    nplayer::{Action, Config, Hand},
};
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    io::{BufRead, Write},
    path::Path,
    sync::Arc,
};

const FORMAT: &str = "nplayer-decision-service-v1";
const SCRIPTS: [&str; 4] = ["random", "check-call", "tight-aggressive", "pot-pressure"];

struct Service {
    tables: Option<&'static EquityTables>,
    policies: BTreeMap<String, Arc<PolicyTable>>,
}

fn kind(name: &str) -> Result<Kind, String> {
    match name {
        "fold" => Ok(Kind::Fold),
        "check" => Ok(Kind::Check),
        "call" => Ok(Kind::Call),
        "raise" => Ok(Kind::Raise),
        _ => Err(format!("unknown action kind {name:?}")),
    }
}

fn action_json(action: Action) -> Value {
    json!([action.kind.name(), action.raise_to])
}

fn u64_field(value: &Value, name: &str) -> Result<u64, String> {
    value[name]
        .as_u64()
        .ok_or_else(|| format!("{name} must be a non-negative integer"))
}

/// Replays the dealer's record; every action must be legal in the native engine.
fn replay(request: &Value) -> Result<Hand, String> {
    let h = &request["hand"];
    let stacks: Vec<u64> = h["stacks"]
        .as_array()
        .ok_or("hand.stacks must be an array")?
        .iter()
        .map(|v| v.as_u64().ok_or("stacks must be integers"))
        .collect::<Result<_, _>>()?;
    let config = Config::new(&stacks, u64_field(h, "sb")?, u64_field(h, "bb")?)?;
    let deck: Vec<u8> = h["deck"]
        .as_array()
        .ok_or("hand.deck must be an array")?
        .iter()
        .map(|v| {
            v.as_u64()
                .filter(|&c| c < 52)
                .map(|c| c as u8)
                .ok_or("cards must be 0..51")
        })
        .collect::<Result<_, _>>()?;
    let mut hand = Hand::from_deck(config, u64_field(h, "button")? as usize, &deck)?;
    for (index, row) in h["actions"]
        .as_array()
        .ok_or("hand.actions must be an array")?
        .iter()
        .enumerate()
    {
        let pair = row
            .as_array()
            .filter(|p| p.len() == 2)
            .ok_or("actions are [kind, raise_to]")?;
        let action = Action {
            kind: kind(pair[0].as_str().ok_or("action kind must be a string")?)?,
            raise_to: pair[1].as_u64().ok_or("raise_to must be an integer")?,
        };
        hand.apply_mut(action)
            .map_err(|e| format!("action {index} rejected by the native engine: {e}"))?;
    }
    Ok(hand)
}

/// The caller's engine and the native engine must agree before any agent acts.
fn check_expected(hand: &Hand, expect: &Value) -> Result<(), String> {
    if expect.is_null() {
        return Ok(());
    }
    if let Some(players) = expect.get("players") {
        let native: Vec<Value> = hand
            .players()
            .iter()
            .map(|p| json!([p.stack, p.street_bet, p.contributed, p.folded]))
            .collect();
        if players != &Value::Array(native.clone()) {
            return Err(format!(
                "engine parity: players {players} != native {}",
                Value::Array(native)
            ));
        }
    }
    if let Some(legal) = expect.get("legal") {
        let l = hand
            .legal()
            .ok_or("engine parity: native hand has no actor")?;
        let native =
            json!({"check":l.check,"call":l.call_amount,"raise_to":l.raise_to.map(|(a,b)|[a,b])});
        if legal != &native {
            return Err(format!("engine parity: legal {legal} != native {native}"));
        }
    }
    Ok(())
}

impl Service {
    fn decide(&self, request: &Value) -> Result<Value, String> {
        let hand = replay(request)?;
        let seat = u64_field(request, "seat")? as usize;
        if hand.actor() != Some(seat) {
            return Err(format!(
                "seat {seat} is not acting (native actor {:?})",
                hand.actor()
            ));
        }
        check_expected(&hand, &request["expect"])?;
        // Agents below see only this observation, never `hand`.
        let observation = hand.observe(seat)?;
        let menu = multi_holdem::menu(&observation);
        let mut response = json!({
            "ok": true,
            "seat": seat,
            "street": observation.street.name(),
            "menu": menu.iter().map(|(_, a)| action_json(*a)).collect::<Vec<_>>(),
            "labels": menu.iter().map(|(l, _)| *l).collect::<Vec<_>>(),
            "probabilities": null,
            "trained": null,
            "action": null,
            "players": hand.players().iter().map(|p| json!([p.stack, p.street_bet, p.contributed, p.folded])).collect::<Vec<_>>(),
        });
        let projected = match request.get("view").and_then(Value::as_str) {
            None | Some("native") => false,
            Some("projected") => true,
            Some(other) => return Err(format!("unknown view {other:?}")),
        };
        let agent = request["agent"].as_str().ok_or("agent must be a string")?;
        if agent == "menu" {
            return Ok(response);
        }
        let seed = u64_field(request, "seed")?;
        if let Some(name) = agent.strip_prefix("policy:") {
            let table = self
                .policies
                .get(name)
                .ok_or_else(|| format!("unknown policy {name:?}"))?;
            let tables = self.tables.ok_or("policies need --card-buckets")?;
            let frame = if projected {
                if !multi_view::supports(table.schema) {
                    return Err("projected views need a live-order policy".into());
                }
                Some(multi_view::project(&observation, table.config()?)?)
            } else {
                None
            };
            let projected_view = frame.as_ref().map(|f| f.observation());
            let seen = projected_view.as_ref().unwrap_or(&observation);
            let (probabilities, trained) = table.distribution(seen, tables)?;
            let action = Policy::new(table.clone(), seed).choose(seen, tables)?;
            response["probabilities"] = json!(probabilities);
            response["trained"] = json!(trained);
            response["action"] = action_json(action);
        } else if projected {
            return Err("projected views apply to policies only".into());
        } else if let Some(name) = agent.strip_prefix("script:") {
            response["action"] = action_json(Bot::new(name, seed)?.choose(&observation)?);
        } else {
            return Err(format!("unknown agent {agent:?}"));
        }
        Ok(response)
    }

    fn state(&self, request: &Value) -> Result<Value, String> {
        let hand = replay(request)?;
        let legal = hand
            .legal()
            .map(|l| json!({"check":l.check,"call":l.call_amount,"raise_to":l.raise_to.map(|(a,b)|[a,b])}));
        Ok(json!({"ok":true,"actor":hand.actor(),"finished":hand.finished(),
            "street":if hand.finished(){None}else{Some(hand.street().name())},"board":hand.board(),
            "players":hand.players().iter().map(|p| json!([p.stack, p.street_bet, p.contributed, p.folded])).collect::<Vec<_>>(),
            "legal":legal}))
    }

    fn settle(&self, request: &Value) -> Result<Value, String> {
        let hand = replay(request)?;
        let n = hand.config().players();
        let s = hand.settlement().ok_or("hand is not finished")?;
        Ok(
            json!({"ok":true,"rewards":s.rewards[..n],"contributions":s.contributions[..n],
            "refunds":s.refunds[..n],"pots":s.pots().iter().map(|p|json!([p.amount,p.eligible])).collect::<Vec<_>>()}),
        )
    }

    fn handle(&self, line: &str) -> Value {
        let result = serde_json::from_str::<Value>(line)
            .map_err(|e| format!("invalid JSON: {e}"))
            .and_then(|request| match request["op"].as_str() {
                Some("decide") => self.decide(&request),
                Some("settle") => self.settle(&request),
                Some("state") => self.state(&request),
                _ => Err("op must be decide, settle or state".into()),
            });
        result.unwrap_or_else(|error| json!({"ok":false,"error":error}))
    }
}

fn run() -> Result<(), String> {
    let usage = "serve [--card-buckets DIR] [--policy NAME PATH SHA256]...";
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.first().map(String::as_str) != Some("serve") {
        return Err(usage.into());
    }
    let mut tables = None;
    let mut sources = Vec::new();
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--card-buckets" if i + 1 < args.len() && tables.is_none() => {
                tables = Some(EquityTables::load(Path::new(&args[i + 1]), false)?);
                i += 2;
            }
            "--policy" if i + 3 < args.len() => {
                sources.push((
                    args[i + 1].clone(),
                    args[i + 2].clone(),
                    args[i + 3].clone(),
                ));
                i += 4;
            }
            _ => return Err(usage.into()),
        }
    }
    if !sources.is_empty() && tables.is_none() {
        return Err("policies need --card-buckets".into());
    }
    let mut policies = BTreeMap::new();
    let mut loaded: BTreeMap<String, Arc<PolicyTable>> = BTreeMap::new();
    let mut pins = serde_json::Map::new();
    for (name, path, sha) in sources {
        if name.is_empty() || policies.contains_key(&name) {
            return Err(format!(
                "policy names must be nonempty and distinct: {name:?}"
            ));
        }
        // Several names may pin one file; its weights load once.
        let table = match loaded.get(&sha) {
            Some(t) => t.clone(),
            None => {
                let t = Arc::new(PolicyTable::load(Path::new(&path), &sha)?);
                loaded.insert(sha.clone(), t.clone());
                t
            }
        };
        pins.insert(
            name.clone(),
            json!({"sha256":sha,"identity":table.identity,"players":table.players,
            "strategy":table.mode.name(),"average_scope":table.scope,
            "source_checkpoint_sha256":table.source_checkpoint_sha256,"rows":table.rows.len()}),
        );
        policies.insert(name, table);
    }
    let service = Service { tables, policies };
    let stdout = std::io::stdout();
    let mut out = stdout.lock();
    let ready = json!({"ok":true,"format":FORMAT,"schema":SCHEMA,"menu":MENU,"scripts":SCRIPTS,
        "card_tables":tables.map(|t|t.sha256.clone()),"policies":pins,"loaded_weight_tables":loaded.len()});
    writeln!(out, "{ready}").map_err(|e| e.to_string())?;
    out.flush().map_err(|e| e.to_string())?;
    for line in std::io::stdin().lock().lines() {
        let line = line.map_err(|e| e.to_string())?;
        if line.trim().is_empty() {
            continue;
        }
        writeln!(out, "{}", service.handle(&line)).map_err(|e| e.to_string())?;
        out.flush().map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("nplayer_serve: {e}");
        std::process::exit(2);
    }
}
