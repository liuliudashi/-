#!/usr/bin/env bash
# 用法: run.sh lunch | run.sh dinner
DIR="/home/heng/文档/Default Project/health-reminder"
mkdir -p "$DIR/logs"
/usr/bin/python3 "$DIR/remind.py" "$1" >> "$DIR/logs/remind.log" 2>&1
