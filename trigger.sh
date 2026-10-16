#!/usr/bin/env bash
# 本机 17:50 运行：推一下 evening-trigger.txt，让云端任务在 19:10 / 20:30 准点发。
# 用 SSH 推送，不依赖任何 token，不会过期。
# 重复触发不会重复发消息：workflow 的 concurrency 会把旧任务取消掉。
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || exit 1

export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

TODAY="$(date '+%F')"
NOW="$(date '+%T')"

git pull --rebase --quiet origin main >/dev/null 2>&1

echo "$TODAY $NOW" > evening-trigger.txt
git add evening-trigger.txt
git commit --quiet -m "trigger evening $TODAY $NOW" || { echo "$TODAY $NOW 无变化，未触发"; exit 0; }

if git push --quiet origin main; then
    echo "$TODAY $NOW 已触发云端晚间任务（19:10 晚餐 / 20:30 午餐）"
else
    echo "$TODAY $NOW push 失败"
    git reset --quiet --hard HEAD~1
    exit 1
fi
