#!/bin/sh
cd "/Users/danielfoojunwei/Swarm Alignment Hackathon/antivenom"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
for D in hotpotqa msmarco; do .venv/bin/python experiments/e29_tier2.py $D; done
