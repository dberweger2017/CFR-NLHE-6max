# hash-strategy-bench

Times whole-file integrity strategies for pinned policy binaries (SHA-256 implementations, SHA-512/256, a parallel SHA-256 tree, BLAKE2b, BLAKE3, xxh3) on one file. It's a standalone crate, so the trainer's dependencies are unchanged.

```sh
cargo build --release --locked
./target/release/hash-strategy-bench MODEL.bin 3
cargo build --release --locked --features sha2-asm   # sha2's asm/hardware backend
./target/release/hash-strategy-bench MODEL.bin 3
```

The tool prints one JSON line per strategy and round. Results: [docs/reports/load-hash-strategies](../../docs/reports/load-hash-strategies/results.md).
