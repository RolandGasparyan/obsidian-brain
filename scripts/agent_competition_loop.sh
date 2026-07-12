#!/bin/bash

while true
do
    cd /root/canary || exit

    TS=$(date +%Y-%m-%d_%H:%M:%S)

    echo "{ \
\"timestamp\":\"$TS\", \
\"trend_agent\":\"active\", \
\"breakout_agent\":\"active\", \
\"scalping_agent\":\"active\", \
\"defense_agent\":\"active\", \
\"volatility_agent\":\"active\", \
\"competition\":\"running\" \
}" >> intelligence/competition/agent_battles.jsonl

    sleep 60
done
