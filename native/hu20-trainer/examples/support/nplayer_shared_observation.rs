//! Evaluator-only comparisons on one acting-seat observation; never draw actions.
use super::{mass, Model};
use hu20_trainer::{
    multi_cfr::Decision,
    multi_checkpoint::key_hex,
    multi_holdem,
    multi_policy::PolicyTable,
    nplayer::{Event, Observation},
};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::HashMap;

pub fn aliases(value: &Value) -> Result<Option<[String; 2]>, String> {
    if value.is_null() {
        return Ok(None);
    }
    let list = value
        .as_array()
        .ok_or("shared_models must be two model aliases")?;
    if list.len() != 2 {
        return Err("shared_models must be two model aliases".into());
    }
    let names: Vec<_> = list
        .iter()
        .map(|v| v.as_str().map(str::to_owned).ok_or("shared model alias"))
        .collect::<Result<_, _>>()?;
    if names[0] == names[1] || names.iter().any(|s| s.is_empty() || s.starts_with("bot=")) {
        return Err("shared_models must name two distinct weight tables".into());
    }
    Ok(Some([names[0].clone(), names[1].clone()]))
}

/// This projection cannot access opponent cards, deck order or future boards.
/// It binds an exact legal observation rather than an abstract information key.
pub fn observation_fingerprint(view: &Observation<'_>) -> Result<String, String> {
    if view.actor != Some(view.seat) || view.legal.is_none() {
        return Err("shared query requires acting-seat observation".into());
    }
    let legal = view.legal.as_ref().unwrap();
    let history: Vec<_> = view
        .history
        .iter()
        .map(|event| match event {
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
    let public = json!({"format":"nplayer-legal-observation-v1", "seat":view.seat,
        "button":view.button, "hole":view.hole, "board":view.board, "street":view.street.name(),
        "actor":view.actor, "stacks":view.config.stacks(), "sb":view.config.small_blind(),
        "bb":view.config.big_blind(), "players":view.players.iter().map(|p|
            json!([p.stack,p.street_bet,p.contributed,p.folded])).collect::<Vec<_>>(),
        "legal":{"check":legal.check,"call":legal.call_amount,"raise_to":legal.raise_to},
        "history":history});
    Ok(format!(
        "{:x}",
        Sha256::digest(serde_json::to_vec(&public).map_err(|e| e.to_string())?)
    ))
}

fn distribution(table: &PolicyTable, d: &Decision) -> Result<Value, String> {
    let row = table.rows.get(&d.key);
    if row.is_some_and(|r| {
        (r.owner as usize, r.street as usize, r.code) != (d.owner, d.street, d.code)
    }) {
        return Err("shared lookup key/action identity mismatch".into());
    }
    let status = mass::LABELS[mass::MassMetadata::classify_row(row)?];
    let probabilities = row
        .map(|r| r.probabilities.to_vec())
        .unwrap_or_else(|| vec![1. / d.len() as f64; d.len()]);
    if probabilities.len() != d.len()
        || probabilities.is_empty()
        || probabilities.iter().any(|p| !p.is_finite() || *p < 0.)
        || (probabilities.iter().sum::<f64>() - 1.).abs() > 1e-10
    {
        return Err("shared lookup invalid probability row".into());
    }
    if status == "zero_mass"
        && probabilities
            .iter()
            .any(|p| (*p - 1. / d.len() as f64).abs() > 1e-14)
    {
        return Err("shared zero mass must use uniform fallback".into());
    }
    Ok(json!({"status":status,"probabilities":probabilities}))
}

pub fn query(
    view: &Observation<'_>,
    d: &Decision,
    aliases: &[String; 2],
    models: &HashMap<String, Model>,
) -> Result<Value, String> {
    let fingerprint = observation_fingerprint(view)?;
    let actions = multi_holdem::menu(view)
        .iter()
        .map(|(_, a)| json!([a.kind.name(), a.raise_to]))
        .collect::<Vec<_>>();
    if actions.len() != d.len() || d.actor != view.seat || d.street != view.street as usize {
        return Err("shared decision/observation mismatch".into());
    }
    let mut queries = Vec::new();
    for alias in aliases {
        let model = models.get(alias).ok_or("shared model alias absent")?;
        if model.table.config() != view.config {
            return Err("shared model/game identity differs".into());
        }
        // `d` is keyed by the released history schema.
        if model.table.schema != multi_holdem::KeySchema::History {
            return Err("shared queries support history keys only".into());
        }
        let mut value = distribution(&model.table, d)?;
        value["alias"] = json!(alias);
        queries.push(value);
    }
    Ok(
        json!({"format":"nplayer-shared-observation-v1","observation_sha256":fingerprint,
        "key":key_hex(&d.key),"actions":actions,"queries":queries}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use hu20_trainer::nplayer::{Config, Hand};

    fn table() -> (std::path::PathBuf, PolicyTable) {
        use flate2::{write::GzEncoder, Compression};
        use std::io::Write;
        let path = std::env::temp_dir().join(format!(
            "shared-query-{}-{}.gz",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let mut out = GzEncoder::new(Vec::new(), Compression::default());
        let identity = json!({"players":6,"stacks":vec![10000;6],"small_blind":50,"big_blind":100,
            "schema":multi_holdem::SCHEMA,"menu":multi_holdem::MENU,"game":"nlhe-cash",
            "utility_unit":"big-blind","card_tables":hu20_trainer::cards::EQUITY_K50_SHA256});
        writeln!(
            out,
            "{}",
            json!({"format":"nplayer-policy-v1","identity":identity,"players":6,"entries":2,
            "strategy":"average","last_average_street":3,"continuation":"none","missing":"uniform",
            "source_checkpoint_sha256":"a".repeat(64)})
        )
        .unwrap();
        for (key, probabilities) in [(1, vec![0.75, 0.25]), (2, vec![0.5, 0.5])] {
            writeln!(
                out,
                "{}",
                json!([key_hex(&[key; 16]), 0, 0, 5, probabilities])
            )
            .unwrap();
        }
        std::fs::write(&path, out.finish().unwrap()).unwrap();
        let digest = hu20_trainer::export::sha256_file(&path);
        let mut table = PolicyTable::load(&path, &digest).unwrap();
        table.rows.tag_all_mass(true);
        table.rows.tag_mass(&[2; 16], false).unwrap();
        (path, table)
    }

    #[test]
    fn exact_rows_zero_mass_and_missing_keep_distinct_statuses() {
        let (path, table) = table();
        let mut d = Decision {
            key: [1; 16],
            actor: 0,
            owner: 0,
            street: 0,
            code: 5,
        };
        assert_eq!(
            distribution(&table, &d).unwrap(),
            json!({"status":"positive_mass","probabilities":[0.75,0.25]})
        );
        d.key = [2; 16];
        assert_eq!(
            distribution(&table, &d).unwrap(),
            json!({"status":"zero_mass","probabilities":[0.5,0.5]})
        );
        d.key = [3; 16];
        assert_eq!(
            distribution(&table, &d).unwrap(),
            json!({"status":"missing","probabilities":[0.5,0.5]})
        );
        d.key = [1; 16];
        d.owner = 1;
        assert!(distribution(&table, &d).is_err());
        d.owner = 0;
        d.code = 7;
        assert!(distribution(&table, &d).is_err());
        std::fs::remove_file(path).unwrap();
    }

    #[test]
    fn shared_aliases_are_explicit_and_fail_closed() {
        assert!(aliases(&Value::Null).unwrap().is_none());
        assert_eq!(
            aliases(&json!(["control", "candidate"])).unwrap().unwrap(),
            ["control", "candidate"]
        );
        for invalid in [
            json!([]),
            json!(["a"]),
            json!(["a", "a"]),
            json!(["a", "bot=random"]),
            json!(["a", 2]),
        ] {
            assert!(aliases(&invalid).is_err());
        }
    }

    #[test]
    fn fingerprint_ignores_opponent_cards_and_future_cards() {
        let cfg = Config::new(&[10000; 6], 50, 100).unwrap();
        let deck: Vec<u8> = (0..52).collect();
        let a = Hand::from_deck(cfg, 0, &deck).unwrap();
        let actor = a.actor().unwrap();
        let original = observation_fingerprint(&a.observe(actor).unwrap()).unwrap();
        let mut changed = deck.clone();
        // Hole cards are dealt to seats1..5,0; swap another seat's card and an unused card.
        let other = (0..6).find(|&offset| (offset + 1) % 6 != actor).unwrap();
        changed.swap(other, 40);
        changed.swap(12, 45); // First unrevealed public card.
        let b = Hand::from_deck(cfg, 0, &changed).unwrap();
        assert_eq!(a.observe(actor).unwrap(), b.observe(actor).unwrap());
        assert_eq!(
            original,
            observation_fingerprint(&b.observe(actor).unwrap()).unwrap()
        );
        let own = (0..6).find(|&offset| (offset + 1) % 6 == actor).unwrap();
        changed.swap(own, 41);
        let c = Hand::from_deck(cfg, 0, &changed).unwrap();
        assert_ne!(
            original,
            observation_fingerprint(&c.observe(actor).unwrap()).unwrap()
        );
    }
}
