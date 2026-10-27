#!/usr/bin/env bash
# First live Open Poker session (docs/openpoker-live-pilot.md), on bb128.
# The API key arrives on standard input and is only exported into the bot's environment:
#   security find-generic-password -a "$USER" -s openpoker-api-key -w | ssh bb128 "bash $W/run.sh SESSION HANDS"
set -euo pipefail
W=/mnt/data2tb/openpoker-live-pilot-20261027
R=/mnt/data2tb/openpoker-routing-20261027/models
H=/mnt/data2tb/openpoker-heads-up-20261027/main
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
S=$1 HANDS=$2
IFS= read -r OPENPOKER_API_KEY
export OPENPOKER_API_KEY PYTHONPATH=$W/pydeps
cd $W/source
setsid nohup $PY -m scripts.openpoker_bot --routes $W/routes.json \
  --policy six /mnt/data2tb/openpoker-mixed-stacks-20261027/six.bin f894a59f8a92424d735438726d16834901a7dcaf6d560c98b950fb72a143c9ea \
  --policy mix $R/mix.bin 64c693c4a3a56f69fcdd050b5da9dde0cfee76e108676b4816dbab98dccfbb20 \
  --policy p3 $R/p3.bin 1a607613a29d2c4d62e16ce31df5214f160796391730b2fbc55495fd286fc894 \
  --policy p4 $R/p4.bin 66ec2f87d3fbfb3100c92325939c0fa43e34c4168e66ffad6cfa73a44c8688ba \
  --policy p5 $R/p5.bin bdc5ab50bb4765f86ebd7e044beb95db09a86bb1cff170eaf800f8781851ec26 \
  --policy hu100 $H/hu100/model.bin 1722f0d8744487fcc1c049373f3e3b0a08926701bbdcec5e617d08b7b62cae47 \
  --policy humix $H/humix/model.bin 9d39dda9d9a5c07a1372dd7a876353fbeffc664eb321c891570c0038558493fc \
  --card-buckets /home/dberweger/cygnus-qualification-20261014/tables \
  --journal $W/journal-$S.jsonl --max-hands $HANDS --buy-in 2000 --stop-file $W/STOP \
  > $W/bot-$S.out 2> $W/bot-$S.err < /dev/null &
echo "started $!"
