#!/bin/bash

while true
do
    cd /root/canary || exit

    TS=$(date +%Y-%m-%d_%H:%M:%S)

    echo "{ \
\"timestamp\":\"$TS\", \
\"brain\":\"recursive_reasoning\", \
\"status\":\"learning\", \
\"evolution\":\"active\" \
}" >> intelligence/brain/recursive_cycles.jsonl

    grep -Ei "BUY|SELL|EXIT|TAKE PROFIT" runtime/battle.log | tail -100 \
      >> intelligence/reasoning/trade_reasoning_memory.jsonl

    sleep 120
done
