#!/bin/bash
# Controller for docs/openpoker-phantom-depth.md. Stops at the first failure; never retries.
set -euo pipefail
W=/mnt/data2tb/openpoker-phantom-depth-20261027
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
G=$W/guarded.sh
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
RECIPE="--small-blind 50 --big-blind 100 --fast --roots-per-seat 8 --seed 2026102361001 --max-entries 250000000 --freeze-at-cap --last-average-street 3 --fast-gzip --max-seconds 1e100 --card-buckets /home/dberweger/cygnus-qualification-20261014/tables --key-schema live-order"
SCREEN=/mnt/data2tb/nplayer-live-order-screen-20261026
NODES=/mnt/data2tb/nplayer-live-order-nodes-20261026
SIX_BIN_SHA=f894a59f8a92424d735438726d16834901a7dcaf6d560c98b950fb72a143c9ea
SIX_MASS=$SCREEN/live-10b-mass
SIX_MASS_SHA=806e7b9c92b7fbfd8f6ea2de30535d4dc7a525cc096091c458fe1e6c15000bda
sha() { sha256sum "$1" | cut -d' ' -f1; }

if [ ! -e $W/binaries.sha256 ]; then
  stage build
  (cd $S/native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_train --example nplayer_policy --example nplayer_inference --example nplayer_paired_arena --example nplayer_allin_equity)
  sha256sum $B/nplayer_train $B/nplayer_policy $B/nplayer_inference $B/nplayer_paired_arena $B/nplayer_allin_equity > $W/binaries.sha256
fi

P=$W/qualification; mkdir -p $P
if [ ! -e $P/receipt.json ]; then
  stage qualification
  (cd $S/native/hu20-trainer && ~/.cargo/bin/cargo test --release --locked --lib multi_view && ~/.cargo/bin/cargo test --release --locked --example nplayer_paired_arena) > $P/native-tests.log 2>&1
  [ -e $P/six-100m.gz ] || $G $B/nplayer_train $RECIPE --players 6 --stack-bb 100 --nodes 100000000 --threads 16 --out $P/six-100m.gz
  [ "$(sha $P/six-100m.gz)" = 482a0f8f54d0cdf9fd881d5250243fd7261499cc129bf15388c08beee8f4d84d ]
  [ -e $W/six.bin ] || gunzip -c $NODES/live-10b.bin.gz > $W/six.bin
  [ "$(sha $W/six.bin)" = $SIX_BIN_SHA ]
  [ "$(sha $SIX_MASS/receipt.json)" = $SIX_MASS_SHA ]
  echo "{\"live_order_100m\":\"482a0f8f\",\"native_tests\":\"passed\",\"inputs\":\"verified\"}" > $P/receipt.json
  stage qualification-passed
fi

model() {  # directory players stack_bb nodes
  local D=$1
  mkdir -p $D
  [ -e $D/pins.json ] && return
  [ -e $D/train.gz ] || $G $B/nplayer_train $RECIPE --players $2 --stack-bb $3 --nodes $4 --threads 16 --out $D/train.gz --telemetry $D/train.progress.jsonl
  local CK=$(sha $D/train.gz)
  $G $B/nplayer_policy export $D/train.gz $CK average $D/average.gz --fast-gzip
  local AV=$(sha $D/average.gz)
  (cd $S && $G $PY -m scripts.audit_nplayer_policy_parallel $D/train.gz $D/average.gz --workers 8 --lookup-out $D/mass)
  local RC=$(sha $D/mass/receipt.json)
  $G $B/nplayer_inference convert $D/average.gz $AV $D/model.bin --mass $D/mass/receipt.json $RC
  local BN=$(sha $D/model.bin)
  $G $B/nplayer_inference verify $D/average.gz $AV $D/model.bin $BN --mass $D/mass/receipt.json $RC
  echo "{\"players\":$2,\"stack_bb\":$3,\"nodes\":$4,\"checkpoint\":\"$CK\",\"average\":\"$AV\",\"mass_receipt\":\"$RC\",\"binary\":\"$BN\"}" > $D/pins.json
}
catalog() {  # root six_binary six_mass -> models.json
  local R=$1
  $PY - "$R" "$2" "$3" > $R/models.json <<'PYEOF'
import json, sys
root, six_bin, six_mass = sys.argv[1:]
def pin(path, mass):
    import hashlib
    h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return {'path': path, 'sha256': h(path), 'mass': mass, 'mass_sha256': h(mass + '/receipt.json')}
models = {a: pin(f'{root}/{a}/model.bin', f'{root}/{a}/mass') for a in ('p3', 'p4', 'p5', 'six50')}
models['six'] = pin(six_bin, six_mass)
print(json.dumps(models, indent=1))
PYEOF
}
evaluate() {  # out results [--smoke]
  local O=$1 R=$2 F=${3:-}
  local BANKS=4; [ -n "$F" ] && BANKS=1
  cd $S
  [ -e $O/arena-manifest-b0.json ] || $PY -m scripts.openpoker_phantom_depth manifest --out $O --models $(dirname $O)/models.json $F
  for ((BANK=0; BANK<BANKS; BANK++)); do
    if [ ! -e $O/bank-b$BANK.done ]; then
      stage "arena-$(basename $(dirname $O))-b$BANK"
      $G $B/nplayer_paired_arena batch $O/arena-manifest-b$BANK.json
      $G $PY -m scripts.openpoker_phantom_depth scan --out $O --workers 12 $F
      if [ $BANK -eq 0 ]; then $G $PY -m scripts.openpoker_phantom_depth replay --out $O --workers 12 $F; fi
      for f in $O/arena/b$BANK/*/*.jsonl; do gzip -1 $f && gzip -t $f.gz; done
      touch $O/bank-b$BANK.done
    fi
  done
  stage "equity-$(basename $(dirname $O))"
  $G $PY -m scripts.openpoker_phantom_depth equity --out $O --binary $B/nplayer_allin_equity $F
  [ -e $R/results.json ] || $PY -m scripts.openpoker_phantom_depth report --out $O --results $R $F
}

# Smoke: 100M-node models, one 64-block bank; never enters the results.
K=$W/smoke
if [ ! -e $K/results/results.json ]; then
  stage smoke-models
  model $K/p3 3 100 100000000; model $K/p4 4 100 100000000; model $K/p5 5 100 100000000; model $K/six50 6 50 100000000
  mkdir -p $K/six
  if [ ! -e $K/six/pins.json ]; then
    cp $P/six-100m.gz $K/six/train.gz
    model $K/six 6 100 100000000
  fi
  [ -e $K/models.json ] || { catalog $K $K/six/model.bin $K/six/mass; }
  evaluate $K/out $K/results --smoke
  stage smoke-passed
fi

M=$W/main
for spec in "p3 3 100" "p4 4 100" "p5 5 100" "six50 6 50"; do
  set -- $spec
  [ -e $M/$1/pins.json ] || { stage "train-$1"; model $M/$1 $2 $3 10000000000; }
done
[ -e $M/models.json ] || catalog $M $W/six.bin $SIX_MASS
evaluate $M/out $M/results
for a in p3 p4 p5 six50; do [ -e $M/$a/model.bin ] && gzip -1 $M/$a/model.bin && gzip -t $M/$a/model.bin.gz; done
stage done
