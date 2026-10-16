#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""暴跌实时汇报：任一下跌超阈值立即推送飞书（每标的每交易日只报一次）。

用法:
    python3 alert.py --print     # 只打印，不发送
    python3 alert.py             # 检查并推送（crontab 每 5 分钟）
"""

import json
import os
import sys
from datetime import datetime

try:
    import ai
except Exception:
    ai = None

import report as R

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "logs", "alert_state.json")

def load_state():
    try:
        with open(STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def main():
    cfg = R.load_config()
    threshold = float(cfg.get("alert_drop_pct", 5))
    items = R.collect(cfg)
    today = datetime.now().strftime("%Y-%m-%d")
    state = load_state()

    hits = []
    for i in items:
        if i.get("pct") is None:
            continue
        if i["pct"] <= -threshold and state.get(i["code"]) != today:
            hits.append(i)

    if not hits:
        print("无触发（阈值 -%.1f%%）" % threshold)
        return

    lines = ["【暴跌提醒】%s" % datetime.now().strftime("%Y-%m-%d %H:%M"), ""]
    for i in hits:
        lines.append("· %s %s：%.4f（%+.2f%%）" % (i["code"], i["name"], i["price"], i["pct"]))
    body = "\n".join(lines)

    prompt = (
        "使用 10-mind-decision-engine skill 的 Investment Mode。\n"
        + ai.STANDING + "\n"
        "以下持仓今日单日跌幅达到阈值：\n" + body + "\n\n"
        "请判断每只是情绪杀还是基本面杀（无信息则说明不确定），并给出 持有/减仓/止盈 结论之一；"
        "最后给一句纪律提醒。纯文本，200 字内，只用给定信息，不编造。不要出现‘建仓/加仓’。"
    )
    if "--no-ai" not in sys.argv and ai is not None:
        try:
            body += "\n\n【AI 分析】\n" + ai.ask(prompt)
        except Exception as e:
            body += "\n\n【AI 分析】生成失败：%s" % e
            body += "\n【纪律】不因单日暴跌加仓；先看是情绪杀还是订单杀，再决定是否行动。"
    else:
        body += "\n\n【纪律】不因单日暴跌加仓；先看是情绪杀还是订单杀，再决定是否行动。"

    title = "暴跌提醒 %s" % datetime.now().strftime("%m-%d %H:%M")

    if "--print" in sys.argv:
        print("标题:", title)
        print("内容:\n" + body)
        return

    hook = os.environ.get("FEISHU_WEBHOOK_INVEST") or cfg.get("feishu_webhook", "")
    if not hook or "在这里填" in hook:
        raise SystemExit("请先在 config.json 填写 feishu_webhook")
    R.send_feishu(hook, title, body)
    for i in hits:
        state[i["code"]] = today
    save_state(state)
    print(title)

if __name__ == "__main__":
    main()
