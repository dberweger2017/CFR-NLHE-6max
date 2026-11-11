//! Offline correctness receipt for the suit-canonical representation pilot.
use hu20_buckets::{class_key, evaluate};

fn next(state: &mut u64) -> u64 {
    *state = state.wrapping_add(0x9e3779b97f4a7c15);
    let mut z = *state;
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
    z ^ (z >> 31)
}

fn main() {
    let mut state = 20261111860003u64;
    let mut checks = 0;
    println!("{{\"seed\":20261111860003,\"cases\":[");
    for street in 1..=3usize {
        for case in 0..1024 {
            let mut deck: Vec<u8> = (0..52).collect();
            for i in (1..52).rev() {
                let j = (next(&mut state) % (i + 1) as u64) as usize;
                deck.swap(i, j);
            }
            let hole = &deck[..2];
            let board = &deck[2..street + 4];
            let strength = evaluate(&deck[..street + 4]);
            let key = class_key(hole, board);
            for a in 0..4u8 {
                for b in 0..4u8 {
                    for c in 0..4u8 {
                        for d in 0..4u8 {
                            let p = [a, b, c, d];
                            if a == b || a == c || a == d || b == c || b == d || c == d {
                                continue;
                            }
                            let h: Vec<u8> = hole
                                .iter()
                                .map(|&v| (v / 4) * 4 + p[(v % 4) as usize])
                                .collect();
                            let bo: Vec<u8> = board
                                .iter()
                                .map(|&v| (v / 4) * 4 + p[(v % 4) as usize])
                                .collect();
                            assert_eq!(class_key(&h, &bo), key);
                            let cards: Vec<u8> = h.iter().chain(&bo).copied().collect();
                            assert_eq!(evaluate(&cards), strength);
                            checks += 1;
                        }
                    }
                }
            }
            let comma = if street == 3 && case == 1023 { "" } else { "," };
            println!("{{\"hole\":{hole:?},\"board\":{board:?},\"key\":\"{key}\",\"strength\":{strength}}}{comma}");
        }
    }
    println!("],\"checks\":{checks},\"passed\":true}}");
}
