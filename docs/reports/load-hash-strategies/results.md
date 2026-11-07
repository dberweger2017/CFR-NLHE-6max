# Faster whole-file integrity for pinned policy binaries: M4 study

This is a **test-only study on the M4** (base MacBook Pro, Apple M4, 10 cores, 16 GB). It is not the decision measurement. bb128 (i7-10700KF) is where the large teachers load, and it was busy with other studies at the time, so it still needs the same run. The study follows [#466](https://github.com/dberweger2017/CFR-NLHE-6max/pull/466), which loads policy binaries in one read. With that change a load takes about one SHA-256 pass over the file. The question here is which integrity strategy would make that pass cheaper without weakening it.

## Setup
- **Tool:** [`native/hash-strategy-bench`](../../../native/hash-strategy-bench). It times nine strategies over one file. Every strategy reads the file inside its own timed region, after a warm-up read so they all see the same page-cache state.
- **File:** the 2.19 GB six-player mixed-stack binary (`six.bin`, pin `f894a59f…c9ea`), in the page cache.
- **Runs:** three rounds per strategy, in the default build and with `--features sha2-asm`. Raw output (one record per strategy and round): [`m4-strategies.json`](m4-strategies.json) and [`m4-strategies-sha2-asm.json`](m4-strategies-sha2-asm.json). Real loads: [`m4-loads.json`](m4-loads.json).
- **Correctness:** every SHA-256 variant printed the file's pin exactly.

## Hash strategies (2.19 GB, median of 3 rounds)
| Strategy | Same digest as today's pins? | Default build | `sha2` `asm` build |
|---|---|---|---|
| Read only (I/O floor) | — | 0.13 s (17.1 GB/s) | 0.13 s |
| SHA-256, `sha2` (**today**) | yes | **3.91 s (0.56 GB/s)** | — |
| SHA-256, `sha2` with `asm` | yes | — | **0.88 s (2.49 GB/s)** |
| SHA-256, `ring` | yes | 0.77 s (2.84 GB/s) | 0.77 s |
| SHA-512/256, `sha2` | no | 2.48 s (0.88 GB/s) | 1.28 s (1.71 GB/s) |
| SHA-256 tree, 64 MiB leaves on 10 threads | no (new pin) | 0.86 s (2.55 GB/s) | 0.29 s (7.49 GB/s) |
| BLAKE2b-512 | no | 1.54 s (1.42 GB/s) | 1.54 s |
| BLAKE3, 1 thread | no | 1.04 s (2.10 GB/s) | 1.04 s |
| BLAKE3, 10 threads | no | 0.29 s (7.56 GB/s) | 0.29 s |
| xxh3-128 (not cryptographic) | no | 0.20 s (11.1 GB/s) | 0.20 s |

The SHA-256 tree pin is the SHA-256 of the leaf count followed by every 64 MiB leaf's SHA-256, in order.

## Real loads (2.19 GB, 38.6M rows)
| Loader | Seconds per load | Peak RSS |
|---|---|---|
| `main`: verify, then read | 9.62–9.93 | 2,089 MiB |
| #466: one pass | 4.02–4.07 | 2,114 MiB |
| #466 with `sha2` `asm` | **0.97–0.98** | 2,114 MiB |

## Findings
1. **Today's `sha2` build doesn't use the M4's SHA instructions.** On aarch64, `sha2` 0.10 uses its hardware backend only with the `asm` feature. Turning that feature on in the trainer makes SHA-256 4.5× faster with the identical digest. A real load then drops from 4.0 s to 1.0 s (10× faster than `main`).
   - This needs no pin, receipt or format change. It also speeds up the binary's internal payload and key-set checksums, because those are SHA-256 as well.
   - `ring` is a little faster still (5.1×), but it adds a dependency and a second SHA-256 implementation.
2. **A new pin format (BLAKE3, or a parallel SHA-256 tree) would save much less after finding 1:** on the M4, about 0.6 s per 2.2 GB load.
   - It would only help if the binary format's internal checksums changed too. The whole-file pin, the payload SHA-256 and the key-set SHA-256 each hash about the whole file, and the loader overlaps them, so a load can't drop below the slowest single pass.
   - So a parallel pin also means a new binary format version, and that is the owner's call under the evidence rules.
   - Between the two, a SHA-256 tree matches BLAKE3 in parallel (7.5 GB/s) and stays within the SHA-256 family.
3. **xxh3 isn't an option.** It catches accidental corruption but not a deliberately substituted file, so it can't serve as a pin.
4. **bb128 may rank the strategies differently.** Its CPU has no SHA instructions, so `asm` there means hand-written assembly without hardware support. The gain from finding 1 is likely smaller, and parallel strategies are likely worth more. The same tool should run there before choosing.

## Next
- **Done:** finding 1 is in [#466](https://github.com/dberweger2017/CFR-NLHE-6max/pull/466). It turns on the `sha2` `asm` feature for aarch64 only and adds a test against the published FIPS 180-2 vectors. On the M4, the 2.19 GB load now takes 0.94 s (`main`: 9.6 s). x86-64 builds are unchanged.
- **Open:** run `hash-strategy-bench` on bb128 with one widemix binary (about 5 minutes) once it is free, to decide anything for x86-64.
