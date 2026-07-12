#!/bin/bash

while true
do
    cd /root/canary || exit

    TS=$(date +%Y-%m-%d_%H:%M:%S)

    echo "{ \
\"timestamp\":\"$TS\", \
\"market_reasoning\":\"active\", \
\"signal_ai\":\"learning\", \
\"adaptive_strategy\":\"enabled\" \
}" >> intelligence/meta_ai/meta_cycles.jsonl

    grep -Ei "BUY|SELL|EXIT|TAKE PROFIT|Pairs ranked" runtime/battle.log | tail -200 \
      >> intelligence/market_ai/market_memory.jsonl

    sleep 180
done
