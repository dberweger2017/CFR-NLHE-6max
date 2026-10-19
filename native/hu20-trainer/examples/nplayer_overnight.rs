//! Bounded campaign host. The training table is borrowed immutably by probes;
//! policies receive acting-seat observations, never simulator state or seeds.
use hu20_trainer::{
    cards::EquityTables, gz::Gzip,
    multi_arena::{stream_seed, Bot, PERMUTATIONS},
    multi_cfr::{Game, Sampling, Trainer}, multi_checkpoint,
    multi_holdem::{self, CashGame}, multi_policy::PolicyTable,
    nplayer::{Action, Config, Hand, Observation},
};
use rand::{Rng, SeedableRng, seq::SliceRandom};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{io::Write, path::Path, time::Instant};

fn emit(value: Value) { println!("{value}"); std::io::stdout().flush().unwrap(); }
fn distribution(t: &Trainer, o: &Observation<'_>, tables: &EquityTables) -> Result<(Vec<f64>, bool), String> {
    if o.actor != Some(o.seat) || o.legal.is_none() { return Err("probe needs acting observation".into()); }
    let d = multi_holdem::observation_decision(o, tables);
    if let Some(e) = t.table.get(&d.key) {
        e.check(d);
        Ok((e.policy(true)[..d.len()].to_vec(), true))
    } else { Ok((vec![1. / d.len() as f64; d.len()], false)) }
}
fn choose(t: &Trainer, o: &Observation<'_>, tables: &EquityTables, rng: &mut rand::rngs::StdRng,
          reference: Option<&PolicyTable>) -> Result<(Action, bool), String> {
    let (p, found) = distribution(t, o, tables)?;
    if let Some(reference) = reference {
        if (p.clone(), found) != reference.distribution(o, tables)? { return Err("in-memory/export policy differs".into()); }
    }
    let draw: f64 = rng.gen();
    let mut sum = 0.;
    let mut selected = p.iter().rposition(|&v| v > 0.).ok_or("empty support")?;
    for (i, v) in p.iter().enumerate() { sum += v; if draw < sum { selected = i; break; } }
    Ok((multi_holdem::menu(o)[selected].1, found))
}
fn probe(t: &Trainer, tables: &EquityTables, blocks: u64, root: u64, reference: Option<&PolicyTable>) -> Result<Value, String> {
    let started = Instant::now();
    let mut results = Vec::new();
    for (index, name) in ["random", "check-call", "tight-aggressive", "pot-pressure"].iter().enumerate() {
        let root = root + index as u64;
        let mut values = Vec::new();
        let mut decisions = [0u64;4]; let mut missing = [0u64;4];
        let mut seats = [0i64;3];
        let mut fingerprint = Sha256::new();
        for block in 0..blocks {
            let mut deck: Vec<u8> = (0..52).collect();
            deck.shuffle(&mut rand::rngs::StdRng::seed_from_u64(stream_seed(root,b"deck",block,0)));
            let mut reward = 0i64;
            for (permutation, ids) in PERMUTATIONS.into_iter().enumerate() {
                let mut rng = rand::rngs::StdRng::seed_from_u64(stream_seed(root,b"action",block,0));
                let mut bots = [Bot::new(name,stream_seed(root,b"action",block,1))?,
                                Bot::new(name,stream_seed(root,b"action",block,2))?];
                let mut hand = Hand::from_deck(Config::new(&[2000;3],50,100)?,block as usize%3,&deck)?;
                let mut actions = 0;
                let mut actors = Vec::new(); let mut played = Vec::new();
                while let Some(actor) = hand.actor() {
                    if actions >= 10000 { return Err("probe action bound".into()); }
                    let o = hand.observe(actor)?;
                    let id = ids[actor];
                    let action = if id == 0 {
                        let (a,found) = choose(t,&o,tables,&mut rng,reference)?;
                        decisions[o.street as usize] += 1; missing[o.street as usize] += u64::from(!found); a
                    } else { bots[id-1].choose(&o)? };
                    actors.push(actor); played.push(json!([action.kind.name(),action.raise_to]));
                    hand.apply_mut(action)?; actions += 1;
                }
                let s = hand.settlement().ok_or("probe not settled")?;
                if s.rewards.iter().sum::<i64>() != 0 { return Err("probe accounting".into()); }
                let body=json!([block,permutation,actors,played,&s.rewards[..3]]);
                fingerprint.update(serde_json::to_vec(&body).map_err(|e|e.to_string())?); fingerprint.update(b"\n");
                let seat = ids.iter().position(|&id|id==0).unwrap();
                reward += s.rewards[seat]; seats[seat] += s.rewards[seat];
            }
            values.push(reward as f64 / 6.); // BB/100 at exactly100 chips/BB.
        }
        results.push(json!({"bot":name,"root":root,"block_bb100":values,"seat_reward_chips":seats,
                           "decisions_by_street":decisions,"missing_by_street":missing,"play_sha256":format!("{:x}",fingerprint.finalize())}));
    }
    Ok(json!({"event":"probe","nodes":t.counts.nodes,"iteration":t.iteration,"blocks":blocks,
              "seconds":started.elapsed().as_secs_f64(),"results":results}))
}
fn run() -> Result<(),String> {
    let args:Vec<String> = std::env::args().collect();
    if args.len()!=2 { return Err("CONFIG.json".into()); }
    let c:Value = serde_json::from_slice(&std::fs::read(&args[1]).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    let seed=c["seed"].as_u64().ok_or("seed")?;
    let threads=c["threads"].as_u64().ok_or("threads")?;
    if threads!=16 { return Err("campaign requires16 threads".into()); }
    rayon::ThreadPoolBuilder::new().num_threads(16).build_global().map_err(|e|e.to_string())?;
    let tables=EquityTables::load(Path::new(c["tables"].as_str().ok_or("tables")?),false)?;
    let game=CashGame{config:Config::new(&[2000;3],50,100)?,tables};
    let input=Path::new(c["input"].as_str().ok_or("input")?);
    if hu20_trainer::export::sha256_file(input)!=c["input_sha256"].as_str().ok_or("input hash")? { return Err("input SHA mismatch".into()); }
    emit(json!({"event":"phase","phase":"load","target":0}));
    let mut t=multi_checkpoint::load(input)?;
    if t.identity!=game.identity() || t.seed!=seed || t.players!=3 || t.sampling!=Sampling::Path || t.roots_per_seat!=8 ||
       t.last_average_street!=3 || t.freeze_at_cap || t.frozen_at.is_some() || t.max_entries!=150_000_000 {
        return Err("resume configuration mismatch".into());
    }
    let out=Path::new(c["out"].as_str().ok_or("out")?);
    std::fs::create_dir(out).map_err(|e|e.to_string())?;
    let targets:Vec<u64>=c["targets"].as_array().ok_or("targets")?.iter().map(|v|v.as_u64().ok_or("target".to_string())).collect::<Result<_,_>>()?;
    if targets.is_empty() || targets.windows(2).any(|w|w[0]>=w[1]) || targets[0]<=t.counts.nodes { return Err("non-increasing targets".into()); }
    let probe_nodes:Vec<u64>=c["probe_nodes"].as_array().ok_or("probe_nodes")?.iter().map(|v|v.as_u64().ok_or("probe node".to_string())).collect::<Result<_,_>>()?;
    let blocks=c["probe_blocks"].as_u64().ok_or("probe blocks")?;
    if blocks!=0 && !(2..=1024).contains(&blocks) { return Err("probe blocks out of bound".into()); }
    let root=c["probe_root"].as_u64().ok_or("probe root")?;
    let reference=if let Some(path)=c["reference"].as_str() { Some(PolicyTable::load(Path::new(path),c["reference_sha256"].as_str().ok_or("reference hash")?)?) } else {None};
    let initial=t.counts.nodes;
    let mut active=0.; let mut monitor=0.; let mut next_probe=0;
    let mut last_progress=Instant::now();
    for target in targets {
        emit(json!({"event":"phase","phase":"train","target":target}));
        while t.counts.nodes < target {
            if blocks>0 && next_probe<probe_nodes.len() && t.counts.nodes>=probe_nodes[next_probe] {
                emit(json!({"event":"phase","phase":"probe","target":t.counts.nodes}));
                let event=probe(&t,&tables,blocks,root,reference.as_ref())?;
                monitor+=event["seconds"].as_f64().unwrap();emit(event);next_probe+=1;
                emit(json!({"event":"phase","phase":"train","target":target}));
            }
            if t.table.len()>=t.max_entries { return Err("capacity stop; no freezing".into()); }
            if Path::new(c["stop_file"].as_str().ok_or("stop file")?).exists() { return Err("owner stop file".into()); }
            let tick=Instant::now();t.step_fast(&game);active+=tick.elapsed().as_secs_f64();
            if last_progress.elapsed().as_secs_f64()>=30. {
                emit(json!({"event":"progress","nodes":t.counts.nodes,"iteration":t.iteration,"entries":t.table.len(),
                    "active_seconds":active,"monitor_seconds":monitor,"nodes_per_second":(t.counts.nodes-initial)as f64/active}));
                last_progress=Instant::now();
            }
        }
        while blocks>0 && next_probe<probe_nodes.len() && t.counts.nodes>=probe_nodes[next_probe] {
            emit(json!({"event":"phase","phase":"probe","target":t.counts.nodes}));
            let e=probe(&t,&tables,blocks,root,reference.as_ref())?;monitor+=e["seconds"].as_f64().unwrap();emit(e);next_probe+=1;
            emit(json!({"event":"phase","phase":"train","target":target}));
        }
        emit(json!({"event":"trained","target":target,"nodes":t.counts.nodes,"iteration":t.iteration,"entries":t.table.len(),
                    "active_seconds":active,"monitor_seconds":monitor,"counts":multi_checkpoint::counts_json(&t.counts)}));
        emit(json!({"event":"phase","phase":"save","target":target}));
        let path=out.join(format!("{target}.gz"));let tick=Instant::now();multi_checkpoint::save(&t,&path,Gzip::Compatible)?;
        let save=tick.elapsed().as_secs_f64();emit(json!({"event":"phase","phase":"hash","target":target}));
        let digest=hu20_trainer::export::sha256_file(&path);
        emit(json!({"event":"checkpoint","target":target,"path":path,"sha256":digest,"save_seconds":save}));
        emit(json!({"event":"phase","phase":"train","target":target}));
    }
    emit(json!({"event":"complete","active_seconds":active,"monitor_seconds":monitor,"nodes":t.counts.nodes}));Ok(())
}
fn main(){if let Err(e)=run(){eprintln!("nplayer_overnight: {e}");std::process::exit(2);}}
