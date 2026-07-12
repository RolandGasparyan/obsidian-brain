#!/bin/bash

while true
do
    cd /root/canary || exit

    TS=$(date +%Y-%m-%d_%H:%M:%S)

    grep -Ei "BUY|SELL|EXIT|TAKE PROFIT" runtime/battle.log | tail -300 \
      >> intelligence/memory/trade_memory.jsonl

    echo "{ \"timestamp\": \"$TS\", \"brain_cycle\": \"adaptive_evolution\" }" \
      >> intelligence/brain/brain_cycles.jsonl

    echo "{ \"timestamp\": \"$TS\", \"experience\": \"market_learning\" }" \
      >> intelligence/rl/experience_buffer.jsonl

    echo "{ \"timestamp\": \"$TS\", \"mutation\": \"strategy_adaptation\" }" \
      >> intelligence/evolution/behavior_evolution.jsonl

    cp runtime/battle.log backups/brain/battle_$TS.log 2>/dev/null || true

    sleep 60
done
