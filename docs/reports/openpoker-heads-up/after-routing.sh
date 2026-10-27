#!/bin/bash
# Start the heads-up controller once the routing study's controller (pid $1) has exited.
while kill -0 $1 2>/dev/null; do sleep 60; done
tail -1 /mnt/data2tb/openpoker-routing-20261027/stages.jsonl | grep -q '"done"' || { echo 'routing run did not finish; not starting' >&2; exit 1; }
cd /mnt/data2tb/openpoker-heads-up-20261027 && exec bash run.sh > run.out 2> run.err
