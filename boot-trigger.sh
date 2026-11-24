#!/usr/bin/env bash
# 开机补触发（crontab @reboot 调用）。
# 只在 16:00–19:09 之间开机时补一次，避免早上开机就拉起一个要空等十小时的云端 job。
# 结果：白天关机、傍晚才开机时，晚餐/午餐提醒也不会漏。
set -uo pipefail

H=$(date +%H); H=$((10#$H))
M=$(date +%M); M=$((10#$M))

if [ "$H" -lt 16 ]; then
    echo "$(date '+%F %T') 开机过早，跳过" 
    exit 0
fi
if [ "$H" -gt 19 ] || { [ "$H" -eq 19 ] && [ "$M" -ge 10 ]; }; then
    echo "$(date '+%F %T') 已过 19:10，跳过"
    exit 0
fi

# 等网络就绪（@reboot 时 DNS/代理常还没起来）
sleep 90

cd "/home/heng/文档/Default Project/health-reminder" || exit 1
./trigger.sh
