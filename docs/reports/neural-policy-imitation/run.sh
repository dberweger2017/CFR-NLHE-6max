#!/bin/bash
# Controller for docs/neural-policy-imitation.md on bb128. Stops at the first failure; never retries.
set -euo pipefail
W=/home/dberweger/neural-policy-imitation-20261108
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/gpu-check-20261107/venv/bin/python
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
# Samples memory, CPU and GPU temperature every 5 s; stops below 4 GB available memory, 10 GB of
# free NVMe, a CPU of 90 C or a GPU of 87 C.
sampled() {
  local LOG=$1; shift
  "$@" & local JOB=$!
  echo "at,rss_gb,available_gb,cpu_c,gpu_c,gpu_mem_mb,nvme_free_gb" > $LOG.csv
  while kill -0 $JOB 2>/dev/null; do
    local RSS=$(awk '/VmRSS/{printf "%.1f", $2/1048576}' /proc/$JOB/status 2>/dev/null || echo 0)
    local AV=$(free -g | awk '/Mem/{print $7}')
    local CPU=$(sensors 2>/dev/null | awk '/Package id 0/{gsub(/[+°C]/,"",$4);print int($4)}')
    local G=$(nvidia-smi --query-gpu=temperature.gpu,memory.used --format=csv,noheader,nounits 2>/dev/null | tr -d ' ')
    local NV=$(df --output=avail -B1G /home | tail -1 | tr -d ' ')
    echo "$(date -u +%FT%TZ),$RSS,$AV,${CPU:-0},${G:-0,0},$NV" >> $LOG.csv
    local GT=${G%%,*}
    if [ "${AV:-99}" -lt 4 ] || [ "${CPU:-0}" -ge 90 ] || [ "${GT:-0}" -ge 87 ] || [ "${NV:-99}" -lt 10 ]; then
      echo "stop: available $AV GB, CPU $CPU C, GPU $GT C, NVMe $NV GB" >&2; kill $JOB; wait $JOB; return 5; fi
    sleep 5
  done
  wait $JOB
}
if [ ! -e $W/tests.done ]; then
  stage build
  (cd $S/native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_features)
  sha256sum $B/nplayer_features > $W/binaries.sha256
  stage tests
  (cd $S/native/hu20-trainer && HU20_K50_TABLES=/home/dberweger/cygnus-qualification-20261014/tables ~/.cargo/bin/cargo test --release --locked --lib) > $W/tests.log 2>&1
  (cd $S && $PY -m pytest -q tests/test_neural_policy_samples.py tests/test_neural_policy_imitation.py) >> $W/tests.log 2>&1
  $PY -c "import torch; assert torch.cuda.is_available(), 'CUDA unavailable'"
  touch $W/tests.done
fi
cd $S
if [ ! -e $W/data/export.done ]; then
  stage export
  $PY docs/reports/neural-policy-imitation/make_manifest.py $W > $W/hands.json
  sampled $W/data/export $B/nplayer_features $W/data/manifest.json > $W/data/export.log 2> $W/data/export.err
  touch $W/data/export.done
fi
for SEED in 1 2 3; do
  M=$W/models/seed$SEED
  if [ ! -e $M/model.json ]; then
    stage train-seed$SEED
    sampled $W/models/train-seed$SEED $PY -m scripts.neural_policy_imitation train --data $W/data/train/*.npfeat --seed $SEED --out $M > $W/models/train-seed$SEED.log
  fi
  if [ ! -e $W/results/seed$SEED.json ]; then
    stage evaluate-seed$SEED
    mkdir -p $W/results
    $PY -m scripts.neural_policy_imitation evaluate --model $M --data $W/data/test-wide/*.npfeat $W/data/test-short/*.npfeat --out $W/results/seed$SEED.json
  fi
done
$PY -m scripts.neural_policy_imitation decide --results $W/results/seed1.json $W/results/seed2.json $W/results/seed3.json > $W/results/decision.json
stage done
