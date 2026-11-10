#!/bin/bash
# The advantage-network capacity sweep (docs/neural-capacity-sweep.md).
#
#   run.sh prepare   on bb128: a 5M-row subsample of the pilot's advantage reservoir (after
#                    iteration 122), at the lowest CPU and IO priority so a running job is unaffected
#   run.sh sweep     on the M4 (base M4 MacBook Pro, 16 GB): every architecture, one after another,
#                    on the Apple GPU, then the report
#   run.sh rows      on the M4, after sweep: rows or noise? mlp-2m on 0.5M and 1.5M rows, cards-15m on
#                    1.5M rows, mlp-2m with a Huber loss; reported with sweep's 4.5M-row fits
#   run.sh prepare-more   on bb128: 13.5M rows of the HDD copy (13M train, 0.5M holdout), written
#                    to the HDD at the lowest priority
#   run.sh more      on the M4: do bigger networks pay off with more rows? mlp-2m and mlp-13m on 4.5M
#                    and 13M rows, cards-15m on 13M rows, 20,000 steps each
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
  prepare-more)
    W=/mnt/data2tb/neural-capacity-sweep-20261110
    SRC=/mnt/data2tb/neural-deep-cfr-20261109/buffers-hdd-after-it122/advantage
    PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
    mkdir -p $W && cd "$(dirname "$0")/../../.."
    [ -e $W/data/subsample.json ] || nice -n 19 ionice -c3 $PY -m scripts.neural_capacity_sweep subsample \
      --buffer $SRC --rows 13500000 --holdout 0.037037 --seed 20261110700001 --out $W/data
    cat $W/data/subsample.json ;;
  settings)
    # mlp-2m on all 13M rows, one fit setting changed at a time; the baseline is more's mlp-2m-r13m.
    W=${W:-$HOME/neural-capacity-sweep-20261109}
    PY=${PY:-$W/venv/bin/python}
    D=${D:-$W/data-13m}
    cd "$(dirname "$0")/../../.."
    $PY -c "import torch; assert torch.backends.mps.is_available(), 'no MPS'"
    mkdir -p $W/runs-settings
    RUNS="lr3e-4 20000 8192 3e-4 1e-4
lr3e-3 20000 8192 3e-3 1e-4
wd0 20000 8192 1e-3 0
wd1e-2 20000 8192 1e-3 1e-2
steps60k 60000 8192 1e-3 1e-4
batch32k-5k 5000 32768 1e-3 1e-4
batch32k-20k 20000 32768 1e-3 1e-4"
    while read -r N S B L WD; do
      [ -e $W/runs-settings/$N/result.json ] && continue
      rm -rf $W/runs-settings/$N
      caffeinate -is $PY -m scripts.neural_capacity_sweep run --data $D --arch mlp-2m --steps $S --batch $B --lr $L \
        --weight-decay $WD --seed 20261110700001 --device mps --rows 0 --out $W/runs-settings/$N > $W/runs-settings/$N.log 2>&1
    done <<< "$RUNS"
    $PY -m scripts.neural_capacity_sweep report --out $W/report-settings.json --runs $W/runs-more/mlp-2m-r13m \
      $(echo "$RUNS" | while read -r N _; do echo $W/runs-settings/$N; done) ;;
  more)
    W=${W:-$HOME/neural-capacity-sweep-20261109}
    PY=${PY:-$W/venv/bin/python}
    D=${D:-$W/data-13m}
    cd "$(dirname "$0")/../../.."
    $PY -c "import torch; assert torch.backends.mps.is_available(), 'no MPS'"
    mkdir -p $W/runs-more
    RUNS="mlp-2m-r4.5m mlp-2m 4500000
mlp-2m-r13m mlp-2m 0
mlp-13m-r4.5m mlp-13m 4500000
mlp-13m-r13m mlp-13m 0
cards-15m-r13m cards-15m 0"
    while read -r N A R; do
      [ -e $W/runs-more/$N/result.json ] && continue
      rm -rf $W/runs-more/$N
      caffeinate -is $PY -m scripts.neural_capacity_sweep run --data $D --arch $A --steps 20000 --seed 20261110700001 \
        --device mps --rows $R --out $W/runs-more/$N > $W/runs-more/$N.log 2>&1
    done <<< "$RUNS"
    $PY -m scripts.neural_capacity_sweep report --out $W/report-more.json \
      --runs $(echo "$RUNS" | while read -r N _; do echo $W/runs-more/$N; done) ;;
  *) echo "usage: run.sh prepare|sweep|rows|prepare-more|more" >&2; exit 2 ;;
esac
