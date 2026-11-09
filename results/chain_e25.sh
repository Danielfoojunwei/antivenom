#!/bin/sh
# runs after chain_new.sh finishes (its PID is $1); offline, one job at a time
cd "/Users/danielfoojunwei/Swarm Alignment Hackathon/antivenom"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
while kill -0 "$1" 2>/dev/null; do sleep 60; done
for M in permute prefixfree s4; do .venv/bin/python experiments/e25_robustness.py --mode $M; done
