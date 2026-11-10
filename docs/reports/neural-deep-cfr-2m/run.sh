#!/bin/bash
# Controller for run 2, docs/neural-deep-cfr-2m.md, on bb128: run 1's controller
# (docs/reports/neural-deep-cfr-scratch/run.sh) with the 2M advantage network, the iteration-1 identity
# with run 1, and E3/E4 against run 1's networks. Stops at the first failure and never
# retries. Every stage is skipped when its output exists, so a stopped run resumes where it stopped
# (the reservoirs live in /dev/shm, which survives logout only with linger: checked below).
set -euo pipefail
W=/home/dberweger/neural-deep-cfr-2m-20261110
H=/mnt/data2tb/neural-deep-cfr-2m-20261110   # reservoir snapshots
R=/dev/shm/neural-deep-cfr-2m                 # live reservoirs
RUN1=/home/dberweger/neural-deep-cfr-scratch-20261109   # run 1, read only
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
TORCH=/home/dberweger/gpu-check-20261107/venv/bin/python
G=$W/guarded.sh
K50=/home/dberweger/cygnus-qualification-20261014/tables
DCFR="$TORCH -m scripts.neural_deep_cfr"
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
sha() { sha256sum "$1" | cut -d' ' -f1; }
json() { $PY -c "import json,sys;print(json.load(open(sys.argv[1]))$2)" "$1"; }
# Pinned inputs: step 2's net1 (the monitoring and E1 baseline) and the warm pilot's iteration-300
# strategy network (E2), copied from PR476's run.
NET1=/home/dberweger/neural-policy-fallback-20261108/networks/net1.npnet
NET1_SHA=5e276263f7bbd3700a2ce652cbf6d1558072fb839628c7ea9b67ba2af442a1b5
WARM_SRC=/home/dberweger/neural-deep-cfr-20261109/models/strategy300-s4000.npnet
WARM_SHA=6da3db391ba6251634ef9f19103702ed82f6abd2eb33458454068bb4ab923c14
EVERYWHERE=/home/dberweger/neural-policy-everywhere-20261108   # step 4's model catalog
LAYOUT=33d180c77adfd1d322afa313949cb5b7bade2469a92b86022458635d650adb8b
# Run 1's final network (E3) and its iteration-1 records (the identity check).
RUN1_FINAL=$RUN1/models/strategy1375-s20000.npnet
RUN1_FINAL_SHA=b3f67d45e6fcb468fbab4a4a3248fbd02c404beacd4d8f948d165dbe3fc4c606
RUN1_IT1_RECORDS=16090fbb4868e7ff43b913ce8e7662a9bd156a7a5569ffe2572f051cc924673c
# The recipe: run 1's (docs/neural-deep-cfr-scratch.md) except the advantage network.
SEED=20261110000001
PLAYERS=3,4,5,6
ADV_HIDDEN=1024,1024,512   # run 1: 512,256,128
STRATEGY_HIDDEN=1024,1024,512
TRAVERSALS=20000
CAPACITY=30000000
ADV_STEPS=1000
MONITOR_STEPS=4000
FINAL_STEPS=20000
WINDOW=86400
MONITOR="25 50 100 200 300 400 800 1200"
SNAPSHOT_EVERY=100   # a reboot loses at most 100 iterations (about 2 hours)
# Exploration bound, fixed from the bound study (docs/neural-deep-cfr-scratch.md).
PER_STREET=3
DEPTH=8
# Deviation (18:14 UTC Nov 10): the guard stopped iteration 65's traversal at CPU 91 C. Traversals
# then use 12 of the 16 threads. Records don't depend on the thread count (qualification checks it).
TRAVERSE_THREADS=12
cd $S
mkdir -p $W/qualification $W/models $W/iterations $W/monitor $H $R
[ "$(loginctl show-user "$USER" -p Linger --value)" = yes ] || { echo "linger is off: /dev/shm would not survive logout" >&2; exit 2; }

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
  grep -q "exploration_bounds_limit_the_tree_and_only_drop_bounded_advantage_samples ... ok" $P/native-tests.log
  grep -q "sampling_past_the_bound_keeps_the_root_value_unbiased ... ok" $P/native-tests.log
  $TORCH -m pytest -q tests/test_neural_deep_cfr.py tests/test_neural_policy_everywhere.py tests/test_neural_policy_fallback.py >> $P/native-tests.log 2>&1
  $TORCH -m scripts.check_gpu > $P/gpu.json
  [ "$(sha $NET1)" = $NET1_SHA ]
  [ "$(sha $WARM_SRC)" = $WARM_SHA ]
  [ "$(sha $RUN1_FINAL)" = $RUN1_FINAL_SHA ]
  cp $WARM_SRC $W/warm300.npnet && [ "$(sha $W/warm300.npnet)" = $WARM_SHA ]
  $B/nplayer_deep_cfr bench --network $NET1 $NET1_SHA --tables $K50 --seconds 30 > $P/bench-net1.json
  # Bounded traversals from the uniform first iterate don't depend on the thread count.
  $DCFR init --hidden $ADV_HIDDEN --layout $LAYOUT --seed 1 --uniform --out $P/uniform > /dev/null
  $DCFR export --model $P/uniform --out $P/uniform.npnet > /dev/null
  for T in 16 7; do
    $B/nplayer_deep_cfr traverse --advantage $P/uniform.npnet $(sha $P/uniform.npnet) --tables $K50 --seed 1 --iteration 1 \
      --traversals 3000 --players $PLAYERS --explore-per-street $PER_STREET --explore-depth $DEPTH --threads $T --out $P/threads$T.npdcf > $P/threads$T.json
  done
  [ "$(json $P/threads16.json "['records_sha256']")" = "$(json $P/threads7.json "['records_sha256']")" ]
  rm -f $P/threads*.npdcf
  echo '{"native_tests":"passed","bound_tests":"passed","python_tests":"passed","gpu":"passed","pins":"verified","thread_determinism":"passed","run1_final":"verified"}' > $P/receipt.json
  stage qualification-passed
fi

iteration() {  # root T traversals capacity buffers
  local D=$1 T=$2 N=$3 C=$4 BUF=$5
  local M=$D/models/adv$T PNET=$D/models/adv$(($2 - 1)).npnet
  [ -e $M.npnet ] && return 0
  local OUT=$D/iterations/it$T.npdcf t0 t1 t2 t3
  t0=$(date +%s.%N)
  # The summary is written beside its final name and renamed when the traversal succeeds, so a stopped
  # traversal leaves no empty it$T.json for a resume to mistake for a finished one.
  [ -s $D/iterations/it$T.json ] || { rm -f $OUT; $G $B/nplayer_deep_cfr traverse --advantage $PNET $(sha $PNET) --tables $K50 \
      --seed $SEED --iteration $T --traversals $N --players $PLAYERS --explore-per-street $PER_STREET --explore-depth $DEPTH \
      --threads $TRAVERSE_THREADS --out $OUT > $D/iterations/it$T.json.tmp && mv $D/iterations/it$T.json.tmp $D/iterations/it$T.json; }
  t1=$(date +%s.%N)
  if [ -e $OUT ]; then
    $G $DCFR add --samples $OUT --advantage-buffer $BUF/advantage --strategy-buffer $BUF/strategy --capacity $C --seed $SEED \
      > $D/iterations/it$T.add.json
    rm -f $OUT
  fi
  t2=$(date +%s.%N)
  rm -rf $M
  $G $DCFR train --kind advantage --buffer $BUF/advantage --init ${PNET%.npnet} --steps $ADV_STEPS --seed $((SEED + T)) --device cuda \
    --out $M > $M.train.json
  $DCFR export --model $M --out $M.npnet > /dev/null
  t3=$(date +%s.%N)
  echo "$T,$t0,$t1,$t2,$t3" >> $D/progress.csv   # iteration, then traverse/add/train boundaries (epoch seconds)
}
strategy() {  # root buffers iteration steps seed: a fresh strategy network
  local M=$1/models/strategy$3-s$4
  [ -e $M.npnet ] && return 0
  rm -rf $M
  $G $DCFR train --kind strategy --buffer $2/strategy --init none --hidden $STRATEGY_HIDDEN --layout $LAYOUT --steps $4 --seed $5 \
    --device cuda --out $M > $M.train.json
  $DCFR export --model $M --out $M.npnet > /dev/null
}
evaluation() {  # dir mode candidate.npnet start.npnet start-sha [--smoke]
  local E=$1 MODE=$2 NET=$3 START=$4 START_SHA=$5 F=${6:-}
  local O=$E/out EVAL="$PY -m scripts.neural_deep_cfr_scratch_eval"
  export DCFR_SCRATCH_EVAL=$MODE
  mkdir -p $E
  [ -e $E/networks.json ] || printf '{"net1":{"path":"%s","sha256":"%s"},"start":{"path":"%s","sha256":"%s"},"dcfr":{"path":"%s","sha256":"%s"}}\n' \
      $NET1 $NET1_SHA $START $START_SHA $NET $(sha $NET) > $E/networks.json
  [ -e $E/models.json ] || cp $EVERYWHERE/main/run1/models.json $E/models.json
  [ -e $O/arena-manifest-b0.json ] || $EVAL manifest --out $O --models $E/models.json --networks $E/networks.json $F
  if [ ! -e $O/bank-b0.done ]; then
    $G $B/nplayer_paired_arena batch $O/arena-manifest-b0.json
    $G $EVAL scan --out $O --workers 12 $F
    $G $EVAL replay --out $O --workers 12 $F
    for f in $O/arena/b0/*/*.jsonl; do gzip -1 $f && gzip -t $f.gz; done
    touch $O/bank-b0.done
  fi
  [ -e $E/results/results.json ] || { $G $EVAL equity --out $O --binary $B/nplayer_allin_equity $F; \
    $EVAL report --out $O --results $E/results $F > /dev/null; }
}
snapshot() {  # iteration: one compressed copy of both reservoirs on the HDD, replacing the last
  local T=$1 NEED FREE
  [ "$(json $H/snapshot.json "['iteration']" 2>/dev/null || echo 0)" = $T ] && return 0
  stage "snapshot-$T"
  # Write the new copy beside the old one, check it, then rename it over. Only if the HDD can't
  # hold both (the last copy's size plus the guard's 20 GB and 5 GB of slack) does the old copy go
  # first; the reservoirs can still be rebuilt by replaying the deterministic traversals.
  NEED=$(( $(stat -c %s $H/snapshot.tar.zst 2>/dev/null || echo 0) / 1073741824 + 25 ))
  FREE=$(df --output=avail -B1G $H | tail -1 | tr -d ' ')
  if [ -e $H/snapshot.tar.zst ] && [ $FREE -lt $NEED ]; then
    rm -f $H/snapshot.tar.zst $H/snapshot.json
    echo "{\"snapshot\":$T,\"replaced_in_place\":true,\"free_gb\":$FREE,\"need_gb\":$NEED}" >> $W/snapshots.jsonl
  fi
  rm -f $H/snapshot.tmp.tar.zst
  tar -C $R -cf - buffers | zstd -T16 -3 -q -o $H/snapshot.tmp.tar.zst
  zstd -t -q $H/snapshot.tmp.tar.zst
  mv -f $H/snapshot.tmp.tar.zst $H/snapshot.tar.zst
  printf '{"iteration":%d,"sha256":"%s","bytes":%d,"at":"%s"}\n' $T $(sha $H/snapshot.tar.zst) $(stat -c %s $H/snapshot.tar.zst) \
    "$(date -u +%FT%TZ)" > $H/snapshot.json
  cat $H/snapshot.json >> $W/snapshots.jsonl
}

# Smoke: the loop's plumbing at toy size from the uniform network, then a smoke evaluation.
K=$W/smoke
if [ ! -e $K/eval/results/results.json ]; then
  stage smoke
  mkdir -p $K/models $K/iterations
  [ -e $K/models/adv0.npnet ] || { $DCFR init --hidden $ADV_HIDDEN --layout $LAYOUT --seed $SEED --uniform --out $K/models/adv0 > /dev/null; \
    $DCFR export --model $K/models/adv0 --out $K/models/adv0.npnet > /dev/null; }
  for T in 1 2 3; do ADV_STEPS=50 iteration $K $T 500 200000 $K/buffers; done
  strategy $K $K/buffers 3 200 $SEED
  evaluation $K/eval monitor-3 $K/models/strategy3-s200.npnet $NET1 $NET1_SHA --smoke
  stage smoke-passed
fi

# The run's first iterate: uniform play.
[ -e $W/models/adv0.npnet ] || { $DCFR init --hidden $ADV_HIDDEN --layout $LAYOUT --seed $SEED --uniform --out $W/models/adv0 > /dev/null; \
  $DCFR export --model $W/models/adv0 --out $W/models/adv0.npnet > /dev/null; }


# The 24-hour training window.
ln -sfn $R/buffers $W/buffers
[ -e $W/window.json ] || echo "{\"start\":$(date +%s),\"seconds\":$WINDOW}" > $W/window.json
# Stops and pauses (deviations.jsonl) are added back, so the run gets 24 hours of training time.
END=$(( $(json $W/window.json "['start']") + WINDOW + $(json $W/window.json ".get('paused_seconds', 0)") ))
stage deep-cfr
T=1
while [ -e $W/models/adv$T.npnet ]; do T=$((T + 1)); done
while [ "$(date +%s)" -lt $END ]; do
  iteration $W $T $TRAVERSALS $CAPACITY $R/buffers
  # The uniform first iterate doesn't depend on the network's shape: iteration 1 must be run 1's.
  if [ $T = 1 ] && [ "$(json $W/iterations/it1.json "['records_sha256']")" != $RUN1_IT1_RECORDS ]; then
    echo "iteration 1 differs from run 1's" >&2; stage iteration-1-differs; exit 3
  fi
  if [[ " $MONITOR " == *" $T "* ]] && [ ! -e $W/monitor/it$T/results/results.json ]; then
    stage "monitor-$T"
    strategy $W $R/buffers $T $MONITOR_STEPS $((SEED + 100000 + T))
    evaluation $W/monitor/it$T monitor-$T $W/models/strategy$T-s$MONITOR_STEPS.npnet $NET1 $NET1_SHA
  fi
  [ $((T % SNAPSHOT_EVERY)) -eq 0 ] && snapshot $T
  T=$((T + 1))
done
# The last iteration completed inside the window is final, whatever its scores.
FINAL=$((T - 1))
[ -e $W/final.json ] || echo "{\"iteration\":$FINAL,\"window_end\":$END}" > $W/final.json
FINAL=$(json $W/final.json "['iteration']")
stage "final-$FINAL"
strategy $W $R/buffers $FINAL $FINAL_STEPS $((SEED + 200000 + FINAL))
snapshot $FINAL
NET=$W/models/strategy$FINAL-s$FINAL_STEPS.npnet
stage e1
evaluation $W/e1 e1 $NET $NET1 $NET1_SHA
stage e2
evaluation $W/e2 e2 $NET $W/warm300.npnet $WARM_SHA
# E3, equal time: run 2's final against run 1's final.
stage e3
evaluation $W/e3 e3 $NET $RUN1_FINAL $RUN1_FINAL_SHA
# E4, equal iterations: run 2's last checkpoint reached against run 1's at the same iteration.
LAST=0
for N in $MONITOR; do [ $N -le $FINAL ] && LAST=$N; done
[ $LAST -gt 0 ]
[ -e $W/e4.json ] || printf '{"iteration":%d,"run1":"%s","run1_sha256":"%s"}\n' $LAST $RUN1/models/strategy$LAST-s$MONITOR_STEPS.npnet \
    $(sha $RUN1/models/strategy$LAST-s$MONITOR_STEPS.npnet) > $W/e4.json
stage "e4-$LAST"
evaluation $W/e4 e4 $W/models/strategy$LAST-s$MONITOR_STEPS.npnet $(json $W/e4.json "['run1']") $(json $W/e4.json "['run1_sha256']")
stage done
