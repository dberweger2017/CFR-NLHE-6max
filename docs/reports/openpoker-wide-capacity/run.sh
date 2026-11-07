#!/bin/bash
# Controller for docs/openpoker-wide-capacity.md. Stops at the first failure; never retries.
set -euo pipefail
W=/home/dberweger/openpoker-wide-capacity-20261107
H=/mnt/data2tb/openpoker-wide-capacity-20261107
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
G=$W/guarded.sh
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
# #458's recipe with the table cap raised from 250M to 400M entries.
RECIPE="--small-blind 50 --big-blind 100 --fast --roots-per-seat 8 --max-entries 400000000 --freeze-at-cap --last-average-street 3 --fast-gzip --max-seconds 1e100 --card-buckets /home/dberweger/cygnus-qualification-20261014/tables --key-schema live-order --stack-law wide-depth-grid-v1"
# Comparison model: the live widemix (#458 run 1). Read only, pinned.
LIVE=/home/dberweger/openpoker-wide-stacks-20261106/main/run1/widemix
LIVE_BIN=702e10cf228f93ca73ca4c7450607c0371b69a0a6a63db2117efc79fd9922ee9
LIVE_MASS=afd951ffa956a359ff0fd0421fde1bd9ac85c6354684c472f034831c3c74b34c
SEED=2026110791000
sha() { sha256sum "$1" | cut -d' ' -f1; }
mkdir -p $H

if [ ! -e $W/binaries.sha256 ]; then
  stage build
  (cd $S/native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_train --example nplayer_policy --example nplayer_inference --example nplayer_paired_arena --example nplayer_allin_equity)
  sha256sum $B/nplayer_train $B/nplayer_policy $B/nplayer_inference $B/nplayer_paired_arena $B/nplayer_allin_equity > $W/binaries.sha256
fi

P=$W/qualification; mkdir -p $P
if [ ! -e $P/receipt.json ]; then
  stage qualification
  (cd $S/native/hu20-trainer && ~/.cargo/bin/cargo test --release --locked --lib && ~/.cargo/bin/cargo test --release --locked --example nplayer_paired_arena -- --test-threads=1) > $P/native-tests.log 2>&1
  [ "$(sha $LIVE/model.bin)" = $LIVE_BIN ]
  [ "$(sha $LIVE/mass/receipt.json)" = $LIVE_MASS ]
  # Same code as #458: the wide grid at 100M nodes still reproduces #458's qualification checkpoint
  # under #458's 250M cap, and the 400M cap is deterministic across thread counts.
  [ -e $P/widemix-100m.gz ] || $G $B/nplayer_train ${RECIPE/--max-entries 400000000/--max-entries 250000000} --seed 20261106710001 --players 6 --nodes 100000000 --threads 16 --out $P/widemix-100m.gz > $P/widemix-100m.json
  [ "$(sha $P/widemix-100m.gz)" = ca8f357b0e27c7d4accada2479b49497c3072de05a922232825be013ce637b1f ]
  [ -e $P/widecap-100m-t16.gz ] || $G $B/nplayer_train $RECIPE --seed ${SEED}1 --players 6 --nodes 100000000 --threads 16 --out $P/widecap-100m-t16.gz > $P/widecap-100m-t16.json
  [ -e $P/widecap-100m-t8.gz ] || $G $B/nplayer_train $RECIPE --seed ${SEED}1 --players 6 --nodes 100000000 --threads 8 --out $P/widecap-100m-t8.gz > $P/widecap-100m-t8.json
  [ "$(sha $P/widecap-100m-t16.gz)" = "$(sha $P/widecap-100m-t8.gz)" ]
  echo "{\"widemix_100m\":\"ca8f357b\",\"widecap_100m_threads_16_eq_8\":\"$(sha $P/widecap-100m-t16.gz)\",\"native_tests\":\"passed\",\"inputs\":\"verified\"}" > $P/receipt.json
  stage qualification-passed
fi

model() {  # directory seed-run nodes [checkpoint to reuse]
  local D=$1 R=$2 N=$3 REUSE=${4:-}
  mkdir -p $D
  [ -e $D/pins.json ] && return
  [ -n "$REUSE" ] && [ ! -e $D/train.gz ] && cp $REUSE $D/train.gz
  [ -e $D/train.gz ] || $G $B/nplayer_train $RECIPE --seed ${SEED}$R --players 6 --nodes $N --threads 16 --out $D/train.gz --telemetry $D/train.progress.jsonl > $D/train.json
  local CK=$(sha $D/train.gz)
  $G $B/nplayer_policy export $D/train.gz $CK average $D/average.gz --fast-gzip
  local AV=$(sha $D/average.gz)
  (cd $S && $G $PY -m scripts.audit_nplayer_policy_parallel $D/train.gz $D/average.gz --workers 8 --lookup-out $D/mass)
  local RC=$(sha $D/mass/receipt.json)
  $G $B/nplayer_inference convert $D/average.gz $AV $D/model.bin --mass $D/mass/receipt.json $RC
  local BN=$(sha $D/model.bin)
  $G $B/nplayer_inference verify $D/average.gz $AV $D/model.bin $BN --mass $D/mass/receipt.json $RC
  echo "{\"alias\":\"widecap\",\"players\":6,\"stacks\":\"wide-depth-grid-v1\",\"max_entries\":400000000,\"seed\":${SEED}$R,\"nodes\":$N,\"checkpoint\":\"$CK\",\"average\":\"$AV\",\"mass_receipt\":\"$RC\",\"binary\":\"$BN\"}" > $D/pins.json
  # The NVMe holds three runs only without the checkpoints; they move to the HDD, pinned above.
  local T=$H/$(basename $(dirname $D))-$(basename $D); mkdir -p $T
  cp $D/train.gz $T/train.gz && [ "$(sha $T/train.gz)" = $CK ] && rm $D/train.gz
}
catalog() {  # root, then alias=binary=mass triples -> models.json
  local R=$1; shift
  $PY - "$@" > $R/models.json <<'PYEOF'
import hashlib, json, sys
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
out = {}
for spec in sys.argv[1:]:
    alias, path, mass = spec.split('=')
    out[alias] = {'path': path, 'sha256': h(path), 'mass': mass, 'mass_sha256': h(mass + '/receipt.json')}
print(json.dumps(out, indent=1))
PYEOF
}
evaluate() {  # root seed-run [--smoke]
  local M=$1 R=$2 F=${3:-}
  local O=$M/out BANKS=4; [ $R -gt 1 ] && BANKS=1; [ -n "$F" ] && BANKS=1
  local STUDY="$PY -m scripts.openpoker_wide_capacity"
  cd $S
  [ -e $O/arena-manifest-b0.json ] || $STUDY manifest --out $O --models $M/models.json --seed-run $R $F
  for ((BANK=0; BANK<BANKS; BANK++)); do
    if [ ! -e $O/bank-b$BANK.done ]; then
      stage "arena-$(basename $M)-b$BANK"
      $G $B/nplayer_paired_arena batch $O/arena-manifest-b$BANK.json
      $G $STUDY scan --out $O --workers 12 --seed-run $R $F
      if [ $BANK -eq 0 ]; then $G $STUDY replay --out $O --workers 12 --seed-run $R $F; fi
      for f in $O/arena/b$BANK/*/*.jsonl; do gzip -1 $f && gzip -t $f.gz; done
      touch $O/bank-b$BANK.done
    fi
  done
  stage "equity-$(basename $M)"
  $G $STUDY equity --out $O --binary $B/nplayer_allin_equity --seed-run $R $F
  [ -e $M/results/results.json ] || $STUDY report --out $O --results $M/results --seed-run $R $F
}
compare() {  # root: the live widemix plus that run's widecap
  local M=$1
  [ -e $M/models.json ] || catalog $M widemix=$LIVE/model.bin=$LIVE/mass widecap=$M/widecap/model.bin=$M/widecap/mass
}

# Smoke: a 100M widecap against the live widemix; never enters the results.
K=$W/smoke
if [ ! -e $K/results/results.json ]; then
  stage smoke-models
  model $K/widecap 1 100000000 $P/widecap-100m-t16.gz
  compare $K
  evaluate $K 1 --smoke
  stage smoke-passed
fi

# Run 1 decides; runs 2 and 3 replicate on fresh seeds.
for R in 1 2 3; do
  M=$W/main/run$R
  [ -e $M/widecap/pins.json ] || { stage train-widecap-run$R; model $M/widecap $R 10000000000; }
  compare $M
  evaluate $M $R
done
stage done
