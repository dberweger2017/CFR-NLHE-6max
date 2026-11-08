#!/bin/bash
# Controller for docs/neural-policy-fallback.md on bb128. Stops at the first failure; never retries.
set -euo pipefail
W=/home/dberweger/neural-policy-fallback-20261108
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
TORCH=/home/dberweger/gpu-check-20261107/venv/bin/python
IMITATION=/home/dberweger/neural-policy-imitation-20261108
G=$W/guarded.sh
STUDY="$PY -m scripts.neural_policy_fallback"
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
sha() { sha256sum "$1" | cut -d' ' -f1; }
# The live widemix (#458 run 1), read only and pinned.
LIVE=/home/dberweger/openpoker-wide-stacks-20261106/main/run1/widemix
LIVE_BIN=702e10cf228f93ca73ca4c7450607c0371b69a0a6a63db2117efc79fd9922ee9
LIVE_MASS=afd951ffa956a359ff0fd0421fde1bd9ac85c6354684c472f034831c3c74b34c
cd $S
mkdir -p $W/networks $W/qualification

if [ ! -e $W/binaries.sha256 ]; then
  stage build
  (cd native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_paired_arena --example nplayer_allin_equity --example nplayer_network_parity)
  sha256sum $B/nplayer_paired_arena $B/nplayer_allin_equity $B/nplayer_network_parity > $W/binaries.sha256
fi

P=$W/qualification
if [ ! -e $P/receipt.json ]; then
  stage qualification
  (cd native/hu20-trainer && HU20_K50_TABLES=/home/dberweger/cygnus-qualification-20261014/tables ~/.cargo/bin/cargo test --release --locked --lib \
     && ~/.cargo/bin/cargo test --release --locked --example nplayer_paired_arena -- --test-threads=1) > $P/native-tests.log 2>&1
  $TORCH -m pytest -q tests/test_neural_policy_fallback.py tests/test_neural_policy_imitation.py tests/test_neural_policy_samples.py tests/test_openpoker_phantom_depth.py >> $P/native-tests.log 2>&1
  [ "$(sha $LIVE/model.bin)" = $LIVE_BIN ]
  [ "$(sha $LIVE/mass/receipt.json)" = $LIVE_MASS ]
  # Networks: export step 2's weights, check their pins, and check Rust against PyTorch.
  echo "{" > $W/networks.json
  for K in 1 2 3; do
    M=$IMITATION/models/seed$K
    # Pinned by #467's committed report.
    [ "$($PY -c "import json;print(json.load(open('docs/reports/neural-policy-imitation/results/model-seed$K.json'))['weights_sha256'])")" = "$(sha $M/weights.pt)" ]
    [ -e $W/networks/net$K.npnet ] || $TORCH -m scripts.neural_policy_imitation export --model $M --out $W/networks/net$K.npnet
    [ -e $P/parity-net$K.bin ] || $TORCH -m scripts.neural_policy_imitation parity --model $M --data $IMITATION/data/test-wide/wide-6p-mixed.npfeat --count 10000 --out $P/parity-net$K.bin
    $B/nplayer_network_parity $W/networks/net$K.npnet $(sha $W/networks/net$K.npnet) $P/parity-net$K.bin > $P/parity-net$K.json
    SEP=$([ $K -lt 3 ] && echo , || true)
    echo "\"net$K\":{\"path\":\"$W/networks/net$K.npnet\",\"sha256\":\"$(sha $W/networks/net$K.npnet)\"}$SEP" >> $W/networks.json
  done
  echo "}" >> $W/networks.json
  # Existing play is unchanged: uniform in both arms reproduces two of #461's run 1 cases.
  $PY docs/reports/neural-policy-fallback/repro.py manifest $P/repro
  $G $B/nplayer_paired_arena batch $P/repro/manifest.json > $P/repro/run.log
  $PY docs/reports/neural-policy-fallback/repro.py check $P/repro
  rm -f $P/repro/*.jsonl
  echo "{\"native_tests\":\"passed\",\"parity\":\"passed\",\"reproduction\":\"passed\",\"inputs\":\"verified\"}" > $P/receipt.json
  stage qualification-passed
fi

catalog() {  # root -> models.json with the live widemix
  $PY - $LIVE/model.bin $LIVE/mass > $1/models.json <<'PYEOF'
import hashlib, json, sys
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
print(json.dumps({'widemix': {'path': sys.argv[1], 'sha256': h(sys.argv[1]), 'mass': sys.argv[2], 'mass_sha256': h(sys.argv[2] + '/receipt.json')}}, indent=1))
PYEOF
}
evaluate() {  # root seed-run [--smoke]: #461's evaluation
  local M=$1 R=$2 F=${3:-}
  local O=$M/out BANKS=4; [ $R -gt 1 ] && BANKS=1; [ -n "$F" ] && BANKS=1
  mkdir -p $M
  [ -e $M/models.json ] || catalog $M
  [ -e $O/arena-manifest-b0.json ] || $STUDY manifest --out $O --models $M/models.json --networks $W/networks.json --seed-run $R $F
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

K=$W/smoke
if [ ! -e $K/results/results.json ]; then
  stage smoke
  evaluate $K 1 --smoke
  stage smoke-passed
fi
for R in 1 2 3; do
  evaluate $W/main/run$R $R
done
stage done
