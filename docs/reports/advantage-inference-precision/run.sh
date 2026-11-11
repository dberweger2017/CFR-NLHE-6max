#!/bin/bash
# Cheaper weights for traversal inference, on the M4 (base M4 MacBook Pro, 16 GB), single thread.
# Inputs: the first 50,000 held-out rows of the 13M-row advantage subsample (#480), real
# advantage-sample feature vectors with their legal masks.
set -euo pipefail
W=${W:-$HOME/m4-queue-20261110/b-inference-precision}
cd "$(dirname "$0")/../../.."
PY=${PY:-$HOME/neural-capacity-sweep-20261109/venv/bin/python}
D=${D:-$HOME/neural-capacity-sweep-20261109/data-13m}
NETS=${NETS:-$HOME/deep-cfr-2m-timing-20261110/nets}
export CARGO_TARGET_DIR=$W/target
mkdir -p $W/out
(cd native/hu20-trainer && ~/.cargo/bin/cargo test --release --locked --example nplayer_net_precision \
   && ~/.cargo/bin/cargo build --release --locked --example nplayer_net_precision) > $W/build.log 2>&1
[ -e $W/inputs.bin ] || $PY - "$D/holdout" $W/inputs.bin <<'PYEOF'
import sys
import numpy as np
from scripts import neural_capacity_sweep as sweep
rows, _ = sweep.arrays(sys.argv[1])
n = 50000
out = np.concatenate([rows['features'][:n], rows['legal'][:n, None].astype(np.uint8)], axis=1)
assert out.shape == (n, 613) and out.dtype == np.uint8
out.tofile(sys.argv[2])
PYEOF
B=$W/target/release/examples/nplayer_net_precision
for N in adv1375 run2-adv72 net1 strategy800-s4000 u-1024-1024-512; do
  [ -e $W/out/$N.json ] && continue
  F=$NETS/$N.npnet
  $B --network $F $(shasum -a 256 $F | cut -d' ' -f1) --inputs $W/inputs.bin --rows 50000 --seconds 10 > $W/out/$N.json 2> $W/out/$N.err
done
