#!/bin/bash
# traverse_bench.sh LABEL BINARY NET THREADS TRAVERSALS [extra args]: one timed traverse, one JSON line.
set -euo pipefail
cd ~/Local/dcfr-speed-bench
L=$1 B=$2 N=$3 T=$4 K=$5; shift 5
SHA=$(grep " $N.npnet" shas.txt | cut -d' ' -f1)
O=/tmp/tb-$$.npdcf; rm -f $O
$B traverse --advantage $N.npnet $SHA --tables tables --seed 20261110000001 --iteration 1375 --traversals $K --players 3,4,5,6 \
  --explore-per-street 3 --explore-depth 8 --threads $T --out $O "$@" > /tmp/tb-$$.json
rm -f $O
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(json.dumps({'label':sys.argv[2],'net':sys.argv[3],'threads':int(sys.argv[4]),'sha':d['records_sha256'][:12],'seconds':round(d['seconds'],2),'nodes':d['nodes'],'decisions':d['nodes']-d['terminals'],'us_per_decision_thread':round(d['seconds']*int(sys.argv[4])/(d['nodes']-d['terminals'])*1e6,2)}))" /tmp/tb-$$.json $L $N $T
rm -f /tmp/tb-$$.json
