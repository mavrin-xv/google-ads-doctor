#!/usr/bin/env python3
"""Structure audit of a Google Ads account from campaign and keyword exports.

Checks (state PASS / FAIL / WARN / UNKNOWN when the column is missing / N_A):
  S01  one keyword takes over 50% of spend (single point of failure, often a broad head term)
  S02  broad match keywords in a campaign without smart bidding (broad needs conversion signals)
  S03  keyword spent over 3x target CPA with 0 conversions: pause or fix (kill rule)
       WARN at 1x to 3x: watch, read its search terms
  S04  the same keyword and match type in more than one ad group (they bid against each other)
  S05  ad group with more than 20 keywords (ads cannot match all of them)
  S06  Search lost IS (budget) >= 15%: budget caps you; check marginal CPA before raising it
       lost IS (rank) larger than budget loss: raise Ad Rank (quality, bids) before budget
  S07  enabled campaign that spent at least target CPA with 0 conversions
  S08  Quality Score 4 or below on a keyword with spend
  S09  Search campaign also on Search Partners or Display Network
  S10  enabled campaign with 0 impressions (stuck: approvals, budget, bids, targeting)

The report ends with evidence coverage: share of checks that had the data to run.
Below 60% treat the verdict as a guess and get the missing columns.

Examples:
  python structure_audit.py --campaigns campaigns-month.csv --keywords keywords.csv --target-cpa 60
  python structure_audit.py --campaigns campaigns-month.csv --json

Exit codes: 0 no FAIL, 1 at least one FAIL, 2 bad input.
"""
import argparse
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adsreport import read_report, num, match_type_of  # noqa: E402

SMART = ("maximize conversions", "target cpa", "target roas", "maximize conversion value", "conversion value")
ALL_CHECKS = [f"S{i:02d}" for i in range(1, 11)]


def pct(v):
    return num(v, default=None) if v not in (None, "", "--") else None


def run(camps, kws, target):
    out = []
    ran = set()

    def add(cid, state, where, finding, fix=""):
        out.append({"check": cid, "state": state, "where": where, "finding": finding, "fix": fix})

    camp_by = {c.get("campaign"): c for c in camps}
    if not target:
        cost = sum(num(c.get("cost")) for c in camps) or sum(num(k.get("cost")) for k in kws)
        conv = sum(num(c.get("conv")) for c in camps) or sum(num(k.get("conv")) for k in kws)
        target = cost / conv if conv else 0

    if kws:
        total = sum(num(k.get("cost")) for k in kws)
        ran.update(["S01", "S03", "S04", "S05"])
        top = max(kws, key=lambda k: num(k.get("cost")))
        share = num(top.get("cost")) / total if total else 0
        if share > 0.5:
            add("S01", "FAIL", top.get("keyword"), f"takes {share * 100:.0f}% of keyword spend",
                "split it: exact and phrase versions in their own ad group, read its search terms")
        else:
            add("S01", "PASS", "-", f"top keyword takes {share * 100:.0f}% of spend")
        if any(k.get("campaign") for k in kws) and any(c.get("bid_strategy") for c in camps):
            ran.add("S02")
            flagged = set()
            for k in kws:
                _, mt = match_type_of(k.get("keyword"), k.get("match_type"))
                c = camp_by.get(k.get("campaign"), {})
                bs = (c.get("bid_strategy") or "").lower().replace("_", " ")
                if mt == "broad" and bs and not any(s in bs for s in SMART) and k.get("campaign") not in flagged:
                    n = sum(1 for x in kws if x.get("campaign") == k.get("campaign") and match_type_of(x.get("keyword"), x.get("match_type"))[1] == "broad")
                    add("S02", "FAIL", k.get("campaign"), f"{n} broad keyword(s) on {c.get('bid_strategy')}",
                        "broad without conversion-based bidding matches loosely and bids blind: use phrase/exact or switch bidding")
                    flagged.add(k.get("campaign"))
        for k in kws:
            cost, conv = num(k.get("cost")), num(k.get("conv"))
            if target and conv == 0 and cost >= 3 * target:
                add("S03", "FAIL", k.get("keyword"), f"spent {cost:.2f} (over 3x target CPA {target:.2f}) with 0 conversions",
                    "pause it or narrow the match type; read its search terms first")
            elif target and conv == 0 and cost >= target:
                add("S03", "WARN", k.get("keyword"), f"spent {cost:.2f} (1x to 3x target CPA) with 0 conversions", "watch; read its search terms")
            elif target and conv > 0 and cost / conv > 3 * target:
                add("S03", "FAIL", k.get("keyword"), f"CPA {cost / conv:.2f} is over 3x target", "cut the bid or narrow the match")
        seen = defaultdict(set)
        for k in kws:
            text, mt = match_type_of(k.get("keyword"), k.get("match_type"))
            seen[(text, mt)].add(f"{k.get('campaign')} > {k.get('ad_group')}")
        for (text, mt), groups in seen.items():
            if len(groups) > 1:
                add("S04", "WARN", f"{text} ({mt})", f"in {len(groups)} ad groups: {'; '.join(sorted(groups))}",
                    "keep it in the ad group whose ads and landing page fit it; remove or negate it in the others")
        size = defaultdict(int)
        for k in kws:
            size[f"{k.get('campaign')} > {k.get('ad_group')}"] += 1
        for g, n in size.items():
            if n > 20:
                add("S05", "WARN", g, f"{n} keywords in one ad group", "split by intent so ad text can match the search")
        if any(k.get("qs") not in (None, "", "--") for k in kws):
            ran.add("S08")
            for k in kws:
                qs = num(k.get("qs"), default=None)
                if qs is not None and qs <= 4 and num(k.get("cost")) > 0:
                    add("S08", "WARN", k.get("keyword"), f"Quality Score {qs:g} with {num(k.get('cost')):.2f} spend",
                        "check ad relevance and the landing page for this keyword")

    for c in camps:
        name = c.get("campaign")
        status = (c.get("campaign_status") or "enabled").lower()
        ctype = (c.get("campaign_type") or "").lower()
        cost, conv, impr = num(c.get("cost")), num(c.get("conv")), num(c.get("impr"))
        lb, lr = pct(c.get("lost_is_budget")), pct(c.get("lost_is_rank"))
        if lb is not None or lr is not None:
            ran.add("S06")
            if lb is not None and lb >= 15:
                if lr is not None and lr > lb:
                    add("S06", "WARN", name, f"lost IS budget {lb:g}%, rank {lr:g}%: rank is the bigger loss",
                        "raise Ad Rank first (ad relevance, landing page, bids); more budget buys the worse auctions")
                else:
                    cpa = cost / conv if conv else None
                    ok = cpa is not None and target and cpa <= target
                    add("S06", "FAIL" if conv == 0 else "WARN", name,
                        f"lost IS budget {lb:g}% at CPA {cpa:.2f}" if cpa else f"lost IS budget {lb:g}% with 0 conversions",
                        "budget is the limit and CPA is on target: more budget should buy more leads" if ok
                        else "fix conversions or CPA before adding budget")
            elif lr is not None and lr >= 40:
                add("S06", "WARN", name, f"lost IS rank {lr:g}%", "Ad Rank problem: quality, relevance, bids")
        if "enabled" in status:
            ran.add("S07")
            ran.add("S10")
            if target and conv == 0 and cost >= target:
                add("S07", "FAIL", name, f"spent {cost:.2f} with 0 conversions", "check tracking first, then search terms and keywords")
            if impr == 0:
                add("S10", "WARN", name, "enabled but 0 impressions", "check ad approvals, budget, bids, location and schedule")
        if c.get("networks"):
            ran.add("S09")
            nw = c["networks"].lower()
            if "search" in ctype and ("partner" in nw or "display" in nw):
                add("S09", "WARN", name, f"networks: {c['networks']}",
                    "turn off Display on Search campaigns; keep Partners only if its segment converts")
    # PASS rows for checks that ran clean
    failed = {o["check"] for o in out}
    for cid in sorted(ran - failed):
        add(cid, "PASS", "-", "no issue")
    for cid in ALL_CHECKS:
        if cid not in ran:
            add(cid, "UNKNOWN", "-", "needed columns not in the exports")
    coverage = len(ran) / len(ALL_CHECKS)
    return out, coverage, target


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaigns", help="campaign report CSV")
    ap.add_argument("--keywords", help="keyword report CSV")
    ap.add_argument("--target-cpa", type=float, default=0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not a.campaigns and not a.keywords:
        ap.error("give --campaigns and/or --keywords")
    camps = read_report(a.campaigns, need=("campaign",))[0] if a.campaigns else []
    kws = read_report(a.keywords, need=("keyword", "cost"))[0] if a.keywords else []
    out, coverage, target = run(camps, kws, a.target_cpa)
    band = "high" if coverage >= 0.8 else "medium" if coverage >= 0.6 else "low"
    if a.json:
        print(json.dumps({"findings": out, "coverage": round(coverage, 2), "band": band, "target_cpa": round(target, 2)}, indent=2))
    else:
        print("## Structure audit\n")
        print(f"Target CPA used: {target:.2f}. Evidence coverage {coverage * 100:.0f}% ({band}).\n")
        print("| Check | State | Where | Finding | Fix |")
        print("|---|---|---|---|---|")
        order = {"FAIL": 0, "WARN": 1, "UNKNOWN": 2, "PASS": 3}
        for o in sorted(out, key=lambda o: (order[o["state"]], o["check"])):
            print(f"| {o['check']} | {o['state']} | {o['where']} | {o['finding']} | {o['fix']} |")
        if band == "low":
            print("\nCoverage is low: get the missing columns before acting on this.")
    return 1 if any(o["state"] == "FAIL" for o in out) else 0


if __name__ == "__main__":
    sys.exit(main())
