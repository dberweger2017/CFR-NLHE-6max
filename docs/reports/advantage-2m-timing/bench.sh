#!/bin/bash
# Advantage-network traversal timing on the M4: 0.5M against 2M on identical trees (uniform iteration 1),
# plus run 1's iteration-1375 network for the late tree. Run 1's code (4a4bf2b), bound 3/8, players 3-6.
set -euo pipefail
R=~/deep-cfr-2m-timing-20261110
PY=~/neural-capacity-sweep-20261109/venv/bin/python
B=$R/target/release/examples/nplayer_deep_cfr
K50=~/Local/openpoker-client-20261027/models/openpoker-e2e
LAYOUT=33d180c77adfd1d322afa313949cb5b7bade2469a92b86022458635d650adb8b
SEED=20261110000001
O=$R/out; N=$R/nets
mkdir -p $O
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
cd $R/source
for h in 512,256,128 1024,1024,512; do
  n=u-${h//,/-}
  [ -e $N/$n.npnet ] || { $PY scripts/neural_deep_cfr.py init --hidden $h --layout $LAYOUT --seed 1 --uniform --out $N/$n > /dev/null
                          $PY scripts/neural_deep_cfr.py export --model $N/$n --out $N/$n.npnet > /dev/null; }
done
U05=$N/u-512-256-128.npnet; U2=$N/u-1024-1024-512.npnet; LATE=$N/adv1375.npnet
trav() {  # name net iteration traversals threads
  local f=$O/$1.npdcf
  rm -f $f
  $B traverse --advantage $2 $(sha $2) --tables $K50 --seed $SEED --iteration $3 --traversals $4 --players 3,4,5,6 \
    --explore-per-street 3 --explore-depth 8 --threads $5 --out $f > $O/$1.json
  rm -f $f
  echo "$1 $(cat $O/$1.json | $PY -c 'import json,sys; d=json.load(sys.stdin); print(d["seconds"], d["nodes"], d["terminals"], d["records_sha256"][:12])')"
}
for rep in 1 2 3; do
  trav u05-t10-r$rep $U05 1 5000 10
  trav u2-t10-r$rep $U2 1 5000 10
  trav late-t10-r$rep $LATE 1375 5000 10
done
for rep in 1 2; do
  trav u05-t1-r$rep $U05 1 500 1
  trav u2-t1-r$rep $U2 1 500 1
  trav late-t1-r$rep $LATE 1375 500 1
done
for net in $U05 $U2 $LATE; do
  b=$(basename $net .npnet)
  $B bench --network $net $(sha $net) --tables $K50 --seconds 20 --threads 10 > $O/bench-$b.json
  echo "bench $b $(head -c 300 $O/bench-$b.json)"
done
echo DONE
