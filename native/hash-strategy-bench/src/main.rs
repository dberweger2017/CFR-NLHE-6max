//! Whole-file integrity strategies for pinned policy binaries, timed on one file.
//! Every strategy reads the file the same way inside its timed region.
//! Usage: hash-strategy-bench FILE ROUNDS  (build with --features sha2-asm for sha2's asm backend)
use rayon::prelude::*;
use sha2::Digest;
use std::{fs::File, io::Read, time::Instant};

const BUFFER: usize = 8 << 20;
/// Leaf size of the parallel tree strategies.
const LEAF: usize = 64 << 20;

fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}
/// Stream the file in fixed buffers through `f`.
fn stream(path: &str, mut f: impl FnMut(&[u8])) -> u64 {
    let mut file = File::open(path).unwrap();
    let mut b = vec![0; BUFFER];
    let mut total = 0;
    loop {
        let n = file.read(&mut b).unwrap();
        if n == 0 {
            return total;
        }
        f(&b[..n]);
        total += n as u64;
    }
}
/// Read the file in batches of whole leaves, so parallel strategies have work for every thread.
fn leaves(path: &str, mut f: impl FnMut(&[Vec<u8>])) -> u64 {
    let mut file = File::open(path).unwrap();
    let width = rayon::current_num_threads();
    let mut total = 0;
    loop {
        let mut batch = Vec::with_capacity(width);
        for _ in 0..width {
            let mut leaf = Vec::with_capacity(LEAF);
            (&mut file).take(LEAF as u64).read_to_end(&mut leaf).unwrap();
            if leaf.is_empty() {
                break;
            }
            total += leaf.len() as u64;
            batch.push(leaf);
        }
        if batch.is_empty() {
            return total;
        }
        f(&batch);
    }
}
/// SHA-256 over (leaf count, then every leaf's SHA-256 in order), leaves hashed in parallel.
fn tree_sha256(path: &str) -> (u64, String) {
    let mut digests = Vec::new();
    let n = leaves(path, |batch| {
        let d: Vec<[u8; 32]> = batch.par_iter().map(|l| sha2::Sha256::digest(l).into()).collect();
        digests.extend(d);
    });
    let mut root = sha2::Sha256::new();
    root.update((digests.len() as u64).to_le_bytes());
    for d in &digests {
        root.update(d);
    }
    (n, hex(&root.finalize()))
}
fn run(name: &str, path: &str) -> (u64, String) {
    match name {
        "read-only" => (stream(path, |b| { std::hint::black_box(b); }), String::new()),
        "sha256-sha2" | "sha256-sha2-asm" => {
            let mut h = sha2::Sha256::new();
            (stream(path, |b| h.update(b)), hex(&h.finalize()))
        }
        "sha256-ring" => {
            let mut h = ring::digest::Context::new(&ring::digest::SHA256);
            (stream(path, |b| h.update(b)), hex(h.finish().as_ref()))
        }
        "sha512-256-sha2" => {
            let mut h = sha2::Sha512_256::new();
            (stream(path, |b| h.update(b)), hex(&h.finalize()))
        }
        "sha256-tree-parallel" => tree_sha256(path),
        "blake2b-512" => {
            let mut h = blake2::Blake2b512::new();
            (stream(path, |b| h.update(b)), hex(&h.finalize()))
        }
        "blake3-1-thread" => {
            let mut h = blake3::Hasher::new();
            (stream(path, |b| { h.update(b); }), h.finalize().to_hex().to_string())
        }
        "blake3-parallel" => {
            let mut h = blake3::Hasher::new();
            let n = leaves(path, |batch| {
                for l in batch {
                    h.update_rayon(l);
                }
            });
            (n, h.finalize().to_hex().to_string())
        }
        "xxh3-128-noncrypto" => {
            let mut h = xxhash_rust::xxh3::Xxh3Default::new();
            (stream(path, |b| h.update(b)), format!("{:032x}", h.digest128()))
        }
        _ => unreachable!(),
    }
}
fn main() {
    let a: Vec<String> = std::env::args().collect();
    let (path, rounds): (&str, usize) = (&a[1], a[2].parse().unwrap());
    let sha2 = if cfg!(feature = "sha2-asm") { "sha256-sha2-asm" } else { "sha256-sha2" };
    let names = [
        "read-only", sha2, "sha256-ring", "sha512-256-sha2", "sha256-tree-parallel",
        "blake2b-512", "blake3-1-thread", "blake3-parallel", "xxh3-128-noncrypto",
    ];
    // Warm the page cache so every strategy sees the same storage state.
    run("read-only", path);
    for round in 1..=rounds {
        for name in names {
            let t = Instant::now();
            let (bytes, digest) = run(name, path);
            let s = t.elapsed().as_secs_f64();
            println!(
                "{{\"round\":{round},\"strategy\":\"{name}\",\"bytes\":{bytes},\"seconds\":{s:.4},\"mb_per_s\":{:.1},\"threads\":{},\"digest\":\"{digest}\"}}",
                bytes as f64 / s / 1e6,
                rayon::current_num_threads()
            );
        }
    }
}
