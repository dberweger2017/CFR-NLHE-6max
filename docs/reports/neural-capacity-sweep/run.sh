#!/bin/bash
# The advantage-network capacity sweep (docs/neural-capacity-sweep.md).
#
#   run.sh prepare   on bb128: a 5M-row subsample of the pilot's advantage reservoir (after
#                    iteration 122), at the lowest CPU and IO priority so a running job is unaffected
#   run.sh sweep     on the M4 (base M4 MacBook Pro, 16 GB): every architecture, one after another,
#                    on the Apple GPU, then the report
#   run.sh rows      on the M4, after sweep: rows or noise? mlp-2m on 0.5M and 1.5M rows, cards-15m on
#                    1.5M rows, mlp-2m with a Huber loss; reported with sweep's 4.5M-row fits
set -euo pipefail
SEED=20261109700001
ROWS=${ROWS:-5000000}
STEPS=${STEPS:-10000}
ARCHS=${ARCHS:-"mlp-0.5m mlp-2m mlp-13m res-15m cards-15m"}
case "${1:-}" in
  prepare)
    W=/home/dberweger/neural-capacity-sweep-20261109
    SRC=/mnt/data2tb/neural-deep-cfr-20261109/buffers-hdd-after-it122/advantage
    PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
    mkdir -p $W && cd "$(dirname "$0")/../../.."
    [ -e $W/data/subsample.json ] || nice -n 19 ionice -c3 $PY -m scripts.neural_capacity_sweep subsample \
      --buffer $SRC --rows $ROWS --holdout 0.1 --seed $SEED --out $W/data
    cat $W/data/subsample.json ;;
  sweep)
    W=${W:-$HOME/neural-capacity-sweep-20261109}
    PY=${PY:-$W/venv/bin/python}
    cd "$(dirname "$0")/../../.."
    PYBASE=${PYBASE:-python3}   # Python 3.11 or newer (hashlib.file_digest); on the M4, Homebrew python3.12
    [ -x $PY ] || { $PYBASE -m venv $W/venv && $W/venv/bin/pip install -q torch numpy; }
    $PY -c "import torch; assert torch.backends.mps.is_available(), 'no MPS'"
    mkdir -p $W/runs
    for A in $ARCHS; do
      [ -e $W/runs/$A/result.json ] && continue
      rm -rf $W/runs/$A
      # caffeinate keeps the laptop awake while plugged in; logs per architecture.
      caffeinate -is $PY -m scripts.neural_capacity_sweep run --data $W/data --arch $A --steps $STEPS --seed $SEED \
        --device mps --out $W/runs/$A > $W/runs/$A.log 2>&1
    done
    $PY -m scripts.neural_capacity_sweep report --runs $(for A in $ARCHS; do echo $W/runs/$A; done) --out $W/report.json ;;
  rows)
    W=${W:-$HOME/neural-capacity-sweep-20261109}
    PY=${PY:-$W/venv/bin/python}
    cd "$(dirname "$0")/../../.."
    $PY -c "import torch; assert torch.backends.mps.is_available(), 'no MPS'"
    mkdir -p $W/runs-rows
    # name arch rows loss (rows 0: every training row)
    RUNS="mlp-2m-r0.5m mlp-2m 500000 mse
mlp-2m-r1.5m mlp-2m 1500000 mse
mlp-2m-huber20 mlp-2m 0 huber
cards-15m-r1.5m cards-15m 1500000 mse"
    while read -r N A R L; do
      [ -e $W/runs-rows/$N/result.json ] && continue
      rm -rf $W/runs-rows/$N
      caffeinate -is $PY -m scripts.neural_capacity_sweep run --data $W/data --arch $A --steps $STEPS --seed $SEED \
        --device mps --rows $R --loss $L --huber-delta 20 --out $W/runs-rows/$N > $W/runs-rows/$N.log 2>&1
    done <<< "$RUNS"
    $PY -m scripts.neural_capacity_sweep report --out $W/report-rows.json --runs $W/runs/mlp-2m $W/runs/cards-15m \
      $(echo "$RUNS" | while read -r N _; do echo $W/runs-rows/$N; done) ;;
  *) echo "usage: run.sh prepare|sweep|rows" >&2; exit 2 ;;
esac
