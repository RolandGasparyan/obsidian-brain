#!/bin/bash

while true
do
    cd /root/canary || exit

    git add .gitignore intelligence/configs scripts watchdogs 2>/dev/null

    git commit -m "AUTO EVOLUTION $(date +%Y%m%d_%H%M%S)" 2>/dev/null

    git push origin main 2>/dev/null

    sleep 600
done
