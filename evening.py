#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云端晚间准点发送：19:10 发晚餐、20:30 发明天午餐。

本机 18:00 关机，所以由本机 17:50 推一次 evening-trigger.txt 触发本任务，
任务在云端睡到点再发，发送时间与关机无关。

用法:
    python3 evening.py            # 正常：睡到 19:10 / 20:30 分别发送
    python3 evening.py --now      # 测试：立刻发这两条
    python3 evening.py --dry      # 测试：只打印计划，不睡不发
    python3 evening.py --test     # 测试：只发一条链路自检消息
"""

import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import remind

TZ = ZoneInfo("Asia/Shanghai")
TARGETS = [((19, 10), "dinner"), ((20, 30), "lunch")]
LATE_LIMIT = timedelta(minutes=30)


def stamp():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def send(mode):
    title, body = remind.build(mode)
    cfg = remind.load_config()
    print("[%s] 发送 %s" % (stamp(), title), flush=True)
    print(remind.send(cfg, title, body), flush=True)


def main():
    dry = "--dry" in sys.argv
    now_all = "--now" in sys.argv

    print("[%s] evening 任务启动 (TZ=%s)" % (stamp(), TZ), flush=True)

    if "--test" in sys.argv:
        cfg = remind.load_config()
        title = "云端定时链路自检"
        body = "云端时间 %s\n触发方式 push evening-trigger.txt\n若你看到这条，说明「本机推送 -> 云端准点发送」链路通了。" % stamp()
        print(remind.send(cfg, title, body), flush=True)
        return

    for (h, m), mode in TARGETS:
        now = datetime.now(TZ)
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)

        if now_all:
            send(mode)
            continue

        if target > now:
            wait = (target - now).total_seconds()
            print(
                "[%s] 等待 %.0f 分钟 -> %02d:%02d 发 %s"
                % (stamp(), wait / 60.0, h, m, mode),
                flush=True,
            )
            if dry:
                continue
            time.sleep(wait)
        elif now - target > LATE_LIMIT:
            print(
                "[%s] 已过 %02d:%02d 超过 %d 分钟，跳过 %s"
                % (stamp(), h, m, int(LATE_LIMIT.total_seconds() // 60), mode),
                flush=True,
            )
            continue

        send(mode)

    print("[%s] evening 任务结束" % stamp(), flush=True)


if __name__ == "__main__":
    main()
