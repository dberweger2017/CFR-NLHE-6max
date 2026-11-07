#!/bin/bash
# Journal replay, then the deploy check, with the capped client (feature/openpoker-stack-cap).
set -u
W=/home/dberweger/openpoker-stack-cap-20261106
R=/mnt/data2tb/openpoker-routing-20261027/models
H=/mnt/data2tb/openpoker-heads-up-20261027/main
L=/mnt/data2tb/openpoker-live-pilot-20261027
PY=/home/dberweger/nplayer-bb200-feasibility-20261022/venv/bin/python
POL=(--policy six /mnt/data2tb/openpoker-mixed-stacks-20261027/six.bin f894a59f8a92424d735438726d16834901a7dcaf6d560c98b950fb72a143c9ea
  --policy mix $R/mix.bin 64c693c4a3a56f69fcdd050b5da9dde0cfee76e108676b4816dbab98dccfbb20
  --policy p3 $R/p3.bin 1a607613a29d2c4d62e16ce31df5214f160796391730b2fbc55495fd286fc894
  --policy p4 $R/p4.bin 66ec2f87d3fbfb3100c92325939c0fa43e34c4168e66ffad6cfa73a44c8688ba
  --policy p5 $R/p5.bin bdc5ab50bb4765f86ebd7e044beb95db09a86bb1cff170eaf800f8781851ec26
  --policy hu100 $H/hu100/model.bin 1722f0d8744487fcc1c049373f3e3b0a08926701bbdcec5e617d08b7b62cae47
  --policy humix $H/humix/model.bin 9d39dda9d9a5c07a1372dd7a876353fbeffc664eb321c891570c0038558493fc
  --policy p3mix /home/dberweger/openpoker-short-mixed-20261028/main/p3mix/model.bin afddb59521bd518aa25ef5c7a499ea09059b102dc289d34d3978d1438a85a16a
  --card-buckets /home/dberweger/cygnus-qualification-20261014/tables)
cd $W/source
nice -n 5 $PY -m scripts.openpoker_cap_replay $L/journal-1.jsonl $L/journal-2.jsonl --routes $W/routes.json "${POL[@]}" --out $W/replay.json > $W/replay.out 2> $W/replay.err
nice -n 5 $PY -m scripts.openpoker_deploy_check --routes $W/routes.json "${POL[@]}" --out $W/deploy-check.json > $W/deploy.out 2> $W/deploy.err
echo done > $W/CHECKS-DONE
