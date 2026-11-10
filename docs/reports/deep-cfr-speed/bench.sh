#!/bin/bash
# The bb128 benchmark for docs/reports/deep-cfr-speed/results.md: run 1's code (81bb6d1f) against
# this branch, at run 1's settings, with parity checks. Run it only when bb128 is otherwise idle;
# it uses all 16 threads and the GPU for about 20 minutes. The November 10 run used commit
# 8cd6ebc2's version, which also timed batch widths 8 and 32 (since removed: slower everywhere).
#
#     bench.sh ROOT NEW_COMMIT [NET2M NET2M_SHA]
#
# ROOT is a new scratch folder. NET2M is a trained 2M advantage network (run 2's last one, once it
# exists); without it, run 1's strategy800-s4000 stands in, relabelled as an advantage network.
# Every result is one JSON line in ROOT/results.jsonl. Any parity failure stops the script.
set -euo pipefail
R=$1 NEW_COMMIT=$2
BASE_COMMIT=81bb6d1f
RUN1=/home/dberweger/neural-deep-cfr-scratch-20261109        # read only
K50=/home/dberweger/cygnus-qualification-20261014/tables
TORCH=/home/dberweger/gpu-check-20261107/venv/bin/python
SEED=20261110000001
IT1375_SHA=002fb6195848afa9   # run 1's iteration-1375 records (it1375.json), from adv1374
mkdir "$R"
cd "$R"
log() { echo "$1" | tee -a results.jsonl; }
sha() { sha256sum "$1" | cut -d' ' -f1; }
# bb128 has no /usr/bin/time: seconds of a command into file $1, keeping its exit status.
walltime() { local o=$1 s rc=0; shift; s=$(date +%s.%N); "$@" || rc=$?; echo "$(date +%s.%N) - $s" | bc > $o; return $rc; }

git clone -q --filter=blob:none https://github.com/dberweger2017/CFR-NLHE-6max.git src
for v in base new; do git -C src worktree add -q ../$v $([ $v = base ] && echo $BASE_COMMIT || echo $NEW_COMMIT); done
build() {  # tree target-dir [rustflags]
  (cd $1/native/hu20-trainer && RUSTFLAGS="${3:-}" ~/.cargo/bin/cargo build -q --release --locked --example nplayer_deep_cfr --target-dir $2)
}
build base $R/target-base
build new $R/target-new
build new $R/target-native "-C target-cpu=native"
declare -A BIN=([base]=$R/target-base/release/examples/nplayer_deep_cfr [new]=$R/target-new/release/examples/nplayer_deep_cfr
                [native]=$R/target-native/release/examples/nplayer_deep_cfr)

# Networks: run 1's adv1374 (0.5M) and a trained 2M advantage network.
cp $RUN1/models/adv1374.npnet net05.npnet
if [ $# -ge 4 ]; then cp "$3" net2m.npnet; [ "$(sha net2m.npnet)" = "$4" ]; else
  $TORCH - <<'EOF'
import json
b = open('/home/dberweger/neural-deep-cfr-scratch-20261109/models/strategy800-s4000.npnet', 'rb').read()
n = int.from_bytes(b[8:16], 'little'); h = json.loads(b[16:16 + n]); h['output'] = 'advantage-6'
hb = json.dumps(h, separators=(',', ':')).encode()
open('net2m.npnet', 'wb').write(b[:8] + len(hb).to_bytes(8, 'little') + hb + b[16 + n:])
EOF
fi

traverse() {  # label binary net -> one JSON line; keeps the file as $1.npdcf
  local out=$R/$1.npdcf
  walltime $1.wall ${BIN[$2]} traverse --advantage $3.npnet $(sha $3.npnet) --tables $K50 --seed $SEED --iteration 1375 \
    --traversals 20000 --players 3,4,5,6 --explore-per-street 3 --explore-depth 8 --threads 16 --out $out > $1.json
  log "$($TORCH -c "import json,sys; d=json.load(open(sys.argv[1])); print(json.dumps({'stage':'traverse','label':sys.argv[2],
    'process_seconds':float(open(sys.argv[3]).read()),'loop_seconds':d['seconds'],'records_sha256':d['records_sha256'],'nodes':d['nodes'],
    'decisions':d['nodes']-d['terminals']}))" $1.json $1 $1.wall)"
}
for N in net05 net2m; do
  traverse $N-base base $N
  REF=$($TORCH -c "import json;print(json.load(open('$N-base.json'))['records_sha256'])")
  [ $N = net05 ] && [ "${REF:0:16}" != $IT1375_SHA ] && { echo "base does not reproduce run 1's iteration 1375" >&2; exit 2; }
  for v in new native; do
    traverse $N-$v $v $N
    [ "$($TORCH -c "import json;print(json.load(open('$N-$v.json'))['records_sha256'])")" = "$REF" ] || { echo "$N-$v: records differ" >&2; exit 3; }
    rm -f $N-$v.npdcf
  done
done

# add: full 800k-row reservoirs with run 1's seen counts (its keep rate), then base and new on copies.
mkdir -p buf
PYTHONPATH=$R/new $TORCH - <<EOF
import json
from scripts import neural_deep_cfr as d
d.main(['add', '--samples', 'net05-base.npdcf', '--advantage-buffer', 'buf/advantage', '--strategy-buffer', 'buf/strategy',
        '--capacity', '800000', '--seed', '1'])
for kind, seen in (('advantage', 913639602), ('strategy', 2661917069)):
    p = 'buf/%s/state.json' % kind; s = json.load(open(p)); s['seen'] = seen; s['batches'] = 1374
    open(p, 'w').write(json.dumps(s, indent=1) + '\n')
EOF
for v in base new base new; do
  rm -rf buf-$v; cp -r buf buf-$v
  walltime add.wall env PYTHONPATH=$R/$v $TORCH -m scripts.neural_deep_cfr add --samples net05-base.npdcf \
    --advantage-buffer buf-$v/advantage --strategy-buffer buf-$v/strategy --capacity 800000 --seed $SEED > /dev/null
  log "{\"stage\":\"add\",\"label\":\"$v\",\"seconds\":$(cat add.wall)}"
done
for f in advantage/rows.u1 advantage/weights.f4 advantage/state.json strategy/rows.u1 strategy/weights.f4 strategy/state.json; do
  cmp buf-base/$f buf-new/$f
done
log '{"stage":"add","parity":"identical reservoirs"}'

# train: 1,000 steps on CUDA from run 1's adv1374 model; base twice (is CUDA training repeatable at
# all?), then new with in-process export.
cp -r $RUN1/models/adv1374 init
for v in base base2 new; do
  tree=${v%2}; rm -rf m-$v m-$v.npnet
  s=$(date +%s.%N)
  if [ $tree = base ]; then
    PYTHONPATH=$R/base $TORCH -m scripts.neural_deep_cfr train --kind advantage --buffer buf-new/advantage --init init --steps 1000 \
      --seed $((SEED + 1375)) --device cuda --out m-$v > /dev/null
    PYTHONPATH=$R/base $TORCH -m scripts.neural_deep_cfr export --model m-$v --out m-$v.npnet > /dev/null
  else
    PYTHONPATH=$R/new $TORCH -m scripts.neural_deep_cfr train --kind advantage --buffer buf-new/advantage --init init --steps 1000 \
      --seed $((SEED + 1375)) --device cuda --out m-$v --export m-$v.npnet > /dev/null
  fi
  log "{\"stage\":\"train\",\"label\":\"$v\",\"seconds\":$(echo "$(date +%s.%N) - $s" | bc),\"npnet_sha256\":\"$(sha m-$v.npnet)\"}"
done
[ "$(sha m-base.npnet)" = "$(sha m-base2.npnet)" ] && log '{"stage":"train","cuda_repeatable":true}' || log '{"stage":"train","cuda_repeatable":false}'
[ "$(sha m-base.npnet)" = "$(sha m-new.npnet)" ] && log '{"stage":"train","parity":"identical networks"}' || log '{"stage":"train","parity":"DIFFERENT"}'
rm -f *.npdcf
