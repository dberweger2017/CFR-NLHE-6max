#!/bin/bash
# Thermal stops (CPU 90 C, VRM Thermistor 15 100 C, GPU 87 C) and plumbing stops below 10 GB free on
# the NVMe, 20 GB on the HDD or 4 GB of available memory.
set -u
W=/home/dberweger/neural-deep-cfr-2m-20261110
"$@" &
JOB=$!
trap 'kill $JOB 2>/dev/null' EXIT
while kill -0 $JOB 2>/dev/null; do
  T=$(sensors 2>/dev/null)
  CPU=$(echo "$T" | awk '/Package id 0/{gsub(/[+°C]/,"",$4);print int($4)}')
  VRM=$(echo "$T" | awk '/Thermistor 15/{gsub(/[+°C]/,"",$3);print int($3)}')
  GPU=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 | cut -d. -f1)
  NV=$(df --output=avail -B1G /home | tail -1 | tr -d ' ')
  HD=$(df --output=avail -B1G /mnt/data2tb | tail -1 | tr -d ' ')
  AV=$(free -g | awk '/Mem/{print $7}')
  echo "$(date -u +%FT%TZ),$CPU,$VRM,${GPU:-},$(free -m | awk '/Mem/{print $3}'),$NV,$HD" >> $W/resources.csv
  if [ "${CPU:-0}" -ge 90 ] || [ "${VRM:-0}" -ge 100 ] || [ "${GPU:-0}" -ge 87 ]; then echo "thermal stop CPU=$CPU VRM=$VRM GPU=$GPU" >&2; kill $JOB; wait $JOB; exit 3; fi
  if [ "${NV:-0}" -lt 10 ] || [ "${HD:-0}" -lt 20 ]; then echo "disk stop: NVMe $NV GB, HDD $HD GB (plumbing)" >&2; kill $JOB; wait $JOB; exit 5; fi
  if [ "${AV:-99}" -lt 4 ]; then echo "memory stop: $AV GB available (plumbing)" >&2; kill $JOB; wait $JOB; exit 6; fi
  sleep 5
done
wait $JOB
