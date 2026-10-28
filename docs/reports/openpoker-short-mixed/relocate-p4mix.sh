#!/bin/bash
# Moves p4mix/train.gz to the HDD once its export, audit and conversion are done (pins.json written).
set -e
D=/home/dberweger/openpoker-short-mixed-20261028/main/p4mix; H=/mnt/data2tb/openpoker-short-mixed-20261028/main/p4mix
while [ ! -e $D/pins.json ]; do sleep 20; done
mkdir -p $H
pin=$(python3 -c "import json; print(json.load(open(\"$D/pins.json\"))[\"checkpoint\"])")
cp --preserve=timestamps $D/train.gz $H/train.gz.part && sync
[ "$(sha256sum $H/train.gz.part | cut -d" " -f1)" = "$pin" ]
mv $H/train.gz.part $H/train.gz && rm $D/train.gz && ln -s $H/train.gz $D/train.gz
echo "moved p4mix train.gz $(date -u +%FT%TZ)"
df -h /home /mnt/data2tb | tail -2
