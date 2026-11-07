#!/bin/bash
# Controller for docs/openpoker-short-coverage.md. Stops at the first failure; never retries.
set -euo pipefail
W=/home/dberweger/openpoker-short-coverage-20261108
H=/mnt/data2tb/openpoker-short-coverage-20261108
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
G=$W/guarded.sh
STUDY="$PY -m scripts.openpoker_short_coverage"
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
# #458's recipe; each arm adds its key schema and stack law.
BASE="--small-blind 50 --big-blind 100 --fast --roots-per-seat 8 --max-entries 250000000 --freeze-at-cap --last-average-street 3 --fast-gzip --max-seconds 1e100 --card-buckets /home/dberweger/cygnus-qualification-20261014/tables --players 6"
recipe() {
  case $1 in
    ctrl) echo "$BASE --key-schema live-order --stack-law wide-depth-grid-v1" ;;
    eff) echo "$BASE --key-schema live-order-effective --stack-law wide-depth-grid-v1" ;;
    short) echo "$BASE --key-schema live-order --stack-law short-wide-mixture-v1" ;;
    effshort) echo "$BASE --key-schema live-order-effective --stack-law short-wide-mixture-v1" ;;
    *) echo "unknown arm $1" >&2; exit 2 ;;
  esac
}
# The live widemix (#458 run 1): Stage B's comparison and the six-player copies field. Read only, pinned.
LIVE=/home/dberweger/openpoker-wide-stacks-20261106/main/run1/widemix
LIVE_BIN=702e10cf228f93ca73ca4c7450607c0371b69a0a6a63db2117efc79fd9922ee9
LIVE_MASS=afd951ffa956a359ff0fd0421fde1bd9ac85c6354684c472f034831c3c74b34c
SCREEN_SEED=2026110892000
MAIN_SEED=2026110893000
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
  # Unchanged code: #458's widemix recipe at 100M still writes #458's qualification checkpoint.
  [ -e $P/ctrl-100m.gz ] || $G $B/nplayer_train $(recipe ctrl) --seed 20261106710001 --nodes 100000000 --threads 16 --out $P/ctrl-100m.gz > $P/ctrl-100m.json
  [ "$(sha $P/ctrl-100m.gz)" = ca8f357b0e27c7d4accada2479b49497c3072de05a922232825be013ce637b1f ]
  # Both new paths are deterministic across thread counts.
  [ -e $P/effshort-100m-t16.gz ] || $G $B/nplayer_train $(recipe effshort) --seed ${SCREEN_SEED}4 --nodes 100000000 --threads 16 --out $P/effshort-100m-t16.gz > $P/effshort-100m-t16.json
  [ -e $P/effshort-100m-t8.gz ] || $G $B/nplayer_train $(recipe effshort) --seed ${SCREEN_SEED}4 --nodes 100000000 --threads 8 --out $P/effshort-100m-t8.gz > $P/effshort-100m-t8.json
  [ "$(sha $P/effshort-100m-t16.gz)" = "$(sha $P/effshort-100m-t8.gz)" ]
  rm $P/effshort-100m-t8.gz
  echo "{\"ctrl_100m\":\"ca8f357b\",\"effshort_100m_threads_16_eq_8\":\"$(sha $P/effshort-100m-t16.gz)\",\"native_tests\":\"passed\",\"inputs\":\"verified\"}" > $P/receipt.json
  stage qualification-passed
fi

model() {  # directory arm seed nodes [checkpoint to reuse]
  local D=$1 ARM=$2 SEED=$3 N=$4 REUSE=${5:-}
  mkdir -p $D
  [ -e $D/pins.json ] && return
  [ -n "$REUSE" ] && [ ! -e $D/train.gz ] && cp $REUSE $D/train.gz
  [ -e $D/train.gz ] || $G $B/nplayer_train $(recipe $ARM) --seed $SEED --nodes $N --threads 16 --out $D/train.gz --telemetry $D/train.progress.jsonl > $D/train.json
  local CK=$(sha $D/train.gz)
  $G $B/nplayer_policy export $D/train.gz $CK average $D/average.gz --fast-gzip
  local AV=$(sha $D/average.gz)
  (cd $S && $G $PY -m scripts.audit_nplayer_policy_parallel $D/train.gz $D/average.gz --workers 8 --lookup-out $D/mass)
  local RC=$(sha $D/mass/receipt.json)
  $G $B/nplayer_inference convert $D/average.gz $AV $D/model.bin --mass $D/mass/receipt.json $RC
  local BN=$(sha $D/model.bin)
  $G $B/nplayer_inference verify $D/average.gz $AV $D/model.bin $BN --mass $D/mass/receipt.json $RC
  echo "{\"arm\":\"$ARM\",\"players\":6,\"recipe\":\"$(recipe $ARM)\",\"seed\":$SEED,\"nodes\":$N,\"checkpoint\":\"$CK\",\"average\":\"$AV\",\"mass_receipt\":\"$RC\",\"binary\":\"$BN\"}" > $D/pins.json
  # The NVMe can't hold seven models' checkpoints; they move to the HDD, pinned above.
  local T=$H/$(echo ${D#$W/} | tr / -); mkdir -p $T
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
screen() {  # root candidate [--smoke]: arena, scan and bank-0 replay; coverage only, no equity
  local M=$1 C=$2 F=${3:-} O=$1/out
  cd $S
  [ -e $O/arena-manifest-b0.json ] || $STUDY manifest --out $O --models $M/models.json --stage screen --candidate $C $F
  if [ ! -e $O/bank-b0.done ]; then
    stage "screen-arena-$C$F"
    $G $B/nplayer_paired_arena batch $O/arena-manifest-b0.json
    $G $STUDY scan --out $O --workers 12 --stage screen --candidate $C $F
    $G $STUDY replay --out $O --workers 12 --stage screen --candidate $C $F
    for f in $O/arena/b0/*/*.jsonl; do gzip -1 $f && gzip -t $f.gz; done
    touch $O/bank-b0.done
  fi
}
evaluate() {  # root seed-run [--smoke]: #461's evaluation
  local M=$1 R=$2 F=${3:-}
  local O=$M/out BANKS=4; [ $R -gt 1 ] && BANKS=1; [ -n "$F" ] && BANKS=1
  cd $S
  [ -e $O/arena-manifest-b0.json ] || $STUDY manifest --out $O --models $M/models.json --stage main --seed-run $R $F
  for ((BANK=0; BANK<BANKS; BANK++)); do
    if [ ! -e $O/bank-b$BANK.done ]; then
      stage "arena-$(basename $M)-b$BANK"
      $G $B/nplayer_paired_arena batch $O/arena-manifest-b$BANK.json
      $G $STUDY scan --out $O --workers 12 --stage main --seed-run $R $F
      if [ $BANK -eq 0 ]; then $G $STUDY replay --out $O --workers 12 --stage main --seed-run $R $F; fi
      for f in $O/arena/b$BANK/*/*.jsonl; do gzip -1 $f && gzip -t $f.gz; done
      touch $O/bank-b$BANK.done
    fi
  done
  stage "equity-$(basename $M)"
  $G $STUDY equity --out $O --binary $B/nplayer_allin_equity --stage main --seed-run $R $F
  [ -e $M/results/results.json ] || $STUDY report --out $O --results $M/results --stage main --seed-run $R $F
}

# Smoke: 100M models through both stages' pipelines; never enters the results.
K=$W/smoke
if [ ! -e $K/main/results/results.json ]; then
  stage smoke-models
  model $K/ctrl ctrl 20261106710001 100000000 $P/ctrl-100m.gz
  model $K/eff eff ${SCREEN_SEED}2 100000000
  model $K/short short ${SCREEN_SEED}3 100000000
  mkdir -p $K/screen $K/main
  [ -e $K/screen/models.json ] || catalog $K/screen ctrl=$K/ctrl/model.bin=$K/ctrl/mass eff=$K/eff/model.bin=$K/eff/mass widemix=$LIVE/model.bin=$LIVE/mass
  screen $K/screen eff --smoke
  [ -e $K/main/models.json ] || catalog $K/main widemix=$LIVE/model.bin=$LIVE/mass cand=$K/short/model.bin=$K/short/mass
  evaluate $K/main 1 --smoke
  stage smoke-passed
fi

# Stage A: four 4B models; each candidate against ctrl on shared roots.
A=$W/screen
for ARM in ctrl eff short effshort; do
  case $ARM in ctrl) I=1;; eff) I=2;; short) I=3;; effshort) I=4;; esac
  [ -e $A/models/$ARM/pins.json ] || { stage train-screen-$ARM; model $A/models/$ARM $ARM ${SCREEN_SEED}$I 4000000000; }
  # Averages aren't read after verification; removing them keeps four models on the NVMe.
  rm -f $A/models/$ARM/average.gz
done
for C in eff short effshort; do
  mkdir -p $A/$C
  [ -e $A/$C/models.json ] || catalog $A/$C ctrl=$A/models/ctrl/model.bin=$A/models/ctrl/mass $C=$A/models/$C/model.bin=$A/models/$C/mass widemix=$LIVE/model.bin=$LIVE/mass
  screen $A/$C $C
done
cd $S
[ -e $A/screen.json ] || $STUDY coverage --screens $A --out $A/screen.json
WIN=$($PY -c "import json;print(json.load(open('$A/screen.json'))['advance'] or '')")
stage "screen-decided-${WIN:-none}"
# The screen models are reproducible from their pins; their pins, mass receipts and reports stay.
for ARM in ctrl eff short effshort; do rm -f $A/models/$ARM/model.bin; done
rm -rf $H/screen-models-*
if [ -z "$WIN" ]; then stage done-no-advance; exit 0; fi

# Stage B: the advancing recipe at 10B, three seeds, against the live widemix.
for R in 1 2 3; do
  M=$W/main/run$R
  [ -e $M/cand/pins.json ] || { stage train-cand-run$R; model $M/cand $WIN ${MAIN_SEED}$R 10000000000; }
  [ -e $M/models.json ] || catalog $M widemix=$LIVE/model.bin=$LIVE/mass cand=$M/cand/model.bin=$M/cand/mass
  evaluate $M $R
done
stage done
