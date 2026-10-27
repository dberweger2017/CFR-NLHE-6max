#!/bin/bash
# Thermal stops (CPU 90 C, VRM Thermistor 15 100 C) and plumbing stops below 10 GB free on the NVMe or 20 GB on the HDD.
set -u
W=/mnt/data2tb/openpoker-routing-20261027
"$@" &
JOB=$!
trap 'kill $JOB 2>/dev/null' EXIT
while kill -0 $JOB 2>/dev/null; do
  T=$(sensors 2>/dev/null)
  CPU=$(echo "$T" | awk '/Package id 0/{gsub(/[+°C]/,"",$4);print int($4)}')
  VRM=$(echo "$T" | awk '/Thermistor 15/{gsub(/[+°C]/,"",$3);print int($3)}')
  NV=$(df --output=avail -B1G /home | tail -1 | tr -d ' ')
  HD=$(df --output=avail -B1G /mnt/data2tb | tail -1 | tr -d ' ')
  echo "$(date -u +%FT%TZ),$CPU,$VRM,$(free -m | awk '/Mem/{print $3}'),$NV,$HD" >> $W/resources.csv
  if [ "${CPU:-0}" -ge 90 ] || [ "${VRM:-0}" -ge 100 ]; then echo "thermal stop CPU=$CPU VRM=$VRM" >&2; kill $JOB; wait $JOB; exit 3; fi
  if [ "${NV:-0}" -lt 10 ] || [ "${HD:-0}" -lt 20 ]; then echo "disk stop: NVMe $NV GB, HDD $HD GB (plumbing)" >&2; kill $JOB; wait $JOB; exit 5; fi
  sleep 5
done
wait $JOB
