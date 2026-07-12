#!/bin/bash

while true
do
    cd /root/canary || exit

    TS=$(date +%Y-%m-%d_%H:%M:%S)

    grep -Ei "BUY|SELL|EXIT|TAKE PROFIT" runtime/battle.log | tail -200 \
      >> intelligence/memory/trade_memory.jsonl

    echo "{ \"timestamp\": \"$TS\", \"cycle\": \"learning\" }" \
      >> intelligence/rl/experience_buffer.jsonl

    cp runtime/battle.log backups/self_learning/battle_$TS.log 2>/dev/null || true

    sleep 300
done
