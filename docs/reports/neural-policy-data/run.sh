#!/bin/bash
# Measurement run for docs/neural-policy-data.md on bb128. Stops at the first failure.
set -euo pipefail
W=/home/dberweger/neural-policy-data-20261108
S=$W/source
B=$S/native/hu20-trainer/target/release/examples
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
stage() { echo "{\"stage\":\"$1\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl; }
sha() { sha256sum "$1" | cut -d' ' -f1; }
# Runs a command, sampling its resident memory, host available memory and CPU temperature every
# 5 s into $1.csv; stops it below 4 GB available memory or at a CPU package of 90 C.
sampled() {
  local LOG=$1; shift
  "$@" & local JOB=$!
  echo "at,rss_gb,available_gb,cpu_c,nvme_free_gb" > $LOG.csv
  while kill -0 $JOB 2>/dev/null; do
    local RSS=$(awk '/VmRSS/{printf "%.1f", $2/1048576}' /proc/$JOB/status 2>/dev/null || echo 0)
    local AV=$(free -g | awk '/Mem/{print $7}')
    local CPU=$(sensors 2>/dev/null | awk '/Package id 0/{gsub(/[+°C]/,"",$4);print int($4)}')
    echo "$(date -u +%FT%TZ),$RSS,$AV,${CPU:-0},$(df --output=avail -B1G /home | tail -1 | tr -d ' ')" >> $LOG.csv
    if [ "${AV:-99}" -lt 4 ] || [ "${CPU:-0}" -ge 90 ]; then echo "stop: available $AV GB, CPU $CPU C" >&2; kill $JOB; wait $JOB; return 5; fi
    sleep 5
  done
  wait $JOB
}
stage build
(cd $S/native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_features)
sha256sum $B/nplayer_features > $W/binaries.sha256
stage tests
(cd $S/native/hu20-trainer && HU20_K50_TABLES=/home/dberweger/cygnus-qualification-20261014/tables ~/.cargo/bin/cargo test --release --locked --lib) > $W/native-tests.log 2>&1
(cd $S && $PY -m pytest -q tests/test_neural_policy_samples.py) >> $W/native-tests.log 2>&1
cd $S && $PY docs/reports/neural-policy-data/make_manifest.py $W
stage determinism
sampled $W/qualification/t16 $B/nplayer_features $W/qualification/manifest-t16.json > $W/qualification/t16.log 2> $W/qualification/t16.err
sampled $W/qualification/t8 $B/nplayer_features $W/qualification/manifest-t8.json > $W/qualification/t8.log 2> $W/qualification/t8.err
[ "$(sha $W/qualification/determinism-t16.npfeat)" = "$(sha $W/qualification/determinism-t8.npfeat)" ]
stage measure
sampled $W/measure/run $B/nplayer_features $W/measure/manifest.json > $W/measure/run.log 2> $W/measure/run.err
$PY -m scripts.neural_policy_samples $W/measure/*.npfeat > $W/measure/read.jsonl
stage done
