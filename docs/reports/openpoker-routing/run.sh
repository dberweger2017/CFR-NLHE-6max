#!/bin/bash
# Controller for docs/openpoker-routing.md. Stops at the first failure; never retries.
set -euo pipefail
W=/mnt/data2tb/openpoker-routing-20261027
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
G=$W/guarded.sh
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
PD=/mnt/data2tb/openpoker-phantom-depth-20261027   # read only
MS=/mnt/data2tb/openpoker-mixed-stacks-20261027    # read only
SIX_BIN=$MS/six.bin
SIX_MASS=/mnt/data2tb/nplayer-live-order-screen-20261026/live-10b-mass
declare -A BIN=([six]=f894a59f8a92424d735438726d16834901a7dcaf6d560c98b950fb72a143c9ea
  [mix]=64c693c4a3a56f69fcdd050b5da9dde0cfee76e108676b4816dbab98dccfbb20
  [p3]=1a607613a29d2c4d62e16ce31df5214f160796391730b2fbc55495fd286fc894
  [p4]=66ec2f87d3fbfb3100c92325939c0fa43e34c4168e66ffad6cfa73a44c8688ba
  [p5]=bdc5ab50bb4765f86ebd7e044beb95db09a86bb1cff170eaf800f8781851ec26)
declare -A MASS=([six]=806e7b9c92b7fbfd8f6ea2de30535d4dc7a525cc096091c458fe1e6c15000bda
  [mix]=c390909ac19365e9f840ab54368796ea31dbe08e24af9baf39a287af1c387fbd
  [p3]=269ede08cd223680238d7e37a850f268ffdc027770be2b96932bd7673c47fe7f
  [p4]=43364dc91d7c5a064ac1365dd347006267d6c4e8420f1f75829ed55d3eb19d8c
  [p5]=01fbe8b92d9d2d22aa05baea1e0d9255050fe6b1c2ac1bac1c48abdefcb4bf33)
sha() { sha256sum "$1" | cut -d' ' -f1; }

if [ ! -e $W/binaries.sha256 ]; then
  stage build
  (cd $S/native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_paired_arena --example nplayer_allin_equity)
  sha256sum $B/nplayer_paired_arena $B/nplayer_allin_equity > $W/binaries.sha256
fi

# Pinned main models: (binary, mass directory) per alias.
declare -A PATHS=([six]=$SIX_BIN [mix]=$W/models/mix.bin [p3]=$W/models/p3.bin [p4]=$W/models/p4.bin [p5]=$W/models/p5.bin)
declare -A MASSES=([six]=$SIX_MASS [mix]=$MS/main/mix/mass [p3]=$PD/main/p3/mass [p4]=$PD/main/p4/mass [p5]=$PD/main/p5/mass)
P=$W/qualification; mkdir -p $P $W/models
if [ ! -e $P/receipt.json ]; then
  stage qualification
  (cd $S/native/hu20-trainer && ~/.cargo/bin/cargo test --release --locked --example nplayer_paired_arena -- --test-threads=1) > $P/native-tests.log 2>&1
  [ -e $W/models/mix.bin ] || gunzip -c $MS/main/mix/model.bin.gz > $W/models/mix.bin
  for n in 3 4 5; do [ -e $W/models/p$n.bin ] || gunzip -c $PD/main/p$n/model.bin.gz > $W/models/p$n.bin; done
  for a in six mix p3 p4 p5; do
    [ "$(sha ${PATHS[$a]})" = ${BIN[$a]} ]
    [ "$(sha ${MASSES[$a]}/receipt.json)" = ${MASS[$a]} ]
  done
  echo '{"native_tests":"passed","inputs":"verified"}' > $P/receipt.json
  stage qualification-passed
fi

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
  [ -e $O/arena-manifest-b0.json ] || $PY -m scripts.openpoker_routing manifest --out $O --models $(dirname $O)/models.json $F
  for ((BANK=0; BANK<BANKS; BANK++)); do
    if [ ! -e $O/bank-b$BANK.done ]; then
      stage "arena-$(basename $(dirname $O))-b$BANK"
      $G $B/nplayer_paired_arena batch $O/arena-manifest-b$BANK.json
      $G $PY -m scripts.openpoker_routing scan --out $O --workers 12 $F
      if [ $BANK -eq 0 ]; then $G $PY -m scripts.openpoker_routing replay --out $O --workers 12 $F; fi
      for f in $O/arena/b$BANK/*/*.jsonl; do gzip -1 $f && gzip -t $f.gz; done
      touch $O/bank-b$BANK.done
    fi
  done
  stage "equity-$(basename $(dirname $O))"
  $G $PY -m scripts.openpoker_routing equity --out $O --binary $B/nplayer_allin_equity $F
  [ -e $R/results.json ] || $PY -m scripts.openpoker_routing report --out $O --results $R $F
}

# Smoke: the earlier studies' 100M smoke models, one 64-block bank; never enters the results.
K=$W/smoke; mkdir -p $K
if [ ! -e $K/results/results.json ]; then
  stage smoke
  [ -e $K/models.json ] || catalog $K six=$PD/smoke/six/model.bin=$PD/smoke/six/mass mix=$MS/smoke/mix/model.bin=$MS/smoke/mix/mass \
    p3=$PD/smoke/p3/model.bin=$PD/smoke/p3/mass p4=$PD/smoke/p4/model.bin=$PD/smoke/p4/mass p5=$PD/smoke/p5/model.bin=$PD/smoke/p5/mass
  evaluate $K/out $K/results --smoke
  stage smoke-passed
fi

M=$W/main; mkdir -p $M
[ -e $M/models.json ] || catalog $M $(for a in six mix p3 p4 p5; do echo "$a=${PATHS[$a]}=${MASSES[$a]}"; done)
evaluate $M/out $M/results
stage done
