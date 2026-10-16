#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三餐提醒：通过 飞书自定义机器人 Webhook 推送。

用法:
    python3 remind.py lunch    # 提醒“明天”的午餐（建议 20:30 运行）
    python3 remind.py dinner   # 提醒“今天”的晚餐（建议 19:10 运行）
    python3 remind.py shop     # 推送本周采购清单（建议周日下午运行）
    python3 remind.py lunch --print     # 只打印不发送，用于测试
    python3 remind.py lunch --desktop   # 发本机桌面通知，用于测试
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Asia/Shanghai")
except Exception:
    TZ = None

BASE = os.path.dirname(os.path.abspath(__file__))
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def now_cn():
    return datetime.now(TZ) if TZ else datetime.now()

# 7天计划：index 0=周一 ... 6=周日
LUNCH = {
    0: "米饭 + 鸡腿肉 + 西兰花 + 番茄",
    1: "米饭 + 清蒸鱼 + 白菜 + 菠菜 + 豆腐",
    2: "米饭 + 瘦猪肉炒青菜 + 番茄 + 菌菇",
    3: "米饭 + 鸡肉 + 鸡蛋 + 青菜 + 菠菜",
    4: "米饭 + 草鱼 + 西兰花 + 菌菇 + 豆腐",
    5: "米饭 + 虾仁炒蛋 + 番茄 + 青菜",
    6: "米饭 + 排骨炖冬瓜 + 瘦牛肉炒芹菜 + 白菜",
}
DINNER = {
    0: "无糖豆浆250mL + 全麦面包2片",
    1: "纯牛奶250mL + 玉米1根",
    2: "无糖豆浆250mL + 红薯150~200g",
    3: "纯牛奶250mL + 全麦面包2片",
    4: "无糖豆浆250mL + 玉米1根 + 鸡蛋1个",
    5: "纯牛奶250mL + 红薯150~200g",
    6: "无糖豆浆250mL + 全麦面包2片",
}
BREAKFAST = {
    0: "纯牛奶250mL + 全麦面包2片",
    1: "无糖豆浆250mL + 全麦面包2片",
    2: "纯牛奶250mL + 全麦面包2片",
    3: "无糖豆浆250mL + 全麦面包2片",
    4: "纯牛奶250mL + 全麦面包2片",
    5: "无糖豆浆250mL + 全麦面包2片",
    6: "纯牛奶250mL + 全麦面包2片",
}

RULES = "少油少糖；酒尽量不喝；水/茶/无糖饮料优先；水果+少量原味坚果当零食，红薯干控制在30~50g。"

# 每周日推送的采购清单
SHOPPING = (
    "【肉类】\n"
    "· 鸡腿肉/鸡胸 500g（去皮）\n"
    "· 鱼 500~600g（草鱼/鲈鱼/巴沙鱼）\n"
    "· 瘦猪肉 300g（里脊/瘦肉）\n"
    "· 排骨 500g\n"
    "· 瘦牛肉 300g（里脊/后腿）\n"
    "· 虾仁 300g\n\n"
    "【蛋豆】\n"
    "· 鸡蛋 1板（约10个）\n"
    "· 豆腐 2~3盒\n\n"
    "【蔬菜】\n"
    "· 西兰花、白菜、青菜、番茄\n"
    "· 菠菜、菌菇、冬瓜、芹菜\n\n"
    "【主食】\n"
    "· 红薯 1kg\n"
    "· 玉米 4根"
)


def load_config():
    path = os.path.join(BASE, "config.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build(mode):
    now = now_cn()
    if mode == "lunch":
        target = now + timedelta(days=1)
        title = "明天(%s)午餐" % WEEKDAYS[target.weekday()]
        body = "【午餐】%s\n\n米饭 + 一份肉/鱼/虾/豆腐 + 两份蔬菜，正常吃，别天天油炸/红烧。" % LUNCH[target.weekday()]
        body += "\n\n【顺带早餐】%s" % BREAKFAST[target.weekday()]
        body += "\n\n【规则】" + RULES
    elif mode == "dinner":
        target = now
        title = "今晚(%s)晚餐" % WEEKDAYS[target.weekday()]
        body = "【晚餐】%s" % DINNER[target.weekday()]
        body += "\n\n太饿的话可再加1个鸡蛋或把主食加量。"
        body += "\n\n【规则】" + RULES
    elif mode == "shop":
        title = "本周采购清单（周日）"
        body = SHOPPING
    else:
        raise SystemExit("参数只能是 lunch / dinner / shop")
    return title, body


def send_serverchan(key, title, body):
    url = "https://sctapi.ftqq.com/%s.send" % key
    data = urllib.parse.urlencode({"title": title, "desp": body}).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def send_feishu(webhook, title, body):
    payload = {"msg_type": "text", "content": {"text": "%s\n\n%s" % (title, body)}}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def send(cfg, title, body):
    provider = cfg.get("provider", "feishu")
    if provider == "feishu":
        raw = os.environ.get("FEISHU_WEBHOOK") or cfg.get("feishu_webhook", "")
        hooks = [
            h for h in re.split(r"[,\s;]+", raw) if h.strip() and "在这里填" not in h
        ]
        if not hooks:
            raise SystemExit("请先在 config.json 填写 feishu_webhook（可填多个，逗号或换行分隔）")
        results = []
        for h in hooks:
            r = send_feishu(h, title, body)
            results.append("[%s...] %s" % (h[-8:], r))
        return "\n".join(results)
    if provider == "serverchan":
        key = os.environ.get("SERVERCHAN_KEY") or cfg.get("serverchan_key", "")
        if not key or "在这里填" in key:
            raise SystemExit("请先在 config.json 填写 serverchan_key")
        return send_serverchan(key, title, body)
    raise SystemExit("未知 provider: %s（可选 feishu / serverchan）" % provider)


def desktop(title, body):
    import subprocess
    subprocess.run(["notify-send", "-u", "normal", title, body], check=False)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--print" in sys.argv
    if not args:
        raise SystemExit(__doc__)
    mode = args[0]
    title, body = build(mode)

    if dry:
        print("标题:", title)
        print("内容:\n" + body)
        return

    if "--desktop" in sys.argv:
        desktop(title, body)
        print("已发桌面通知:", title)
        return

    cfg = load_config()
    result = send(cfg, title, body)
    print(title)
    print(result)


if __name__ == "__main__":
    main()
