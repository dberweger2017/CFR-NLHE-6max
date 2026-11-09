#!/bin/bash
# Controller for docs/neural-deep-cfr.md on bb128 (the step 5 pilot). Stops at the first failure;
# never retries. Every stage is skipped when its output exists, so a stopped run resumes.
set -euo pipefail
W=/home/dberweger/neural-deep-cfr-20261109
H=/mnt/data2tb/neural-deep-cfr-20261109          # reservoirs and the warm export (large)
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
TORCH=/home/dberweger/gpu-check-20261107/venv/bin/python
G=$W/guarded.sh
K50=/home/dberweger/cygnus-qualification-20261014/tables
DCFR="$TORCH -m scripts.neural_deep_cfr"
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
sha() { sha256sum "$1" | cut -d' ' -f1; }
# Pinned inputs: widemix run 1 and its training checkpoint, step 2's seed-1 network and its export.
LIVE=/home/dberweger/openpoker-wide-stacks-20261106/main/run1/widemix
CHECKPOINT=$LIVE/train.gz
CHECKPOINT_SHA=859e0dc1ebbd724d740a80323db8640585d7123d72b478ebf273f17c3758532a
START_MODEL=/home/dberweger/neural-policy-imitation-20261108/models/seed1
START_WEIGHTS=d222a1655db10c4842a47c16b92946fa3b1d4424c76ec2b163d11dbd4dfdd5c3
START_NET=/home/dberweger/neural-policy-fallback-20261108/networks/net1.npnet
START_NET_SHA=5e276263f7bbd3700a2ce652cbf6d1558072fb839628c7ea9b67ba2af442a1b5
LAYOUT=33d180c77adfd1d322afa313949cb5b7bade2469a92b86022458635d650adb8b
# The recipe (docs/neural-deep-cfr.md, "Recipe").
SEED=20261109000001
PLAYERS=3,4,5,6
ADV_HIDDEN=512,256,128
WARM_ITERATIONS=100        # the table stands for iterations 1..100
FIRST=$((WARM_ITERATIONS + 1))
LAST=${LAST:-400}          # 300 Deep CFR iterations
TRAVERSALS=${TRAVERSALS:-20000}
CAPACITY=${CAPACITY:-30000000}
PRETRAIN_STEPS=20000
ADV_STEPS=${ADV_STEPS:-1000}
STRATEGY_EVERY=50
STRATEGY_STEPS=4000
FINAL_STRATEGY_STEPS=20000
cd $S
evaluation() {  # root candidate.npnet [--smoke]: the candidate against its start, step 4's tables
  local R=$1 NET=$2 F=${3:-}
  local O=$R/eval/out BANKS=1
  local EVAL="$PY -m scripts.neural_deep_cfr_eval"
  mkdir -p $R/eval
  if [ ! -e $R/eval/networks.json ]; then
    printf '{"net1":{"path":"%s","sha256":"%s"},"start":{"path":"%s","sha256":"%s"},"dcfr":{"path":"%s","sha256":"%s"}}\n' \
      $START_NET $START_NET_SHA $START_NET $START_NET_SHA $NET $(sha $NET) > $R/eval/networks.json
  fi
  [ -e $R/eval/models.json ] || cp $EVERYWHERE/main/run1/models.json $R/eval/models.json
  [ -e $O/arena-manifest-b0.json ] || $EVAL manifest --out $O --models $R/eval/models.json --networks $R/eval/networks.json $F
  if [ ! -e $O/bank-b0.done ]; then
    stage "eval-arena-$(basename $R)"
    $G $B/nplayer_paired_arena batch $O/arena-manifest-b0.json
    $G $EVAL scan --out $O --workers 12 $F
    $G $EVAL replay --out $O --workers 12 $F
    for f in $O/arena/b0/*/*.jsonl; do gzip -1 $f && gzip -t $f.gz; done
    touch $O/bank-b0.done
  fi
  stage "eval-equity-$(basename $R)"
  $G $EVAL equity --out $O --binary $B/nplayer_allin_equity $F
  [ -e $R/eval/results/results.json ] || $EVAL report --out $O --results $R/eval/results $F
}
EVERYWHERE=/home/dberweger/neural-policy-everywhere-20261108
# Deviation (owner, Nov 9): iteration 310 stopped on the traversal node limit, so the final
# strategy network was never trained and the RAM reservoirs are gone. Evaluate the iteration-300
# checkpoint (4,000 steps) with the planned evaluation instead.
NET=$W/models/strategy300-s4000.npnet
stage deviation-eval-strategy300
evaluation $W $NET
stage eval-strategy300-done
