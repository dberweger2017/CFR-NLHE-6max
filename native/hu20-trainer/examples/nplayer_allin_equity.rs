//! Exact all-in expectations for saved n-player showdowns.
//!
//! Reads one JSON object per line: `id`, `button`, `holes`, the visible
//! `board`, the `realized` five-card board, the recorded `pots` as
//! `[amount, eligible mask]`, `refunds`, `contributions` and `rewards`.
//! Writes `id`, each seat's expected reward over every runout of the unseen
//! cards (all hole cards and the visible board excluded), and whether the
//! engine's split rule reproduces the recorded rewards on the realized board.
use hu20_buckets::evaluate;
use rayon::prelude::*;
use serde_json::{json, Value};
use std::io::{BufRead, Write};

struct Showdown {
    id: Value,
    button: usize,
    holes: Vec<[u8; 2]>,
    board: Vec<u8>,
    realized: Vec<u8>,
    pots: Vec<(u64, u8)>,
    refunds: Vec<i64>,
    contributions: Vec<i64>,
    rewards: Vec<i64>,
}

fn list(v: &Value, key: &str) -> Result<Vec<u64>, String> {
    v[key]
        .as_array()
        .ok_or(format!("{key} must be a list"))?
        .iter()
        .map(|x| x.as_u64().ok_or(format!("{key} must hold integers")))
        .collect()
}

fn parse(line: &str) -> Result<Showdown, String> {
    let v: Value = serde_json::from_str(line).map_err(|e| e.to_string())?;
    let holes: Vec<[u8; 2]> = v["holes"]
        .as_array()
        .ok_or("holes")?
        .iter()
        .map(|h| {
            let h = h.as_array().ok_or("hole")?;
            Ok([h[0].as_u64().ok_or("card")? as u8, h[1].as_u64().ok_or("card")? as u8])
        })
        .collect::<Result<_, String>>()?;
    let n = holes.len();
    let pots = v["pots"]
        .as_array()
        .ok_or("pots")?
        .iter()
        .map(|p| Ok((p[0].as_u64().ok_or("pot amount")?, p[1].as_u64().ok_or("pot mask")? as u8)))
        .collect::<Result<Vec<_>, String>>()?;
    let signed = |key| -> Result<Vec<i64>, String> {
        let values: Vec<i64> = v[key]
            .as_array()
            .ok_or(format!("{key} must be a list"))?
            .iter()
            .map(|x| x.as_i64().ok_or(format!("{key} must hold integers")))
            .collect::<Result<_, _>>()?;
        if values.len() == n { Ok(values) } else { Err(format!("{key} length")) }
    };
    let s = Showdown {
        id: v["id"].clone(),
        button: v["button"].as_u64().ok_or("button")? as usize,
        board: list(&v, "board")?.into_iter().map(|c| c as u8).collect(),
        realized: list(&v, "realized")?.into_iter().map(|c| c as u8).collect(),
        refunds: signed("refunds")?,
        contributions: signed("contributions")?,
        rewards: signed("rewards")?,
        holes,
        pots,
    };
    if !(2..=6).contains(&n) || s.button >= n || s.board.len() > 5 || s.realized.len() != 5 {
        return Err("table, button or board shape".into());
    }
    if s.realized[..s.board.len()] != s.board[..] {
        return Err("visible board is not a prefix of the realized board".into());
    }
    Ok(s)
}

/// Rewards on one complete board, by the engine's pot and odd-chip rule.
fn settle(s: &Showdown, board: &[u8; 5], out: &mut [i64]) {
    let n = s.holes.len();
    // Only seats eligible for some pot can win; folded hands are never evaluated.
    let contenders = s.pots.iter().fold(0u8, |m, p| m | p.1);
    let mut ranks = [0u32; 6];
    for (seat, h) in s.holes.iter().enumerate() {
        if contenders & (1 << seat) != 0 {
            ranks[seat] = evaluate(&[h[0], h[1], board[0], board[1], board[2], board[3], board[4]]);
        }
    }
    for seat in 0..n {
        out[seat] = s.refunds[seat] - s.contributions[seat];
    }
    for &(amount, eligible) in &s.pots {
        let best = (0..n).filter(|i| eligible & (1 << i) != 0).map(|i| ranks[i]).max().unwrap();
        let winners = (0..n).filter(|&i| eligible & (1 << i) != 0 && ranks[i] == best).fold(0u8, |m, i| m | 1 << i);
        let share = amount / winners.count_ones() as u64;
        let mut remainder = amount % winners.count_ones() as u64;
        for offset in 1..=n {
            let seat = (s.button + offset) % n;
            if winners & (1 << seat) != 0 {
                out[seat] += (share + u64::from(remainder > 0)) as i64;
                remainder = remainder.saturating_sub(1);
            }
        }
    }
}

fn expectation(s: &Showdown) -> (Vec<f64>, bool) {
    let n = s.holes.len();
    let mut realized = [0i64; 6];
    let full: [u8; 5] = s.realized[..].try_into().unwrap();
    settle(s, &full, &mut realized);
    let ok = realized[..n] == s.rewards[..];
    let mut used = 0u64;
    for &c in s.holes.iter().flatten().chain(&s.board) {
        used |= 1 << c;
    }
    let unseen: Vec<u8> = (0..52).filter(|c| used & (1u64 << c) == 0).collect();
    let k = 5 - s.board.len();
    let mut board = [0u8; 5];
    board[..s.board.len()].copy_from_slice(&s.board);
    let mut sums = [0f64; 6];
    let mut count = 0u64;
    let mut out = [0i64; 6];
    let mut index: Vec<usize> = (0..k).collect();
    loop {
        for (slot, &i) in index.iter().enumerate() {
            board[s.board.len() + slot] = unseen[i];
        }
        settle(s, &board, &mut out);
        for seat in 0..n {
            sums[seat] += out[seat] as f64;
        }
        count += 1;
        // Next k-combination of the unseen cards in lexicographic order.
        let mut slot = k;
        while slot > 0 && index[slot - 1] == unseen.len() - k + slot - 1 {
            slot -= 1;
        }
        if slot == 0 {
            break;
        }
        index[slot - 1] += 1;
        for j in slot..k {
            index[j] = index[j - 1] + 1;
        }
    }
    ((0..n).map(|seat| sums[seat] / count as f64).collect(), ok)
}

fn main() {
    let stdin = std::io::stdin();
    let mut stdout = std::io::BufWriter::new(std::io::stdout());
    let mut lines = stdin.lock().lines();
    loop {
        let batch: Vec<String> = lines.by_ref().take(4096).map(|l| l.expect("read")).collect();
        if batch.is_empty() {
            break;
        }
        let rows: Vec<Result<Value, String>> = batch
            .par_iter()
            .map(|line| {
                let s = parse(line)?;
                let (expected, ok) = expectation(&s);
                Ok(json!({"id":s.id,"expected":expected,"realized_ok":ok}))
            })
            .collect();
        for row in rows {
            match row {
                Ok(row) => writeln!(stdout, "{row}").expect("write"),
                Err(error) => {
                    eprintln!("nplayer_allin_equity: {error}");
                    std::process::exit(2);
                }
            }
        }
    }
    stdout.flush().expect("flush");
}

#[cfg(test)]
mod tests {
    use super::*;
    use hu20_buckets::parse_card;

    fn cards(text: &str) -> Vec<u8> {
        text.split_whitespace().map(parse_card).collect()
    }

    fn showdown(board: &str) -> Showdown {
        // Aces against kings, all in for 100 each, one 200 pot.
        Showdown {
            id: json!(0),
            button: 0,
            holes: vec![[parse_card("As"), parse_card("Ah")], [parse_card("Ks"), parse_card("Kh")]],
            board: cards(board),
            realized: cards("2c 7d 9h Jc 3s"),
            pots: vec![(200, 0b11)],
            refunds: vec![0, 0],
            contributions: vec![100, 100],
            rewards: vec![100, -100],
        }
    }

    #[test]
    fn river_board_is_the_realized_result() {
        let (expected, ok) = expectation(&showdown("2c 7d 9h Jc 3s"));
        assert!(ok);
        assert_eq!(expected, vec![100.0, -100.0]);
    }

    #[test]
    fn preflop_aces_against_kings_matches_the_exact_split() {
        let (expected, ok) = expectation(&showdown(""));
        assert!(ok);
        // Aces win about 82% here, so their expectation is near +64 of the 100 risked.
        assert!((expected[0] + expected[1]).abs() < 1e-9);
        assert!(expected[0] > 60.0 && expected[0] < 66.0, "{expected:?}");
    }

    #[test]
    fn odd_chip_follows_the_engine_seat_order() {
        let mut s = showdown("2c 3d 4h 5s 9c");
        s.holes = vec![[parse_card("As"), parse_card("Kd")], [parse_card("Ah"), parse_card("Kc")], [parse_card("7s"), parse_card("7h")]];
        s.button = 0;
        s.realized = cards("2c 3d 4h 5s 9c");
        s.pots = vec![(301, 0b111)];
        s.refunds = vec![0, 0, 0];
        s.contributions = vec![100, 100, 101];
        // Both A-K hands make the wheel-to-five straight and split; seat 1 is first after the button.
        s.rewards = vec![50, 51, -101];
        let (expected, ok) = expectation(&s);
        assert!(ok);
        assert_eq!(expected, vec![50.0, 51.0, -101.0]);
    }
}
