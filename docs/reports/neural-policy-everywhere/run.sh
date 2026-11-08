#!/bin/bash
# Controller for docs/neural-policy-everywhere.md on bb128. Stops at the first failure; never retries.
set -euo pipefail
W=/home/dberweger/neural-policy-everywhere-20261108
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
G=$W/guarded.sh
K50=/home/dberweger/cygnus-qualification-20261014/tables
STUDY="$PY -m scripts.neural_policy_everywhere"
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
sha() { sha256sum "$1" | cut -d' ' -f1; }
# Step 3's networks (#469), read only and pinned by its committed networks.json.
FALLBACK=/home/dberweger/neural-policy-fallback-20261108
# The live widemix (#458 run 1).
LIVE=/home/dberweger/openpoker-wide-stacks-20261106/main/run1/widemix
LIVE_BIN=702e10cf228f93ca73ca4c7450607c0371b69a0a6a63db2117efc79fd9922ee9
LIVE_MASS=afd951ffa956a359ff0fd0421fde1bd9ac85c6354684c472f034831c3c74b34c
# six: #431's 100 BB live-order 10B, the live band route, with its audited mass.
SIX=/mnt/data2tb/openpoker-mixed-stacks-20261027/six.bin
SIX_BIN=f894a59f8a92424d735438726d16834901a7dcaf6d560c98b950fb72a143c9ea
SIX_MASS_DIR=/mnt/data2tb/nplayer-live-order-screen-20261026/live-10b-mass
SIX_MASS=806e7b9c92b7fbfd8f6ea2de30535d4dc7a525cc096091c458fe1e6c15000bda
# peer: #434's seed-2026102661001 live-order 10B, Gate D's trained field.
PEER_SRC=/mnt/data2tb/nplayer-live-order-seeds-20261026/s2026102661001
PEER_BIN=ab7f8e166448b51cd54be3c9163936126f2b6cff2925b2fa374e7a1db783488b
PEER_MASS=366507548dfdd5d9fd4aa44386f02ac8838947766c8f9b6378878f3d0872188b
cd $S
mkdir -p $W/qualification

if [ ! -e $W/binaries.sha256 ]; then
  stage build
  (cd native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_paired_arena --example nplayer_allin_equity --example nplayer_serve)
  sha256sum $B/nplayer_paired_arena $B/nplayer_allin_equity $B/nplayer_serve > $W/binaries.sha256
fi

P=$W/qualification
if [ ! -e $P/receipt.json ]; then
  stage qualification
  (cd native/hu20-trainer && HU20_K50_TABLES=$K50 ~/.cargo/bin/cargo test --release --locked --lib \
     && ~/.cargo/bin/cargo test --release --locked --example nplayer_paired_arena -- --test-threads=1) > $P/native-tests.log 2>&1
  $PY -m pytest -q tests/test_neural_policy_everywhere.py tests/test_neural_policy_fallback.py tests/test_openpoker_phantom_depth.py \
    tests/test_openpoker_client.py >> $P/native-tests.log 2>&1
  # Pins.
  [ "$(sha $LIVE/model.bin)" = $LIVE_BIN ]
  [ "$(sha $LIVE/mass/receipt.json)" = $LIVE_MASS ]
  [ "$(sha $SIX)" = $SIX_BIN ]
  [ "$(sha $SIX_MASS_DIR/receipt.json)" = $SIX_MASS ]
  [ -e $W/peer.bin ] || gunzip -c $PEER_SRC/live-10b.bin.gz > $W/peer.bin
  [ "$(sha $W/peer.bin)" = $PEER_BIN ]
  [ "$(sha $PEER_SRC/live-10b-mass/receipt.json)" = $PEER_MASS ]
  cmp $FALLBACK/networks.json docs/reports/neural-policy-fallback/networks.json
  for K in 1 2 3; do
    [ "$(sha $FALLBACK/networks/net$K.npnet)" = "$($PY -c "import json;print(json.load(open('$FALLBACK/networks.json'))['net$K']['sha256'])")" ]
  done
  # Existing play unchanged: #469's smoke manifest reproduces its traces byte for byte.
  mkdir -p $P/repro
  $PY - $FALLBACK/smoke/out/arena-manifest-b0.json $FALLBACK/smoke/out/arena $P/repro > $P/repro-manifest.json <<'PYEOF'
import json, os, sys
m = json.load(open(sys.argv[1]))
for c in m['cases']:
    c['traces'] = [t.replace(sys.argv[2], sys.argv[3]) for t in c['traces']]
    c['summary'] = c['summary'].replace(sys.argv[2], sys.argv[3])
    for t in c['traces']:
        os.makedirs(os.path.dirname(t), exist_ok=True)
print(json.dumps(m))
PYEOF
  $G $B/nplayer_paired_arena batch $P/repro-manifest.json > $P/repro.log
  (cd $P/repro && for f in */*/*.jsonl; do a=$(sha256sum < $f); b=$(zcat $FALLBACK/smoke/out/arena/$f.gz | sha256sum); [ "$a" = "$b" ] || echo "DIFF $f"; echo "$a $f"; done) > $P/repro-compare.txt
  if grep -q DIFF $P/repro-compare.txt; then echo 'reproduction differs' >&2; exit 4; fi
  [ "$(wc -l < $P/repro-compare.txt)" = 76 ]
  rm -rf $P/repro
  # The decision service still plays the arena's fallback.
  $PY -m scripts.openpoker_fallback_parity $FALLBACK/smoke/out/arena/b0/*/*-a1.jsonl.gz \
    --policy widemix $LIVE/model.bin $LIVE_BIN --mass $LIVE/mass $LIVE_MASS \
    --network net1 $FALLBACK/networks/net1.npnet "$(sha $FALLBACK/networks/net1.npnet)" --card-buckets $K50 --out $P/fallback-parity.json
  echo "{\"native_tests\":\"passed\",\"reproduction\":\"passed\",\"service_parity\":\"passed\",\"pins\":\"verified\"}" > $P/receipt.json
  stage qualification-passed
fi

catalog() {  # root -> models.json
  $PY - $LIVE/model.bin $LIVE/mass $SIX $SIX_MASS_DIR $W/peer.bin $PEER_SRC/live-10b-mass > $1/models.json <<'PYEOF'
import hashlib, json, sys
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
pin = lambda b, m: {'path': b, 'sha256': h(b), 'mass': m, 'mass_sha256': h(m + '/receipt.json')}
a = sys.argv[1:]
print(json.dumps({'widemix': pin(a[0], a[1]), 'six': pin(a[2], a[3]), 'peer': pin(a[4], a[5])}, indent=1))
PYEOF
}
evaluate() {  # root seed-run [--smoke]
  local M=$1 R=$2 F=${3:-}
  local O=$M/out BANKS=4; [ $R -gt 1 ] && BANKS=1; [ -n "$F" ] && BANKS=1
  mkdir -p $M
  [ -e $M/models.json ] || catalog $M
  [ -e $O/arena-manifest-b0.json ] || $STUDY manifest --out $O --models $M/models.json --networks $FALLBACK/networks.json --seed-run $R $F
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
[ -e $W/decision.json ] || $STUDY decide --results $W/main/run1/results/results.json $W/main/run2/results/results.json $W/main/run3/results/results.json --out $W/decision.json
stage done
