#!/bin/bash
# Controller for docs/openpoker-untrained-fallback.md. Stops at the first failure; never retries.
set -euo pipefail
W=/home/dberweger/openpoker-untrained-fallback-20261028
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
G=$W/guarded.sh
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
MS=/mnt/data2tb/openpoker-mixed-stacks-20261027    # read only
MIX_BIN=/mnt/data2tb/openpoker-routing-20261027/models/mix.bin   # read only, pinned
MIX_MASS=$MS/main/mix/mass
BIN_PIN=64c693c4a3a56f69fcdd050b5da9dde0cfee76e108676b4816dbab98dccfbb20
MASS_PIN=c390909ac19365e9f840ab54368796ea31dbe08e24af9baf39a287af1c387fbd
sha() { sha256sum "$1" | cut -d' ' -f1; }

if [ ! -e $W/binaries.sha256 ]; then
  stage build
  (cd $S/native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_paired_arena --example nplayer_allin_equity)
  sha256sum $B/nplayer_paired_arena $B/nplayer_allin_equity > $W/binaries.sha256
fi

P=$W/qualification; mkdir -p $P
if [ ! -e $P/receipt.json ]; then
  stage qualification
  (cd $S/native/hu20-trainer && ~/.cargo/bin/cargo test --release --locked --example nplayer_paired_arena -- --test-threads=1) > $P/native-tests.log 2>&1
  [ "$(sha $MIX_BIN)" = $BIN_PIN ]
  [ "$(sha $MIX_MASS/receipt.json)" = $MASS_PIN ]
  echo '{"native_tests":"passed","inputs":"verified"}' > $P/receipt.json
  stage qualification-passed
fi

catalog() {  # root, then alias=binary=mass -> models.json
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
  [ -e $O/arena-manifest-b0.json ] || $PY -m scripts.openpoker_untrained manifest --out $O --models $(dirname $O)/models.json $F
  for ((BANK=0; BANK<BANKS; BANK++)); do
    if [ ! -e $O/bank-b$BANK.done ]; then
      stage "arena-$(basename $(dirname $O))-b$BANK"
      $G $B/nplayer_paired_arena batch $O/arena-manifest-b$BANK.json
      $G $PY -m scripts.openpoker_untrained scan --out $O --workers 12 $F
      if [ $BANK -eq 0 ]; then $G $PY -m scripts.openpoker_untrained replay --out $O --workers 12 $F; fi
      for f in $O/arena/b$BANK/*/*.jsonl; do gzip -1 $f && gzip -t $f.gz; done
      touch $O/bank-b$BANK.done
    fi
  done
  stage "equity-$(basename $(dirname $O))"
  $G $PY -m scripts.openpoker_untrained equity --out $O --binary $B/nplayer_allin_equity $F
  [ -e $R/results.json ] || $PY -m scripts.openpoker_untrained report --out $O --results $R $F
}

# Smoke: #447's 100M smoke model, one 64-block bank; never enters the results.
K=$W/smoke; mkdir -p $K
if [ ! -e $K/results/results.json ]; then
  stage smoke
  [ -e $K/models.json ] || catalog $K mix=$MS/smoke/mix/model.bin=$MS/smoke/mix/mass
  evaluate $K/out $K/results --smoke
  stage smoke-passed
fi

M=$W/main; mkdir -p $M
[ -e $M/models.json ] || catalog $M mix=$MIX_BIN=$MIX_MASS
evaluate $M/out $M/results
stage done
