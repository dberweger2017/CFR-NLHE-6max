//! Privileged duplicate host. Bots and models receive only acting observations.
use hu20_trainer::{
    cards::EquityTables,
    multi_arena::{stream_seed, Bot, PERMUTATIONS},
    multi_policy::{Policy, PolicyTable},
    nplayer::{Config, Event, Hand},
};
use rand::{seq::SliceRandom, SeedableRng};
use rayon::prelude::*;
use serde_json::{json, Value};
use std::{collections::HashMap, io::Write, path::Path, sync::Arc, time::Instant};

enum Player {
    Model(Policy),
    Script(Bot),
}
fn snapshot(hand: &Hand) -> Value {
    let legal = hand
        .legal()
        .map(|l| json!({"check":l.check,"call":l.call_amount,"raise_to":l.raise_to}));
    json!({"actor":hand.actor(),"finished":hand.finished(),"board":hand.board(),
        "street":if hand.finished(){None}else{Some(hand.street().name())},"pot":hand.pot(),
        "wager":if hand.finished(){None}else{Some(hand.wager())},"min_raise":if hand.finished(){None}else{Some(hand.min_raise())},
        "players":hand.players().iter().map(|p|json!([p.stack,p.street_bet,p.contributed,p.folded])).collect::<Vec<_>>(),
        "holes":(0..hand.config().players()).map(|p|hand.observe(p).unwrap().hole).collect::<Vec<_>>(),"legal":legal,
        "rewards":hand.settlement().map(|s|s.rewards[..hand.config().players()].to_vec())})
}
fn play_block(block:u64, root:u64, config:Config, tables:Option<&EquityTables>,
    cache:&HashMap<String,Arc<PolicyTable>>, singleton:&str, pair:&str)
    ->Result<(Vec<u8>,[[u64;4];3],[[u64;4];3]),String> {
    let mut bytes=Vec::new();
    let mut decisions=[[0u64;4];3];let mut misses=[[0u64;4];3];
        let mut deck: Vec<u8> = (0..52).collect();
        deck.shuffle(&mut rand::rngs::StdRng::seed_from_u64(stream_seed(
            root, b"deck", block, 0,
        )));
        let button = block as usize % 3;
        for (permutation, ids) in PERMUTATIONS.iter().enumerate() {
            // Reset by labeled identity each duplicate. Action draws never advance the deck stream.
            let mut players = Vec::new();
            for id in 0..3 {
                let seed = stream_seed(root, b"action", block, id);
                let spec = if id == 0 { singleton } else { pair };
                players.push(if let Some(name) = spec.strip_prefix("bot=") {
                    Player::Script(Bot::new(name, seed)?)
                } else {
                    Player::Model(Policy::new(cache[spec].clone(), seed))
                });
            }
            let mut hand = Hand::from_deck(config, button, &deck)?;
            let mut states = vec![snapshot(&hand)];
            let mut actions = Vec::new();
            let mut actors = Vec::new();
            while let Some(actor) = hand.actor() {
                if actions.len() >= 10000 {
                    return Err("hand action bound".into());
                }
                let observation = hand.observe(actor)?;
                let street = observation.street as usize;
                let id = ids[actor];
                let action = match &mut players[id] {
                    Player::Script(bot) => bot.choose(&observation)?,
                    Player::Model(policy) => {
                        let old = policy.misses;
                        let action = policy.choose(&observation, tables.unwrap())?;
                        misses[id][street] += policy.misses - old;
                        action
                    }
                };
                decisions[id][street] += 1;
                hand.apply_mut(action)?;
                actors.push(actor);
                actions.push(json!([action.kind.name(), action.raise_to]));
                states.push(snapshot(&hand));
            }
            let s = hand.settlement().ok_or("hand did not settle")?;
            if s.rewards.iter().sum::<i64>() != 0 {
                return Err("non-zero-sum settlement".into());
            }
            let history: Vec<_> = hand
                .history()
                .iter()
                .map(|e| match e {
                    Event::Board(s) => json!([s.name(), "board"]),
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
            writeln!(&mut bytes,"{}",json!({"hand":block*6+permutation as u64,"block":block,"permutation":permutation,"identities":ids,"rewards":s.rewards[..3],"stacks":config.stacks(),"button":button,"sb":50,"bb":100,"deck":deck,"actors":actors,"actions":actions,"states":states,"history":history,"settlement":{"contributions":s.contributions[..3],"refunds":s.refunds[..3],"pots":s.pots().iter().map(|p|json!([p.amount,p.eligible])).collect::<Vec<_>>()}})).map_err(|e|e.to_string())?;
        }
    Ok((bytes,decisions,misses))
}
// EquityTables::load returns process-lifetime storage. Reuse it for the whole
// batch; loading in each lineup would retain another complete K50 set.
fn tables_for_case(path: &Path, needed: bool, cached: &mut Option<&'static EquityTables>)
    -> Result<Option<&'static EquityTables>, String> {
    if !needed { return Ok(None); }
    if cached.is_none() { *cached = Some(EquityTables::load(path, false)?); }
    Ok(*cached)
}
fn run_case(a: &[String], cache: &mut HashMap<String,Arc<PolicyTable>>,
    card_tables: &mut Option<&'static EquityTables>) -> Result<Value, String> {
    if a.len() != 7 && a.len() != 9 {
        return Err(
            "K50 BLOCKS ROOT NEW_TRACE SINGLETON PAIR [STACK_BB THREADS] (policy=PATH@SHA256 or bot=NAME)".into(),
        );
    }
    let blocks: u64 = a[2].parse().map_err(|_| "invalid blocks")?;
    if !(2..=1_000_000).contains(&blocks) {
        return Err("blocks must be 2..1000000".into());
    }
    let root: u64 = a[3].parse().map_err(|_| "invalid root")?;
    let stack:u64=if a.len()==9 {a[7].parse().map_err(|_|"invalid stack")?}else{20};
    let threads:usize=if a.len()==9 {a[8].parse().map_err(|_|"invalid threads")?}else{1};
    if ![20,100].contains(&stack) || !(1..=16).contains(&threads) {return Err("arena stack/thread bounds".into());}
    let started = Instant::now();
    let mut pins = Vec::new();
    let config = Config::new(&[stack*100; 3], 50, 100)?;
    let mut identity = None;
    for spec in [&a[5], &a[6], &a[6]] {
        if let Some(name) = spec.strip_prefix("bot=") {
            Bot::new(name, 0)?;
            pins.push(json!({"script":name,"version":"nplayer-scripts-v1"}));
        } else if let Some(pin) = spec.strip_prefix("policy=") {
            let (path, sha) = pin.rsplit_once('@').ok_or("policy requires PATH@SHA256")?;
            if !cache.contains_key(spec) {
                // A batch keeps at most its current two distinct models resident.
                if cache.len()>=2 {cache.retain(|key,_|key==&a[5] || key==&a[6]);}
                let table = Arc::new(PolicyTable::load(Path::new(path), sha)?);
                cache.insert(spec.clone(), table);
            }
            let t = &cache[spec];
            if t.config() != config {
                return Err("arena requires the requested three-player stack and50/100 identity".into());
            }
            if identity.as_ref().is_some_and(|i| i != &t.identity) {
                return Err("mixed game identities".into());
            }
            identity = Some(t.identity.clone());
            pins.push(json!({"sha256":sha,"strategy":t.mode.name(),"average_scope":t.scope,"source_checkpoint_sha256":t.source_checkpoint_sha256}));
        } else {
            return Err("expected policy=PATH@SHA256 or bot=NAME".into());
        }
    }
    let tables = tables_for_case(Path::new(&a[1]), !cache.is_empty(), card_tables)?;
    let identity = identity.unwrap_or_else(
        || json!({"players":3,"stacks":vec![stack*100;3],"small_blind":50,"big_blind":100}),
    );
    let load_seconds = started.elapsed().as_secs_f64();
    let mut out = std::io::BufWriter::new(
        std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&a[4])
            .map_err(|e| e.to_string())?,
    );
    let used_tables=usize::from(a[5].starts_with("policy="))+
        usize::from(a[6].starts_with("policy=") && a[6]!=a[5]);
    writeln!(out,"{}",json!({"format":"nplayer-privileged-policy-replay-v1","harness":"nplayer-duplicate-v1","identity":identity,"hands":blocks*6,"blocks":blocks,"seed":root,"policies":pins,"distinct_policy_instances":3,"loaded_weight_tables":used_tables,"seat_semantics":"fixed physical seats; button=block%3; permutation maps seat to identity; identity0 singleton"})).map_err(|e|e.to_string())?;
    let playing = Instant::now();
    let mut decisions = [[0u64; 4]; 3];
    let mut misses = [[0u64; 4]; 3];
    // Bound queued trace bytes and preserve the serial block/permutation order.
    for start in (0..blocks).step_by(threads*2) {
        if std::env::var_os("NPLAYER_STOP_FILE").is_some_and(|p|Path::new(&p).exists()) {
            return Err(format!("clean stop before block {start}; partial trace retained"));
        }
        let rows:Vec<_>=(start..(start+2*threads as u64).min(blocks)).into_par_iter()
            .map(|block|play_block(block,root,config,tables,&cache,&a[5],&a[6])).collect();
        for row in rows {
            let (bytes,d,m)=row?;out.write_all(&bytes).map_err(|e|e.to_string())?;
            for id in 0..3 {for street in 0..4 {decisions[id][street]+=d[id][street];misses[id][street]+=m[id][street];}}
        }
    }
    out.flush().map_err(|e| e.to_string())?;
    Ok(json!({"status":"passed","blocks":blocks,"hands":blocks*6,"load_seconds":load_seconds,
        "play_seconds":playing.elapsed().as_secs_f64(),"decisions_by_identity_street":decisions,
        "misses_by_identity_street":misses,"trace_sha256":hu20_trainer::export::sha256_file(Path::new(&a[4]))}))
}
fn run()->Result<(),String>{
    let a:Vec<String>=std::env::args().collect();
    let mut cache=HashMap::new();
    let mut card_tables=None;
    if a.len()==3 && a[1]=="batch" {
        let m:Value=serde_json::from_slice(&std::fs::read(&a[2]).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
        let threads=m["threads"].as_u64().ok_or("batch threads")?;
        if !(1..=16).contains(&threads){return Err("batch thread bound".into());}
        rayon::ThreadPoolBuilder::new().num_threads(threads as usize).build_global().map_err(|e|e.to_string())?;
        for row in m["cases"].as_array().ok_or("batch cases")? {
            let args=vec![a[0].clone(),m["tables"].as_str().ok_or("tables")?.into(),
                row["blocks"].as_u64().ok_or("blocks")?.to_string(),row["root"].as_u64().ok_or("root")?.to_string(),
                row["trace"].as_str().ok_or("trace")?.into(),row["singleton"].as_str().ok_or("singleton")?.into(),
                row["pair"].as_str().ok_or("pair")?.into(),m["stack_bb"].as_u64().ok_or("stack_bb")?.to_string(),threads.to_string()];
            let result=run_case(&args,&mut cache,&mut card_tables)?;
            let mut summary=std::fs::OpenOptions::new().write(true).create_new(true)
                .open(row["summary"].as_str().ok_or("summary")?).map_err(|e|e.to_string())?;
            writeln!(&mut summary,"{result}").map_err(|e|e.to_string())?;
            println!("{}",json!({"event":"progress","completed":row["name"],"resident_weight_tables":cache.len()}));
            std::io::stdout().flush().map_err(|e|e.to_string())?;
        }
    }else{
        let threads:usize=if a.len()==9 {a[8].parse().map_err(|_|"threads")?}else{1};
        if !(1..=16).contains(&threads){return Err("thread bound".into());}
        rayon::ThreadPoolBuilder::new().num_threads(threads).build_global().map_err(|e|e.to_string())?;
        println!("{}",run_case(&a,&mut cache,&mut card_tables)?);
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("nplayer_arena: {error}");
        std::process::exit(2);
    }
}

#[cfg(test)]
mod batch_resource_tests {
    use super::*;

    #[test]
    #[ignore = "Requires pinned K50 files; run guarded with NPLAYER_K50_TABLES"]
    fn seventy_two_lineups_reuse_one_card_table_set() {
        let path = std::env::var("NPLAYER_K50_TABLES").expect("pinned K50 directory");
        let mut cached = None;
        assert!(tables_for_case(Path::new(&path), false, &mut cached).unwrap().is_none());
        let first = tables_for_case(Path::new(&path), true, &mut cached).unwrap().unwrap();
        for _ in 1..72 {
            let next = tables_for_case(Path::new(&path), true, &mut cached).unwrap().unwrap();
            assert!(std::ptr::eq(first, next));
        }
        assert!(tables_for_case(Path::new(&path), false, &mut cached).unwrap().is_none());
        assert!(std::ptr::eq(first, cached.unwrap()));
    }
}
