#!/bin/bash
# Controller for docs/openpoker-wide-stacks.md. Stops at the first failure; never retries.
set -euo pipefail
W=/home/dberweger/openpoker-wide-stacks-20261106
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
G=$W/guarded.sh
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
RECIPE="--small-blind 50 --big-blind 100 --fast --roots-per-seat 8 --max-entries 250000000 --freeze-at-cap --last-average-street 3 --fast-gzip --max-seconds 1e100 --card-buckets /home/dberweger/cygnus-qualification-20261014/tables --key-schema live-order"
LIVE="--stack-law live-depth-grid-v1"
LAW="--stack-law wide-depth-grid-v1"
# Comparison models: the live routes the wide models would replace. Read only, pinned.
HU=/mnt/data2tb/openpoker-heads-up-20261027/main/humix
P3=/home/dberweger/openpoker-short-mixed-20261028/main/p3mix
RM=/mnt/data2tb/openpoker-routing-20261027/models
MS=/mnt/data2tb/openpoker-mixed-stacks-20261027
declare -A BIN=([humix]=9d39dda9d9a5c07a1372dd7a876353fbeffc664eb321c891570c0038558493fc
  [p3mix]=afddb59521bd518aa25ef5c7a499ea09059b102dc289d34d3978d1438a85a16a
  [mix]=64c693c4a3a56f69fcdd050b5da9dde0cfee76e108676b4816dbab98dccfbb20)
declare -A MASS=([humix]=3775739b0dd867ee01d4d21ba10d1834e7b405448dbe81dec1dad2e81d8ba234
  [p3mix]=6306e3979d85ff446c079f8137d50aeb789e31afd4253ea088022599ddb6d99c
  [mix]=c390909ac19365e9f840ab54368796ea31dbe08e24af9baf39a287af1c387fbd)
declare -A PATHS=([humix]=$HU/model.bin [p3mix]=$P3/model.bin [mix]=$RM/mix.bin)
declare -A MASSES=([humix]=$HU/mass [p3mix]=$P3/mass [mix]=$MS/main/mix/mass)
declare -A SEED=([widemix]=2026110671000 [huwide]=2026110681000)
declare -A PLAYERS=([widemix]=6 [huwide]=2)
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
  for a in humix p3mix mix; do
    [ "$(sha ${PATHS[$a]})" = ${BIN[$a]} ]
    [ "$(sha ${MASSES[$a]}/receipt.json)" = ${MASS[$a]} ]
  done
  # The live grid and fixed training are unchanged: both checkpoints match the earlier studies'.
  [ -e $P/six-100m.gz ] || $G $B/nplayer_train $RECIPE --seed 2026102361001 --players 6 --stack-bb 100 --nodes 100000000 --threads 16 --out $P/six-100m.gz
  [ "$(sha $P/six-100m.gz)" = 482a0f8f54d0cdf9fd881d5250243fd7261499cc129bf15388c08beee8f4d84d ]
  [ -e $P/p5mix-100m.gz ] || $G $B/nplayer_train $RECIPE $LIVE --seed 2026102361001 --players 5 --nodes 100000000 --threads 16 --out $P/p5mix-100m.gz > $P/p5mix-100m.json
  [ "$(sha $P/p5mix-100m.gz)" = 0448ff914b1aeabfab4696a8152ab84bebf95f1fd551b75042db5ee563ac01a1 ]
  # The wide grid is deterministic across thread counts.
  [ -e $P/widemix-100m-t16.gz ] || $G $B/nplayer_train $RECIPE $LAW --seed ${SEED[widemix]}1 --players 6 --nodes 100000000 --threads 16 --out $P/widemix-100m-t16.gz > $P/widemix-100m-t16.json
  [ -e $P/widemix-100m-t8.gz ] || $G $B/nplayer_train $RECIPE $LAW --seed ${SEED[widemix]}1 --players 6 --nodes 100000000 --threads 8 --out $P/widemix-100m-t8.gz > $P/widemix-100m-t8.json
  [ "$(sha $P/widemix-100m-t16.gz)" = "$(sha $P/widemix-100m-t8.gz)" ]
  [ -e $P/huwide-100m.gz ] || $G $B/nplayer_train $RECIPE $LAW --seed ${SEED[huwide]}1 --players 2 --nodes 100000000 --threads 16 --out $P/huwide-100m.gz > $P/huwide-100m.json
  echo "{\"live_order_100m\":\"482a0f8f\",\"live_grid_p5mix_100m\":\"0448ff91\",\"widemix_100m_threads_16_eq_8\":\"$(sha $P/widemix-100m-t16.gz)\",\"native_tests\":\"passed\",\"inputs\":\"verified\"}" > $P/receipt.json
  stage qualification-passed
fi

model() {  # directory alias seed-run nodes [checkpoint to reuse]
  local D=$1 A=$2 R=$3 N=$4 REUSE=${5:-}
  mkdir -p $D
  [ -e $D/pins.json ] && return
  [ -n "$REUSE" ] && [ ! -e $D/train.gz ] && cp $REUSE $D/train.gz
  [ -e $D/train.gz ] || $G $B/nplayer_train $RECIPE $LAW --seed ${SEED[$A]}$R --players ${PLAYERS[$A]} --nodes $N --threads 16 --out $D/train.gz --telemetry $D/train.progress.jsonl > $D/train.json
  local CK=$(sha $D/train.gz)
  $G $B/nplayer_policy export $D/train.gz $CK average $D/average.gz --fast-gzip
  local AV=$(sha $D/average.gz)
  (cd $S && $G $PY -m scripts.audit_nplayer_policy_parallel $D/train.gz $D/average.gz --workers 8 --lookup-out $D/mass)
  local RC=$(sha $D/mass/receipt.json)
  $G $B/nplayer_inference convert $D/average.gz $AV $D/model.bin --mass $D/mass/receipt.json $RC
  local BN=$(sha $D/model.bin)
  $G $B/nplayer_inference verify $D/average.gz $AV $D/model.bin $BN --mass $D/mass/receipt.json $RC
  echo "{\"alias\":\"$A\",\"players\":${PLAYERS[$A]},\"stacks\":\"wide-depth-grid-v1\",\"seed\":${SEED[$A]}$R,\"nodes\":$N,\"checkpoint\":\"$CK\",\"average\":\"$AV\",\"mass_receipt\":\"$RC\",\"binary\":\"$BN\"}" > $D/pins.json
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
  local STUDY="$PY -m scripts.openpoker_wide_stacks"
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
compare() {  # root seed-run: the live routes plus that run's wide models
  local M=$1
  [ -e $M/models.json ] || catalog $M $(for a in humix p3mix mix; do echo "$a=${PATHS[$a]}=${MASSES[$a]}"; done) \
    widemix=$M/widemix/model.bin=$M/widemix/mass huwide=$M/huwide/model.bin=$M/huwide/mass
}

# Smoke: 100M wide models against the live routes; never enters the results.
K=$W/smoke
if [ ! -e $K/results/results.json ]; then
  stage smoke-models
  model $K/widemix widemix 1 100000000 $P/widemix-100m-t16.gz
  model $K/huwide huwide 1 100000000 $P/huwide-100m.gz
  compare $K 1
  evaluate $K 1 --smoke
  stage smoke-passed
fi

# Run 1 decides; runs 2 and 3 replicate on fresh seeds.
for R in 1 2 3; do
  M=$W/main/run$R
  for A in widemix huwide; do
    [ -e $M/$A/pins.json ] || { stage train-$A-run$R; model $M/$A $A $R 10000000000; }
  done
  compare $M $R
  evaluate $M $R
done
stage done
