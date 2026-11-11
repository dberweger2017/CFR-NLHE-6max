#!/bin/bash
# Target-noise study on the M4 (base M4 MacBook Pro, 16 GB): run 1's code plus the probe, run 1's
# K50 tables and networks. Each run probes the traverser's first decision on one street, for 40,000
# deals, 32 times each with independent samples below it. Run 1's bound (3 per street, 8 per path)
# goes first; 2/6 and 2/8 (both in run 1's bound study) show how the bound trades noise for nodes.
set -euo pipefail
W=${W:-$HOME/m4-queue-20261110/a-target-noise}
cd "$(dirname "$0")/../../.."
PY=${PY:-$HOME/neural-capacity-sweep-20261109/venv/bin/python}
K50=${K50:-$HOME/Local/openpoker-client-20261027/models/openpoker-e2e}
NETS=${NETS:-$HOME/deep-cfr-2m-timing-20261110/nets}
SEED=20261111000001
DEALS=${DEALS:-40000}
REPEATS=${REPEATS:-32}
export CARGO_TARGET_DIR=$W/target
mkdir -p $W/runs
(cd native/hu20-trainer && HU20_K50_TABLES=$K50 ~/.cargo/bin/cargo test --release --locked --lib deep_cfr) > $W/tests.log 2>&1
grep -q "probes_repeat_one_decision_with_independent_samples_below ... ok" $W/tests.log
$PY -m pytest -q tests/test_neural_target_noise.py >> $W/tests.log 2>&1
(cd native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_deep_cfr) > $W/build.log 2>&1
B=$W/target/release/examples/nplayer_deep_cfr
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
for BOUND in "3 8" "2 6" "2 8"; do
  set -- $BOUND
  for NET in "late adv1375 1375" "uniform u-512-256-128 1"; do
    read -r NAME FILE IT <<< "$NET"
    for ST in 0 1 2 3; do
      N=$NAME-b$1-$2-s$ST
      [ -e $W/runs/$N.jsonl.gz ] && continue
      rm -f $W/runs/$N.jsonl
      $B noise --advantage $NETS/$FILE.npnet $(sha $NETS/$FILE.npnet) --tables $K50 --seed $SEED --iteration $IT \
        --deals $DEALS --repeats $REPEATS --street $ST --players 3,4,5,6 --explore-per-street $1 --explore-depth $2 \
        --threads 10 --out $W/runs/$N.jsonl > $W/runs/$N.json
      gzip -1 $W/runs/$N.jsonl
    done
  done
done
$PY -m scripts.neural_target_noise summary --runs $W/runs/*.jsonl.gz --out $W/report.json
