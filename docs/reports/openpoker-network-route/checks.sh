#!/bin/bash
# Build, tests, arena reproduction after the refactor, service-arena fallback parity, then the
# deploy check with the network route set and stacks from 1 BB. Every step logs; nothing retries.
set -u
W=/home/dberweger/openpoker-network-route-20261108
F=/home/dberweger/neural-policy-fallback-20261108
R=/mnt/data2tb/openpoker-routing-20261027/models
H=/mnt/data2tb/openpoker-heads-up-20261027/main
S=/home/dberweger/openpoker-wide-stacks-20261106/main/run1
K=/home/dberweger/cygnus-qualification-20261014/tables
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
WIDEMIX=(widemix $S/widemix/model.bin 702e10cf228f93ca73ca4c7450607c0371b69a0a6a63db2117efc79fd9922ee9)
MASS=($S/widemix/mass afd951ffa956a359ff0fd0421fde1bd9ac85c6354684c472f034831c3c74b34c)
NET=(net1 $F/networks/net1.npnet 5e276263f7bbd3700a2ce652cbf6d1558072fb839628c7ea9b67ba2af442a1b5)
POL=(--policy six /mnt/data2tb/openpoker-mixed-stacks-20261027/six.bin f894a59f8a92424d735438726d16834901a7dcaf6d560c98b950fb72a143c9ea
  --policy mix $R/mix.bin 64c693c4a3a56f69fcdd050b5da9dde0cfee76e108676b4816dbab98dccfbb20
  --policy p3 $R/p3.bin 1a607613a29d2c4d62e16ce31df5214f160796391730b2fbc55495fd286fc894
  --policy p4 $R/p4.bin 66ec2f87d3fbfb3100c92325939c0fa43e34c4168e66ffad6cfa73a44c8688ba
  --policy p5 $R/p5.bin bdc5ab50bb4765f86ebd7e044beb95db09a86bb1cff170eaf800f8781851ec26
  --policy hu100 $H/hu100/model.bin 1722f0d8744487fcc1c049373f3e3b0a08926701bbdcec5e617d08b7b62cae47
  --policy humix $H/humix/model.bin 9d39dda9d9a5c07a1372dd7a876353fbeffc664eb321c891570c0038558493fc
  --policy p3mix /home/dberweger/openpoker-short-mixed-20261028/main/p3mix/model.bin afddb59521bd518aa25ef5c7a499ea09059b102dc289d34d3978d1438a85a16a
  --policy "${WIDEMIX[@]}"
  --policy huwide $S/huwide/model.bin e485d5d7690b2a9e9263f0d93e243db1e45387fb2210a4ab4db25877ee5627d0
  --mass widemix "${MASS[@]}" --network "${NET[@]}" --card-buckets $K)
step() { echo "$1 $2" >> $W/status; [ "$2" = 0 ] || { echo failed > $W/CHECKS-DONE; exit 1; }; }
cd $W/source
(cd native/hu20-trainer && ~/.cargo/bin/cargo build --release --locked --example nplayer_serve --example nplayer_paired_arena \
  && ~/.cargo/bin/cargo test --release --locked --lib policy_network \
  && ~/.cargo/bin/cargo test --release --locked --example nplayer_paired_arena) > $W/build.out 2>&1; step build $?
$PY -m pytest -q tests/test_openpoker_client.py tests/test_neural_policy_fallback.py > $W/tests.out 2>&1; step tests $?
# The refactored arena must reproduce #469's smoke traces byte for byte.
mkdir -p $W/arena
$PY - $F/smoke/out/arena-manifest-b0.json $F/smoke/out/arena $W/arena > $W/arena-manifest.json <<'PYEOF'
import json, os, sys
m = json.load(open(sys.argv[1]))
for c in m['cases']:
    c['traces'] = [t.replace(sys.argv[2], sys.argv[3]) for t in c['traces']]
    c['summary'] = c['summary'].replace(sys.argv[2], sys.argv[3])
    for t in c['traces']:
        os.makedirs(os.path.dirname(t), exist_ok=True)
print(json.dumps(m))
PYEOF
native/hu20-trainer/target/release/examples/nplayer_paired_arena batch $W/arena-manifest.json > $W/arena.out 2>&1; step arena $?
(cd $W/arena && for f in */*/*.jsonl; do a=$(sha256sum < $f); b=$(zcat $F/smoke/out/arena/$f.gz | sha256sum); [ "$a" = "$b" ] || echo "DIFF $f"; echo "$a $f"; done) > $W/arena-compare.txt
grep -q DIFF $W/arena-compare.txt; [ $? = 1 ]; step arena-identical $?
$PY -m scripts.openpoker_fallback_parity $F/smoke/out/arena/b0/*/*-a1.jsonl.gz --policy "${WIDEMIX[@]}" --mass "${MASS[@]}" \
  --network "${NET[@]}" --card-buckets $K --out $W/fallback-parity.json > $W/parity.out 2>&1; step parity $?
nice -n 5 $PY -m scripts.openpoker_deploy_check --routes $W/routes.json "${POL[@]}" --min-bb 1 --out $W/deploy-check.json > $W/deploy.out 2> $W/deploy.err; step deploy $?
echo done > $W/CHECKS-DONE
