#!/bin/bash

while true
do
    if ! pgrep -f canary_executor.py > /dev/null
    then
        systemctl restart canary-battle.service
    fi

    sleep 60
done
