#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""持仓日报：抓取 ETF / 场外基金最新价格，计算盈亏与集中度，推送飞书。

用法:
    python3 report.py            # 生成并推送日报
    python3 report.py --print    # 只打印，不发送
    python3 report.py --desktop  # 发本机桌面通知
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

try:
    import ai
except Exception:
    ai = None

BASE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def http_get(url, referer=None, encoding="utf-8", timeout=15, retries=3):
    cmd = ["curl", "-sL", "--max-time", str(timeout), "-H", "User-Agent: " + UA]
    if referer:
        cmd += ["-H", "Referer: " + referer]
    cmd.append(url)
    last = None
    for i in range(retries + 1):
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
            if proc.returncode == 0 and proc.stdout:
                return proc.stdout.decode(encoding, "ignore")
            last = RuntimeError("curl rc=%s" % proc.returncode)
        except Exception as e:
            last = e
        time.sleep(1 + i)
    raise last

def load_config():
    raw = os.environ.get("INVEST_CONFIG")
    if raw and raw.strip():
        return json.loads(raw)
    with open(os.path.join(BASE, "config.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_etfs(codes, market="sh"):
    query = ",".join("%s%s" % (market, c) for c in codes)
    text = http_get("https://qt.gtimg.cn/q=" + query, encoding="gbk")
    out = {}
    for line in text.split(";"):
        line = line.strip()
        if "=" not in line:
            continue
        body = line.split("=", 1)[1].strip().strip('"')
        f = body.split("~")
        if len(f) < 35:
            continue
        code = f[2]
        out[code] = {
            "name": f[1],
            "price": float(f[3]),
            "prev": float(f[4]),
            "change": float(f[31]),
            "pct": float(f[32]),
            "high": float(f[33]),
            "low": float(f[34]),
            "time": f[30],
        }
    return out

def fetch_fund(code):
    url = "https://api.fund.eastmoney.com/f10/lsjz?fundCode=%s&pageIndex=1&pageSize=1" % code
    text = http_get(url, referer="https://fundf10.eastmoney.com/")
    data = json.loads(text)
    rows = data.get("Data", {}).get("LSJZList") or []
    if not rows:
        return None
    r = rows[0]
    return {
        "name": "",
        "price": float(r["DWJZ"]),
        "pct": float(r["JZZZL"]),
        "date": r["FSRQ"],
    }

def collect(cfg):
    etf_codes = [h["code"] for h in cfg["holdings"] if h["type"] == "etf"]
    etf_data = fetch_etfs(etf_codes) if etf_codes else {}
    items = []
    for h in cfg["holdings"]:
        if h["type"] == "etf":
            d = etf_data.get(h["code"])
        else:
            d = fetch_fund(h["code"])
        if not d:
            items.append({"code": h["code"], "name": h["name"], "sector": h["sector"],
                          "error": "取数失败", "shares": h.get("shares"), "cost": h.get("cost")})
            continue
        shares = h.get("shares")
        cost = h.get("cost") or 0
        price = d["price"]
        if h["type"] == "etf":
            t = d.get("time", "")
            asof = ("%s-%s %s:%s" % (t[4:6], t[6:8], t[8:10], t[10:12])) if len(t) >= 12 else ""
        else:
            asof = d.get("date", "")
        value = price * shares if shares else None
        pnl = (value - cost) if value is not None else None
        pnl_pct = (pnl / cost * 100) if (pnl is not None and cost) else None
        items.append({
            "code": h["code"],
            "name": h.get("name") or d.get("name") or h["code"],
            "sector": h["sector"],
            "price": price,
            "pct": d["pct"],
            "date": d.get("date"),
            "asof": asof,
            "shares": shares,
            "cost": cost,
            "value": value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })
    return items

def build(cfg, items):
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = ["【持仓日报】%s" % today, ""]

    total_value = sum(i["value"] for i in items if i.get("value") is not None)
    total_cost = sum(i["cost"] for i in items if i.get("cost"))
    have_value = total_value > 0

    for i in items:
        tag = "%s %s" % (i["code"], i["name"])
        if i.get("error"):
            lines.append("· %s：%s" % (tag, i["error"]))
            continue
        day = "%+.2f%%" % i["pct"]
        if i.get("value") is not None:
            lines.append("· %s：%.4f（%s） 市值%.0f 盈亏%+.0f（%+.1f%%）"
                         % (tag, i["price"], day, i["value"], i["pnl"], i["pnl_pct"]))
        else:
            extra = "（净值 %s）" % i["date"] if i.get("date") else ""
            lines.append("· %s：%.4f（%s）%s" % (tag, i["price"], day, extra))

    lines.append("")
    if have_value:
        lines.append("合计 市值%.0f / 本金%.0f / 盈亏%+.0f（%+.1f%%）"
                     % (total_value, total_cost, total_value - total_cost,
                        (total_value - total_cost) / total_cost * 100 if total_cost else 0))

        sectors = {}
        for i in items:
            if i.get("value") is None:
                continue
            sectors.setdefault(i["sector"], 0)
            sectors[i["sector"]] += i["value"]
        order = sorted(sectors.items(), key=lambda kv: -kv[1])
        lines.append("集中度：" + "，".join("%s %.1f%%" % (s, v / total_value * 100) for s, v in order))

        tech = sum(v for s, v in sectors.items() if s in cfg.get("tech_sectors", []))
        lines.append("科技合计（%s）：%.1f%%" % ("+".join(cfg.get("tech_sectors", [])), tech / total_value * 100))

        lines.append("")
        lines.append("【风控提示】")
        alerts = []
        for s, v in order:
            cap = cfg.get("sector_caps", {}).get(s)
            w = v / total_value * 100
            if cap and w > cap:
                alerts.append("· %s 占比 %.1f%%，超过上限 %d%%" % (s, w, cap))
        tech_cap = cfg.get("tech_cap")
        if tech_cap and tech / total_value * 100 > tech_cap:
            alerts.append("· 科技合计 %.1f%%，超过上限 %d%%" % (tech / total_value * 100, tech_cap))
        for i in items:
            if i.get("pct") is not None and i["pct"] <= -3:
                alerts.append("· %s 单日 %+.2f%%，注意波动" % (i["name"], i["pct"]))
            if i.get("pnl_pct") is not None and i["pnl_pct"] <= -20:
                alerts.append("· %s 累计 %+.1f%%，检查持有逻辑是否成立" % (i["name"], i["pnl_pct"]))
        lines.extend(alerts or ["· 暂无触发项"])
    else:
        lines.append("（未填写份额，仅显示价格；在 config.json 的 shares 填入份额后自动计算盈亏与集中度）")

    lines.append("")
    lines.append("【纪律】" + cfg.get("rules", ""))
    title = "持仓日报 %s" % datetime.now().strftime("%m-%d")
    return title, "\n".join(lines)

def send_feishu(webhook, title, body):
    payload = {"msg_type": "text", "content": {"text": "%s\n\n%s" % (title, body)}}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")

def desktop(title, body):
    import subprocess
    subprocess.run(["notify-send", "-u", "normal", title, body], check=False)

def ai_conclusion(body):
    prompt = (
        "使用 10-mind-decision-engine skill 的 Investment Mode。\n"
        + ai.STANDING + "\n"
        "以下是今日持仓日报：\n" + body + "\n\n"
        "请对每只持仓给出一句话结论，结论只能是 持有/减仓/止盈 之一，并附一句理由；"
        "再给组合一句话（说明风险）。纯文本，不用表格，300 字内。只用给定数据，不编造。"
        "不要出现‘建仓/加仓/超配’。"
    )
    return ai.ask(prompt)

def main():
    cfg = load_config()
    items = collect(cfg)
    title, body = build(cfg, items)

    if "--no-ai" not in sys.argv and ai is not None:
        try:
            body += "\n\n【AI 结论】\n" + ai_conclusion(body)
        except Exception as e:
            body += "\n\n【AI 结论】生成失败：%s" % e

    if "--print" in sys.argv:
        print("标题:", title)
        print("内容:\n" + body)
        return
    if "--desktop" in sys.argv:
        desktop(title, body)
        print("已发桌面通知:", title)
        return

    hook = os.environ.get("FEISHU_WEBHOOK_INVEST") or cfg.get("feishu_webhook", "")
    if not hook or "在这里填" in hook:
        raise SystemExit("请先在 config.json 填写 feishu_webhook（或复用 health-reminder 的 webhook）")
    result = send_feishu(hook, title, body)
    print(title)
    print(result)

if __name__ == "__main__":
    main()
