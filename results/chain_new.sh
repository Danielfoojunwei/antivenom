#!/bin/sh
# waits for the E12b waiter, then runs the new experiments one at a time, offline
cd "/Users/danielfoojunwei/Swarm Alignment Hackathon/antivenom"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
while kill -0 "$1" 2>/dev/null; do sleep 60; done
.venv/bin/python experiments/e21_capture_rotation.py
.venv/bin/python experiments/e20_low_poison_fraction.py
until [ "$(grep -c '^OK' results/download_readers.log)" -ge 2 ]; do sleep 60; done
for M in mlx-community/Meta-Llama-3-8B-Instruct-4bit mlx-community/Mistral-7B-Instruct-v0.3-4bit; do
  .venv/bin/python tests/fidelity_masked.py "$M"
  .venv/bin/python experiments/e22_other_readers.py "$M"
done
