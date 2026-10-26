//! Fixed synthetic legal observations for the M4 qualification; no model or play.
use hu20_trainer::{
    game::{Kind, Street},
    multi_holdem,
    nplayer::{Action, Config, Event, Hand},
    river::live::whole_hand::{observation_request, MENU},
};
use serde_json::{json, Value};
use std::{fs::OpenOptions, io::Write};

const BOARDS: [[u8; 5]; 3] = [[0, 13, 26, 39, 48], [4, 5, 18, 31, 44], [0, 8, 16, 28, 44]];
const HOLES: [[u8; 2]; 4] = [[1, 2], [21, 22], [45, 46], [50, 51]];

fn hand(board: [u8; 5], button: usize, hero: usize, hole: [u8; 2]) -> Result<Hand, String> {
    let mut rest = (0..52u8).filter(|c| !board.contains(c) && !hole.contains(c));
    let mut deck = vec![0; 6];
    for seat in 0..3 {
        let cards = if seat == hero {
            hole
        } else {
            [rest.next().unwrap(), rest.next().unwrap()]
        };
        let offset = (seat + 3 - (button + 1) % 3) % 3;
        deck[offset] = cards[0];
        deck[3 + offset] = cards[1];
    }
    deck.extend(board);
    deck.extend(rest);
    Hand::from_deck(Config::new(&[10000; 3], 50, 100)?, button, &deck)
}

fn raise(h: &Hand, label: u8) -> Result<Action, String> {
    multi_holdem::menu(&h.observe(h.actor().ok_or("missing actor")?)?)
        .into_iter()
        .find(|(k, _)| *k == label)
        .map(|(_, a)| a)
        .ok_or_else(|| format!("missing declared raise label {label}"))
}

fn position(history: usize, board_index: usize, entry: usize) -> Result<(Hand, u64), String> {
    let button = (history + board_index) % 3;
    let first = (button + 1) % 3;
    let hero = if entry == 0 { first } else { (button + 2) % 3 };
    let mut h = hand(BOARDS[board_index], button, hero, HOLES[entry])?;
    let mut n = 0;
    while h.street() != Street::River {
        n += 1;
        if n > 64 {
            return Err("panel history bound".into());
        }
        let actor = h.actor().ok_or("panel hand ended before river")?;
        let raised = h.history().iter().any(|e| matches!(e,
            Event::Action { street, action, .. } if *street == h.street() && action.kind == Kind::Raise));
        let action = if h.street() == Street::Preflop && actor == button {
            Action {
                kind: Kind::Fold,
                raise_to: 0,
            }
        } else if actor == first
            && !raised
            && h.street() == Street::Preflop
            && matches!(history, 1 | 3)
        {
            raise(&h, 3)?
        } else if actor == first
            && !raised
            && ((history == 2 && h.street() == Street::Flop)
                || (history == 3 && h.street() == Street::Turn))
        {
            raise(&h, 4)?
        } else {
            Action {
                kind: if h.legal().ok_or("panel legal bounds")?.check {
                    Kind::Check
                } else {
                    Kind::Call
                },
                raise_to: 0,
            }
        };
        if !multi_holdem::menu(&h.observe(actor)?)
            .iter()
            .any(|(_, a)| *a == action)
        {
            return Err("panel action outside production menu".into());
        }
        h.apply_mut(action)?;
    }
    let pot = h.pot();
    if pot != [200, 400, 600, 1200][history] || h.actor() != Some(first) {
        return Err("panel river-start recipe differs".into());
    }
    let prefix = match entry {
        0 => None,
        1 => Some(Action {
            kind: Kind::Check,
            raise_to: 0,
        }),
        2 => Some(raise(&h, 3)?),
        3 => Some(raise(&h, 4)?),
        _ => return Err("invalid panel entry".into()),
    };
    if let Some(a) = prefix {
        h.apply_mut(a)?;
    }
    if h.actor() != Some(hero)
        || h.board() != BOARDS[board_index]
        || h.players().iter().filter(|p| !p.folded).count() != 2
        || h.players().iter().any(|p| !p.folded && p.stack == 0)
        || h.pot() + h.players().iter().map(|p| p.stack).sum::<u64>() != 30000
    {
        return Err("panel legal state/accounting differs".into());
    }
    Ok((h, pot))
}

fn panel() -> Result<Vec<Value>, String> {
    let mut rows = Vec::new();
    for history in 0..4 {
        for board in 0..3 {
            for entry in 0..4 {
                let (h, pot) = position(history, board, entry)?;
                let obs = h.observe(h.actor().unwrap())?;
                let mut request = observation_request(&obs)?;
                request["mode"] = json!("solve");
                request["algorithm"] = json!("dcfr-1.5-0-2");
                request["search_menu"] = json!(MENU);
                request["sweeps"] = json!(2048);
                request["checkpoints"] = json!([8, 16, 32, 64, 128, 256, 512, 1024, 2048]);
                request["stop_at_target"] = json!(true);
                request["target"] = json!({"pot_fraction":0.01,"cap_bb":0.1});
                rows.push(
                    json!({"id":rows.len(),"history":history,"board_index":board,"entry":entry,
                    "river_start_pot_bb":pot as f64/100.,"request":request}),
                );
            }
        }
    }
    Ok(rows)
}

fn run() -> Result<(), String> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 2 {
        return Err("nplayer_river_panel NEW_OUTPUT".into());
    }
    let mut out = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&args[1])
        .map_err(|e| e.to_string())?;
    for row in panel()? {
        writeln!(out, "{row}").map_err(|e| e.to_string())?;
    }
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("nplayer_river_panel: {e}");
        std::process::exit(2);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use hu20_trainer::river::live::whole_hand::eligibility;
    #[test]
    fn all_48_roots_are_legal_balanced_and_exactly_repeatable() {
        let a = panel().unwrap();
        assert_eq!(a.len(), 48);
        assert_eq!(a, panel().unwrap());
        let mut seats = [0; 3];
        for (i, row) in a.iter().enumerate() {
            assert_eq!(row["id"], i);
            let (h, pot) = position(i / 12, (i / 4) % 3, i % 4).unwrap();
            assert_eq!(pot, [200, 400, 600, 1200][i / 12]);
            let o = h.observe(h.actor().unwrap()).unwrap();
            assert_eq!(o.hole, HOLES[i % 4]);
            seats[o.seat] += 1;
            assert_eq!(eligibility(&o, true), "eligible");
            assert_eq!(
                eligibility(&o, false),
                if i % 4 == 0 {
                    "eligible"
                } else {
                    "later-first-entry"
                }
            );
        }
        assert_eq!(seats, [16; 3]);
    }
    #[test]
    fn requests_contain_no_deck_or_other_private_cards() {
        for row in panel().unwrap() {
            let r = &row["request"];
            assert!(r.get("deck").is_none() && r.get("holes").is_none() && r.get("seed").is_none());
            assert_eq!(
                r["hole"],
                json!(HOLES[row["entry"].as_u64().unwrap() as usize])
            );
            assert_eq!(
                r["checkpoints"],
                json!([8, 16, 32, 64, 128, 256, 512, 1024, 2048])
            );
        }
    }
}
