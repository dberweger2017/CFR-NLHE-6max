#!/bin/bash
# Controller for docs/openpoker-heads-up.md. Stops at the first failure; never retries.
set -euo pipefail
W=/mnt/data2tb/openpoker-heads-up-20261027
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
G=$W/guarded.sh
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
RECIPE="--small-blind 50 --big-blind 100 --fast --roots-per-seat 8 --seed 2026102361001 --max-entries 250000000 --freeze-at-cap --last-average-street 3 --fast-gzip --max-seconds 1e100 --card-buckets /home/dberweger/cygnus-qualification-20261014/tables --key-schema live-order"
LAW="--stack-law live-depth-grid-v1"
sha() { sha256sum "$1" | cut -d' ' -f1; }

if [ ! -e $W/binaries.sha256 ]; then
  stage build
  (cd $S/native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_train --example nplayer_policy --example nplayer_inference --example nplayer_paired_arena --example nplayer_allin_equity)
  sha256sum $B/nplayer_train $B/nplayer_policy $B/nplayer_inference $B/nplayer_paired_arena $B/nplayer_allin_equity > $W/binaries.sha256
fi

P=$W/qualification; mkdir -p $P
if [ ! -e $P/receipt.json ]; then
  stage qualification
  (cd $S/native/hu20-trainer && ~/.cargo/bin/cargo test --release --locked --lib && ~/.cargo/bin/cargo test --release --locked --example nplayer_paired_arena -- --test-threads=1) > $P/native-tests.log 2>&1
  [ -e $P/six-100m.gz ] || $G $B/nplayer_train $RECIPE --players 6 --stack-bb 100 --nodes 100000000 --threads 16 --out $P/six-100m.gz
  [ "$(sha $P/six-100m.gz)" = 482a0f8f54d0cdf9fd881d5250243fd7261499cc129bf15388c08beee8f4d84d ]
  [ -e $P/humix-100m-t16.gz ] || $G $B/nplayer_train $RECIPE $LAW --players 2 --nodes 100000000 --threads 16 --out $P/humix-100m-t16.gz > $P/humix-100m-t16.json
  [ -e $P/humix-100m-t8.gz ] || $G $B/nplayer_train $RECIPE $LAW --players 2 --nodes 100000000 --threads 8 --out $P/humix-100m-t8.gz > $P/humix-100m-t8.json
  [ "$(sha $P/humix-100m-t16.gz)" = "$(sha $P/humix-100m-t8.gz)" ]
  [ -e $P/hu100-100m.gz ] || $G $B/nplayer_train $RECIPE --players 2 --stack-bb 100 --nodes 100000000 --threads 16 --out $P/hu100-100m.gz > $P/hu100-100m.json
  echo "{\"live_order_100m\":\"482a0f8f\",\"humix_100m_threads_16_eq_8\":\"$(sha $P/humix-100m-t16.gz)\",\"native_tests\":\"passed\"}" > $P/receipt.json
  stage qualification-passed
fi

model() {  # directory nodes stacks-args...
  local D=$1 N=$2; shift 2
  mkdir -p $D
  [ -e $D/pins.json ] && return
  [ -e $D/train.gz ] || $G $B/nplayer_train $RECIPE "$@" --players 2 --nodes $N --threads 16 --out $D/train.gz --telemetry $D/train.progress.jsonl
  local CK=$(sha $D/train.gz)
  $G $B/nplayer_policy export $D/train.gz $CK average $D/average.gz --fast-gzip
  local AV=$(sha $D/average.gz)
  (cd $S && $G $PY -m scripts.audit_nplayer_policy_parallel $D/train.gz $D/average.gz --workers 8 --lookup-out $D/mass)
  local RC=$(sha $D/mass/receipt.json)
  $G $B/nplayer_inference convert $D/average.gz $AV $D/model.bin --mass $D/mass/receipt.json $RC
  local BN=$(sha $D/model.bin)
  $G $B/nplayer_inference verify $D/average.gz $AV $D/model.bin $BN --mass $D/mass/receipt.json $RC
  echo "{\"players\":2,\"stacks\":\"$*\",\"nodes\":$N,\"checkpoint\":\"$CK\",\"average\":\"$AV\",\"mass_receipt\":\"$RC\",\"binary\":\"$BN\"}" > $D/pins.json
}
catalog() {  # root -> models.json
  $PY - "$1" > $1/models.json <<'PYEOF'
import hashlib, json, sys
root = sys.argv[1]
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
pin = lambda a: {'path': f'{root}/{a}/model.bin', 'sha256': h(f'{root}/{a}/model.bin'), 'mass': f'{root}/{a}/mass',
                 'mass_sha256': h(f'{root}/{a}/mass/receipt.json')}
print(json.dumps({a: pin(a) for a in ('hu100', 'humix')}, indent=1))
PYEOF
}
evaluate() {  # out results [--smoke]
  local O=$1 R=$2 F=${3:-}
  local BANKS=4; [ -n "$F" ] && BANKS=1
  cd $S
  [ -e $O/arena-manifest-b0.json ] || $PY -m scripts.openpoker_heads_up manifest --out $O --models $(dirname $O)/models.json $F
  for ((BANK=0; BANK<BANKS; BANK++)); do
    if [ ! -e $O/bank-b$BANK.done ]; then
      stage "arena-$(basename $(dirname $O))-b$BANK"
      $G $B/nplayer_paired_arena batch $O/arena-manifest-b$BANK.json
      $G $PY -m scripts.openpoker_heads_up scan --out $O --workers 12 $F
      if [ $BANK -eq 0 ]; then $G $PY -m scripts.openpoker_heads_up replay --out $O --workers 12 $F; fi
      for f in $O/arena/b$BANK/*/*.jsonl; do gzip -1 $f && gzip -t $f.gz; done
      touch $O/bank-b$BANK.done
    fi
  done
  stage "equity-$(basename $(dirname $O))"
  $G $PY -m scripts.openpoker_heads_up equity --out $O --binary $B/nplayer_allin_equity $F
  [ -e $R/results.json ] || $PY -m scripts.openpoker_heads_up report --out $O --results $R $F
}

K=$W/smoke
if [ ! -e $K/results/results.json ]; then
  stage smoke-models
  mkdir -p $K/hu100 $K/humix
  [ -e $K/hu100/train.gz ] || cp $P/hu100-100m.gz $K/hu100/train.gz
  [ -e $K/humix/train.gz ] || cp $P/humix-100m-t16.gz $K/humix/train.gz
  model $K/hu100 100000000 --stack-bb 100
  model $K/humix 100000000 $LAW
  [ -e $K/models.json ] || catalog $K
  evaluate $K/out $K/results --smoke
  stage smoke-passed
fi

M=$W/main
[ -e $M/hu100/pins.json ] || { stage train-hu100; model $M/hu100 10000000000 --stack-bb 100; }
[ -e $M/humix/pins.json ] || { stage train-humix; model $M/humix 10000000000 $LAW; }
[ -e $M/models.json ] || catalog $M
evaluate $M/out $M/results
stage done
