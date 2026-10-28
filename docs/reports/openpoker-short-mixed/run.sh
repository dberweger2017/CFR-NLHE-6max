#!/bin/bash
# Controller for docs/openpoker-short-mixed.md. Stops at the first failure; never retries.
set -euo pipefail
W=/home/dberweger/openpoker-short-mixed-20261028
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
G=$W/guarded.sh
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
RECIPE="--small-blind 50 --big-blind 100 --fast --roots-per-seat 8 --seed 2026102361001 --max-entries 250000000 --freeze-at-cap --last-average-street 3 --fast-gzip --max-seconds 1e100 --card-buckets /home/dberweger/cygnus-qualification-20261014/tables --key-schema live-order"
LAW="--stack-law live-depth-grid-v1"
PD=/mnt/data2tb/openpoker-phantom-depth-20261027   # read only
MS=/mnt/data2tb/openpoker-mixed-stacks-20261027    # read only
RM=/mnt/data2tb/openpoker-routing-20261027/models   # read only, pinned
declare -A BIN=([mix]=64c693c4a3a56f69fcdd050b5da9dde0cfee76e108676b4816dbab98dccfbb20
  [p3]=1a607613a29d2c4d62e16ce31df5214f160796391730b2fbc55495fd286fc894
  [p4]=66ec2f87d3fbfb3100c92325939c0fa43e34c4168e66ffad6cfa73a44c8688ba
  [p5]=bdc5ab50bb4765f86ebd7e044beb95db09a86bb1cff170eaf800f8781851ec26)
declare -A MASS=([mix]=c390909ac19365e9f840ab54368796ea31dbe08e24af9baf39a287af1c387fbd
  [p3]=269ede08cd223680238d7e37a850f268ffdc027770be2b96932bd7673c47fe7f
  [p4]=43364dc91d7c5a064ac1365dd347006267d6c4e8420f1f75829ed55d3eb19d8c
  [p5]=01fbe8b92d9d2d22aa05baea1e0d9255050fe6b1c2ac1bac1c48abdefcb4bf33)
declare -A PATHS=([mix]=$RM/mix.bin [p3]=$RM/p3.bin [p4]=$RM/p4.bin [p5]=$RM/p5.bin)
declare -A MASSES=([mix]=$MS/main/mix/mass [p3]=$PD/main/p3/mass [p4]=$PD/main/p4/mass [p5]=$PD/main/p5/mass)
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
  for a in mix p3 p4 p5; do
    [ "$(sha ${PATHS[$a]})" = ${BIN[$a]} ]
    [ "$(sha ${MASSES[$a]}/receipt.json)" = ${MASS[$a]} ]
  done
  [ -e $P/six-100m.gz ] || $G $B/nplayer_train $RECIPE --players 6 --stack-bb 100 --nodes 100000000 --threads 16 --out $P/six-100m.gz
  [ "$(sha $P/six-100m.gz)" = 482a0f8f54d0cdf9fd881d5250243fd7261499cc129bf15388c08beee8f4d84d ]
  [ -e $P/p5mix-100m-t16.gz ] || $G $B/nplayer_train $RECIPE $LAW --players 5 --nodes 100000000 --threads 16 --out $P/p5mix-100m-t16.gz > $P/p5mix-100m-t16.json
  [ -e $P/p5mix-100m-t8.gz ] || $G $B/nplayer_train $RECIPE $LAW --players 5 --nodes 100000000 --threads 8 --out $P/p5mix-100m-t8.gz > $P/p5mix-100m-t8.json
  [ "$(sha $P/p5mix-100m-t16.gz)" = "$(sha $P/p5mix-100m-t8.gz)" ]
  for n in 3 4; do
    [ -e $P/p${n}mix-100m.gz ] || $G $B/nplayer_train $RECIPE $LAW --players $n --nodes 100000000 --threads 16 --out $P/p${n}mix-100m.gz > $P/p${n}mix-100m.json
  done
  echo "{\"live_order_100m\":\"482a0f8f\",\"p5mix_100m_threads_16_eq_8\":\"$(sha $P/p5mix-100m-t16.gz)\",\"native_tests\":\"passed\",\"inputs\":\"verified\"}" > $P/receipt.json
  stage qualification-passed
fi

model() {  # directory players nodes
  local D=$1 PL=$2 N=$3
  mkdir -p $D
  [ -e $D/pins.json ] && return
  [ -e $D/train.gz ] || $G $B/nplayer_train $RECIPE $LAW --players $PL --nodes $N --threads 16 --out $D/train.gz --telemetry $D/train.progress.jsonl > $D/train.json
  local CK=$(sha $D/train.gz)
  $G $B/nplayer_policy export $D/train.gz $CK average $D/average.gz --fast-gzip
  local AV=$(sha $D/average.gz)
  (cd $S && $G $PY -m scripts.audit_nplayer_policy_parallel $D/train.gz $D/average.gz --workers 8 --lookup-out $D/mass)
  local RC=$(sha $D/mass/receipt.json)
  $G $B/nplayer_inference convert $D/average.gz $AV $D/model.bin --mass $D/mass/receipt.json $RC
  local BN=$(sha $D/model.bin)
  $G $B/nplayer_inference verify $D/average.gz $AV $D/model.bin $BN --mass $D/mass/receipt.json $RC
  echo "{\"players\":$PL,\"stacks\":\"live-depth-grid-v1\",\"nodes\":$N,\"checkpoint\":\"$CK\",\"average\":\"$AV\",\"mass_receipt\":\"$RC\",\"binary\":\"$BN\"}" > $D/pins.json
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
evaluate() {  # out results [--smoke]
  local O=$1 R=$2 F=${3:-}
  local BANKS=4; [ -n "$F" ] && BANKS=1
  cd $S
  [ -e $O/arena-manifest-b0.json ] || $PY -m scripts.openpoker_short_mixed manifest --out $O --models $(dirname $O)/models.json $F
  for ((BANK=0; BANK<BANKS; BANK++)); do
    if [ ! -e $O/bank-b$BANK.done ]; then
      stage "arena-$(basename $(dirname $O))-b$BANK"
      $G $B/nplayer_paired_arena batch $O/arena-manifest-b$BANK.json
      $G $PY -m scripts.openpoker_short_mixed scan --out $O --workers 12 $F
      if [ $BANK -eq 0 ]; then $G $PY -m scripts.openpoker_short_mixed replay --out $O --workers 12 $F; fi
      for f in $O/arena/b$BANK/*/*.jsonl; do gzip -1 $f && gzip -t $f.gz; done
      touch $O/bank-b$BANK.done
    fi
  done
  stage "equity-$(basename $(dirname $O))"
  $G $PY -m scripts.openpoker_short_mixed equity --out $O --binary $B/nplayer_allin_equity $F
  [ -e $R/results.json ] || $PY -m scripts.openpoker_short_mixed report --out $O --results $R $F
}

# Smoke: 100M versions of the new models with the earlier studies' smoke models; never enters the results.
K=$W/smoke
if [ ! -e $K/results/results.json ]; then
  stage smoke-models
  for n in 3 4 5; do
    mkdir -p $K/p${n}mix
    SRC=$P/p${n}mix-100m.gz; [ $n -eq 5 ] && SRC=$P/p5mix-100m-t16.gz
    [ -e $K/p${n}mix/train.gz ] || cp $SRC $K/p${n}mix/train.gz
    model $K/p${n}mix $n 100000000
  done
  [ -e $K/models.json ] || catalog $K mix=$MS/smoke/mix/model.bin=$MS/smoke/mix/mass \
    $(for n in 3 4 5; do echo "p$n=$PD/smoke/p$n/model.bin=$PD/smoke/p$n/mass p${n}mix=$K/p${n}mix/model.bin=$K/p${n}mix/mass"; done)
  evaluate $K/out $K/results --smoke
  stage smoke-passed
fi

M=$W/main
for n in 3 4 5; do
  [ -e $M/p${n}mix/pins.json ] || { stage train-p${n}mix; model $M/p${n}mix $n 10000000000; }
done
[ -e $M/models.json ] || catalog $M $(for a in mix p3 p4 p5; do echo "$a=${PATHS[$a]}=${MASSES[$a]}"; done) \
  $(for n in 3 4 5; do echo "p${n}mix=$M/p${n}mix/model.bin=$M/p${n}mix/mass"; done)
evaluate $M/out $M/results
stage done
