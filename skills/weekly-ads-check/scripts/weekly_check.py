#!/usr/bin/env python3
"""Weekly Google Ads check: this week vs last week per campaign, with plain flags.

Give two campaign reports for equal-length periods (UI download or gaql_pull.py output).
Flags, in the order to act on them:
  TRACKING   conversions fell to 0 (or by 80%+) while clicks held: check tracking before ads
  SPEND_UP   spend up 25%+ while conversions flat or down
  CPA        CPA over 1.5x target (or over 1.5x last week when no target given)
  VOLUME     impressions down 50%+: approvals, budget, bids or a policy issue
  BUDGET     lost IS (budget) up 10+ points
  LOW_DATA   fewer than 3 days or under 1x target CPA of spend: do not judge yet

--log FILE appends a dated entry (flags + a blank "Decision:" line) so next week starts
from what was decided, not from memory.

Examples:
  python weekly_check.py campaigns-week-curr.csv campaigns-week-prev.csv --target-cpa 60
  python weekly_check.py curr.csv prev.csv --target-cpa 60 --log decisions.md --date 2026-11-30

Exit codes: 0 no flags, 1 flags raised, 2 bad input.
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adsreport import read_report, num  # noqa: E402


def agg(rows):
    d = {}
    for r in rows:
        name = r.get("campaign") or "?"
        x = d.setdefault(name, {"cost": 0.0, "clicks": 0.0, "impr": 0.0, "conv": 0.0, "lost_is_budget": None})
        for k in ("cost", "clicks", "impr", "conv"):
            x[k] += num(r.get(k))
        if r.get("lost_is_budget") not in (None, "", "--"):
            x["lost_is_budget"] = num(r.get("lost_is_budget"))
    return d


def change(a, b):
    if b == 0:
        return None if a == 0 else float("inf")
    return (a - b) / b


def fmt(c):
    if c is None:
        return "-"
    if c == float("inf"):
        return "new"
    return f"{c * 100:+.0f}%"


def check(cur, prev, target, days):
    rows, flags = [], []
    for name in sorted(set(cur) | set(prev)):
        c = cur.get(name, {"cost": 0, "clicks": 0, "impr": 0, "conv": 0, "lost_is_budget": None})
        p = prev.get(name, {"cost": 0, "clicks": 0, "impr": 0, "conv": 0, "lost_is_budget": None})
        cpa_c = c["cost"] / c["conv"] if c["conv"] else None
        cpa_p = p["cost"] / p["conv"] if p["conv"] else None
        f = []
        if p["conv"] >= 2 and (c["conv"] == 0 or c["conv"] <= p["conv"] * 0.2) and c["clicks"] >= p["clicks"] * 0.7:
            f.append(("TRACKING", f"conversions {p['conv']:g} -> {c['conv']:g} with clicks {p['clicks']:g} -> {c['clicks']:g}: "
                                  "check the tag and the form before touching bids"))
        sc = change(c["cost"], p["cost"])
        if sc is not None and sc != float("inf") and sc >= 0.25 and c["conv"] <= p["conv"]:
            f.append(("SPEND_UP", f"spend {fmt(sc)} with conversions {p['conv']:g} -> {c['conv']:g}"))
        ref = target or cpa_p
        if cpa_c and ref and cpa_c > 1.5 * ref:
            f.append(("CPA", f"CPA {cpa_c:.2f} vs {'target' if target else 'last week'} {ref:.2f}"))
        ic = change(c["impr"], p["impr"])
        if ic is not None and ic <= -0.5:
            f.append(("VOLUME", f"impressions {fmt(ic)}: check approvals, budget, bids, policy"))
        if c["lost_is_budget"] is not None and p["lost_is_budget"] is not None and c["lost_is_budget"] - p["lost_is_budget"] >= 10:
            f.append(("BUDGET", f"lost IS budget {p['lost_is_budget']:g}% -> {c['lost_is_budget']:g}%"))
        if days < 3 or (target and c["cost"] < target and not f):
            f.append(("LOW_DATA", "too little data to judge this week"))
        rows.append({"campaign": name, "cost": round(c["cost"], 2), "cost_change": fmt(sc), "conv": c["conv"],
                     "conv_prev": p["conv"], "cpa": round(cpa_c, 2) if cpa_c else None, "cpa_prev": round(cpa_p, 2) if cpa_p else None,
                     "flags": [{"flag": k, "detail": v} for k, v in f]})
        flags += [(name, k, v) for k, v in f if k != "LOW_DATA"]
    order = ["TRACKING", "SPEND_UP", "CPA", "VOLUME", "BUDGET"]
    flags.sort(key=lambda x: order.index(x[1]))
    return rows, flags


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("current")
    ap.add_argument("previous")
    ap.add_argument("--target-cpa", type=float, default=0)
    ap.add_argument("--days", type=int, default=7, help="days in each period (default 7)")
    ap.add_argument("--log", metavar="FILE", help="append a dated entry to this markdown log")
    ap.add_argument("--date", help="date for the log entry, default today")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    cur = agg(read_report(a.current, need=("campaign", "cost"))[0])
    prev = agg(read_report(a.previous, need=("campaign", "cost"))[0])
    rows, flags = check(cur, prev, a.target_cpa, a.days)
    tc, tp = sum(x["cost"] for x in cur.values()), sum(x["cost"] for x in prev.values())
    vc, vp = sum(x["conv"] for x in cur.values()), sum(x["conv"] for x in prev.values())
    head = (f"Account: spend {tp:.2f} -> {tc:.2f} ({fmt(change(tc, tp))}), conversions {vp:g} -> {vc:g}, "
            f"CPA {tp / vp if vp else 0:.2f} -> {tc / vc if vc else 0:.2f}")
    if a.json:
        print(json.dumps({"summary": head, "campaigns": rows}, indent=2))
    else:
        print("## Weekly ads check\n")
        print(head + "\n")
        print("| Campaign | Spend | Change | Conv (prev) | CPA (prev) | Flags |")
        print("|---|---|---|---|---|---|")
        for r in rows:
            fl = "; ".join(f"{x['flag']}: {x['detail']}" for x in r["flags"]) or "ok"
            print(f"| {r['campaign']} | {r['cost']:.2f} | {r['cost_change']} | {r['conv']:g} ({r['conv_prev']:g}) | "
                  f"{r['cpa'] or '-'} ({r['cpa_prev'] or '-'}) | {fl} |")
        if flags:
            print(f"\nFirst look at: {flags[0][0]} ({flags[0][1]}).")
    if a.log:
        date = a.date or dt.date.today().isoformat()
        with open(a.log, "a", encoding="utf-8") as f:
            f.write(f"\n## {date}\n\n{head}\n\n")
            for name, k, v in flags:
                f.write(f"- {k} {name}: {v}\n")
            if not flags:
                f.write("- no flags\n")
            f.write("\nDecision:\nWhy:\nCheck again on:\n")
        print(f"\nlogged to {a.log}")
    return 1 if flags else 0


if __name__ == "__main__":
    sys.exit(main())
