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
mkdir -p $W/qualification $W/networks $W/models $W/iterations $H

if [ ! -e $W/binaries.sha256 ]; then
  stage build
  (cd native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_deep_cfr --example nplayer_features \
     --example nplayer_paired_arena --example nplayer_allin_equity)
  sha256sum $B/nplayer_deep_cfr $B/nplayer_features $B/nplayer_paired_arena $B/nplayer_allin_equity > $W/binaries.sha256
fi

P=$W/qualification
if [ ! -e $P/receipt.json ]; then
  stage qualification
  (cd native/hu20-trainer && HU20_K50_TABLES=$K50 ~/.cargo/bin/cargo test --release --locked --lib \
     && ~/.cargo/bin/cargo test --release --locked --example nplayer_paired_arena -- --test-threads=1) > $P/native-tests.log 2>&1
  $TORCH -m pytest -q tests/test_neural_deep_cfr.py tests/test_neural_policy_everywhere.py tests/test_neural_policy_fallback.py >> $P/native-tests.log 2>&1
  $TORCH -m scripts.check_gpu > $P/gpu.json
  [ "$(sha $START_MODEL/weights.pt)" = $START_WEIGHTS ]
  [ "$(sha $START_NET)" = $START_NET_SHA ]
  [ "$(sha $LIVE/model.bin)" = 702e10cf228f93ca73ca4c7450607c0371b69a0a6a63db2117efc79fd9922ee9 ]
  [ "$(sha $CHECKPOINT)" = $CHECKPOINT_SHA ]
  # The f32 path against the f64 reference on real traversal features, and its speed.
  $B/nplayer_deep_cfr bench --network $START_NET $START_NET_SHA --tables $K50 --seconds 30 > $P/bench-start.json
  # Traversals don't depend on the thread count.
  $DCFR init --hidden $ADV_HIDDEN --layout $LAYOUT --seed 1 --out $P/zero > /dev/null
  $DCFR export --model $P/zero --out $P/zero.npnet > /dev/null
  for T in 16 7; do
    $B/nplayer_deep_cfr traverse --advantage $P/zero.npnet $(sha $P/zero.npnet) --tables $K50 --seed 1 --iteration 1 \
      --traversals 5000 --players $PLAYERS --threads $T --out $P/threads$T.npdcf > $P/threads$T.json
  done
  [ "$($PY -c "import json;print(json.load(open('$P/threads16.json'))['records_sha256'])")" = "$($PY -c "import json;print(json.load(open('$P/threads7.json'))['records_sha256'])")" ]
  rm -f $P/threads*.npdcf
  echo '{"native_tests":"passed","python_tests":"passed","gpu":"passed","pins":"verified","f32_parity":"passed","thread_determinism":"passed"}' > $P/receipt.json
  stage qualification-passed
fi

iterate() {  # root first last traversals capacity adv-steps init-advantage-dir
  local R=$1 F=$2 L=$3 N=$4 C=$5 STEPS=$6 PREV=$7
  for ((T=F; T<=L; T++)); do
    local M=$R/models/adv$T
    if [ ! -e $M.npnet ]; then
      local PNET=$PREV.npnet
      [ $T -gt $F ] && PNET=$R/models/adv$((T-1)).npnet
      local PDIR=${PNET%.npnet}
      local OUT=$R/iterations/it$T.npdcf
      [ -e $R/iterations/it$T.json ] || { rm -f $OUT; $G $B/nplayer_deep_cfr traverse --advantage $PNET $(sha $PNET) --tables $K50 \
          --seed $SEED --iteration $T --traversals $N --players $PLAYERS --out $OUT > $R/iterations/it$T.json; }
      if [ -e $OUT ]; then
        $G $DCFR add --samples $OUT --advantage-buffer $R/buffers/advantage --strategy-buffer $R/buffers/strategy --capacity $C --seed $SEED \
          > $R/iterations/it$T.add.json
        rm -f $OUT
      fi
      rm -rf $M
      $G $DCFR train --kind advantage --buffer $R/buffers/advantage --init $PDIR --steps $STEPS --seed $((SEED + T)) --device cuda \
        --out $M > $M.train.json
      $DCFR export --model $M --out $M.npnet > /dev/null
    fi
    if [ $((T % STRATEGY_EVERY)) -eq 0 ] || [ $T -eq $L ]; then
      strategy $R $T $STRATEGY_STEPS
    fi
  done
}
strategy() {  # root iteration steps
  local M=$1/models/strategy$2-s$3
  if [ ! -e $M.npnet ]; then
    rm -rf $M
    $G $DCFR train --kind strategy --buffer $1/buffers/strategy --init $START_MODEL --steps $3 --seed $((SEED + 100000 + $2)) --device cuda \
      --out $M > $M.train.json
    $DCFR export --model $M --out $M.npnet > /dev/null
  fi
}

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
# Step 4's model catalog (widemix, six and the trained-field peer, with mass receipts), pinned there.
EVERYWHERE=/home/dberweger/neural-policy-everywhere-20261108

# Smoke: the loop's plumbing at toy size, from a zero network, with no warm start, then a smoke
# evaluation of its strategy network. Its numbers mean nothing.
K=$W/smoke
if [ ! -e $K/eval/results/results.json ]; then
  stage smoke
  mkdir -p $K/models $K/iterations $K/buffers
  [ -e $K/models/adv0.npnet ] || { $DCFR init --hidden $ADV_HIDDEN --layout $LAYOUT --seed 1 --out $K/models/adv0 > /dev/null; \
    $DCFR export --model $K/models/adv0 --out $K/models/adv0.npnet > /dev/null; }
  STRATEGY_EVERY=3 iterate $K 1 3 500 200000 50 $K/models/adv0
  evaluation $K $K/models/strategy3-s$STRATEGY_STEPS.npnet --smoke
  stage smoke-passed
fi

# Warm start: widemix run 1's strategy and checkpoint regrets at step 2's kind of samples.
if [ ! -e $H/warm/export.done ]; then
  stage warm-export
  $PY docs/reports/neural-deep-cfr/make_manifest.py $H $CHECKPOINT $CHECKPOINT_SHA $LIVE > $W/warm-hands.json
  $G $B/nplayer_features $H/warm/manifest.json > $W/warm-export.log 2> $W/warm-export.err
  touch $H/warm/export.done
fi
ln -sfn $H/buffers $W/buffers
WARM_FEATURES=$(ls $H/warm/*.npfeat)
WARM_REGRETS=$(ls $H/warm/*.npreg)
# Pretraining: the advantage network fits the table's regrets alone (their common weight is irrelevant).
if [ ! -e $W/models/adv$WARM_ITERATIONS.npnet ]; then
  stage pretrain
  rm -rf $H/pretrain $W/models/adv$WARM_ITERATIONS
  $DCFR warm --features $WARM_FEATURES --regrets $WARM_REGRETS --iterations 1 --per-iteration 1 1 \
    --advantage-buffer $H/pretrain/advantage --strategy-buffer $H/pretrain/strategy --capacity $CAPACITY --seed $SEED > $W/pretrain-warm.json
  $G $DCFR train --kind advantage --buffer $H/pretrain/advantage --init none --hidden $ADV_HIDDEN --layout $LAYOUT \
    --steps $PRETRAIN_STEPS --seed $SEED --device cuda --out $W/models/adv$WARM_ITERATIONS > $W/models/adv$WARM_ITERATIONS.train.json
  $DCFR export --model $W/models/adv$WARM_ITERATIONS --out $W/models/adv$WARM_ITERATIONS.npnet > /dev/null
  rm -rf $H/pretrain
fi
# The first iteration's traversal measures rows per iteration, which sets the warm rows' weight; it is
# then that iteration's own sample file.
if [ ! -e $H/buffers/advantage/state.json ]; then
  stage warm-buffers
  NET=$W/models/adv$WARM_ITERATIONS.npnet
  [ -e $W/iterations/it$FIRST.json ] || $G $B/nplayer_deep_cfr traverse --advantage $NET $(sha $NET) --tables $K50 --seed $SEED \
    --iteration $FIRST --traversals $TRAVERSALS --players $PLAYERS --out $W/iterations/it$FIRST.npdcf > $W/iterations/it$FIRST.json
  PER=$($PY -c "import json;r=json.load(open('$W/iterations/it$FIRST.json'));print(r['advantage_samples'], r['strategy_samples'])")
  $DCFR warm --features $WARM_FEATURES --regrets $WARM_REGRETS --iterations $WARM_ITERATIONS --per-iteration $PER \
    --advantage-buffer $H/buffers/advantage --strategy-buffer $H/buffers/strategy --capacity $CAPACITY --seed $SEED > $W/warm-buffers.json
fi
stage deep-cfr
iterate $W $FIRST $LAST $TRAVERSALS $CAPACITY $ADV_STEPS $W/models/adv$WARM_ITERATIONS
strategy $W $LAST $FINAL_STRATEGY_STEPS
evaluation $W $W/models/strategy$LAST-s$FINAL_STRATEGY_STEPS.npnet
stage done
