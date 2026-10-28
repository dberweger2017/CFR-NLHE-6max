#!/bin/bash
# Starts the controller once the untrained-fallback study's controller (#452) has exited.
W=/home/dberweger/openpoker-short-mixed-20261028
while kill -0 "$1" 2>/dev/null; do sleep 30; done
echo "{\"stage\":\"launch\",\"at\":\"$(date -u +%FT%TZ)\"}" >> $W/stages.jsonl
cd $W && exec ./run.sh
