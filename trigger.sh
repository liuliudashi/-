#!/usr/bin/env bash
# 本机 17:50 运行：推一下 evening-trigger.txt，让云端任务在 19:10 / 20:30 准点发。
# 用 SSH 推送，不依赖任何 token，不会过期。
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || exit 1

export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

TODAY="$(date '+%F')"
NOW="$(date '+%T')"

if [ -f evening-trigger.txt ] && grep -q "^$TODAY" evening-trigger.txt; then
    echo "$TODAY $NOW 今天已触发过，跳过"
    exit 0
fi

git pull --rebase --quiet origin main >/dev/null 2>&1

echo "$TODAY $NOW" > evening-trigger.txt
git add evening-trigger.txt
git commit --quiet -m "trigger evening $TODAY" || { echo "$TODAY $NOW commit 失败"; exit 1; }

if git push --quiet origin main; then
    echo "$TODAY $NOW 已触发云端晚间任务（19:10 晚餐 / 20:30 午餐）"
else
    echo "$TODAY $NOW push 失败"
    git reset --quiet --hard HEAD~1
    exit 1
fi
