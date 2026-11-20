#!/usr/bin/env python3
"""Audit Google Ads conversion actions: what Smart Bidding is actually optimising for.

Reads the conversion actions table (Goals > Conversions > Summary, downloaded with the
columns listed in references/export-columns.md) or the API CSV from gaql_pull.py.

Checks (each returns PASS, FAIL, WARN or UNKNOWN when a column is missing):
  C01  primary action with 0 conversions in the period (dead, or tracking broke)
  C02  primary action whose tracking status is not healthy (Inactive, Unverified, No recent)
  C03  lead action counted Every instead of One (one person, many conversions)
  C04  same lead counted twice: an Ads tag and a GA4 import for the same category, both primary
  C05  non-sales action set primary (careers, newsletter, page view, scroll, video)
  C06  purchase action with no value
  C07  more than 3 primary actions (bidding chases a mix; usually one or two real ones)
  C08  local or Google-hosted actions (directions, store visits) primary for a lead business
  C09  bid strategy vs conversion volume (needs --campaigns): smart bidding on very few
       conversions, or Maximize clicks while conversions exist

Never edit actions from this output alone: read the "Fix" column, confirm each change with
the account owner, and re-read the account after the change (see SKILL.md).

Examples:
  python conversions_audit.py conversion-actions.csv
  python conversions_audit.py conversion-actions.csv --campaigns campaigns-month.csv --days 30
  python conversions_audit.py conversion-actions.csv --owner-leads 21   # leads the business counted

Exit codes: 0 no FAIL, 1 at least one FAIL, 2 bad input.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adsreport import read_report, num  # noqa: E402

NON_SALES = re.compile(r"(career|job|applica|hiring|newsletter|subscribe|page ?view|scroll|engaged|video|time on|session|add to wishlist|sign.?up|signup)", re.I)
LEAD_CAT = re.compile(r"(lead|call|contact|form|quote|book|appointment|phone|signup|sign-up)", re.I)
PURCHASE = re.compile(r"(purchase|sale|order|checkout)", re.I)
LOCAL = re.compile(r"(google hosted|google_hosted|local action|store visit|directions|get directions)", re.I)
GA4 = re.compile(r"(google analytics|ga4|firebase|analytics)", re.I)
HEALTHY = re.compile(r"(recording|enabled|active|^$)", re.I)


def is_primary(r):
    o = (r.get("optimization") or "").strip().lower()
    if o in ("primary", "true", "yes", "1"):
        return True
    if o in ("secondary", "false", "no", "0"):
        return False
    inc = (r.get("include") or "").strip().lower()
    if inc:
        return inc in ("yes", "true", "1")
    return None


def audit(rows, days, campaigns, owner_leads):
    out = []

    def add(cid, state, action, finding, fix):
        out.append({"check": cid, "state": state, "action": action, "finding": finding, "fix": fix})

    have = lambda k: any(r.get(k) not in (None, "") for r in rows)
    prim = [r for r in rows if is_primary(r)]
    if not have("optimization") and not have("include"):
        add("C00", "UNKNOWN", "-", "no Primary/Secondary column: most checks need it",
            "add the 'Action optimization' column before downloading")

    for r in prim:
        name = r.get("conv_action") or "?"
        conv, allc = num(r.get("conv")), num(r.get("all_conv"))
        status = (r.get("tracking_status") or "").strip()
        src = f"{r.get('conv_source', '')} {r.get('conv_category', '')} {name}"
        if conv == 0 and allc == 0:
            add("C01", "FAIL", name, f"primary, 0 conversions in {days} days",
                "check the tag fires (tracking-doctor); if the action is retired set it secondary. "
                "Do not delete: removal cannot be undone and old reports lose it")
        if status and not HEALTHY.search(status):
            add("C02", "FAIL", name, f"primary, tracking status '{status}'",
                "fix the tag or import first; until then this action feeds bidding nothing")
        ct = (r.get("count_type") or "").lower()
        if ct and ("every" in ct or "many" in ct) and LEAD_CAT.search(src) and not PURCHASE.search(src):
            add("C03", "FAIL", name, "lead action counts Every: one person who converts twice is counted twice",
                "set Count to One for leads; keep Every only for purchases")
        if NON_SALES.search(name) or NON_SALES.search(r.get("conv_category") or ""):
            add("C05", "FAIL", name, "non-sales action is primary: bidding will buy more of it",
                "set it secondary (observe only)")
        if PURCHASE.search(src) and num(r.get("conv_value")) == 0 and not (r.get("value_setting") or "").strip():
            add("C06", "WARN", name, "purchase action reports no value",
                "send the order value with the tag; value-based bidding needs it")
        if LOCAL.search(src):
            add("C08", "WARN", name, "local/Google-hosted action is primary",
                "for a lead business set secondary: directions clicks are not leads and inflate conversions")

    # C04 duplicates: same category, a GA4 import and a non-GA4 action, both primary
    cats = {}
    for r in prim:
        cat = (r.get("conv_category") or "").strip().lower() or "?"
        cats.setdefault(cat, []).append(r)
    for cat, group in cats.items():
        g4 = [r for r in group if GA4.search(r.get("conv_source") or "") or GA4.search(r.get("conv_action") or "")]
        tag = [r for r in group if r not in g4 and not LOCAL.search(r.get("conv_source") or "")]
        if g4 and tag:
            add("C04", "FAIL", f"{tag[0].get('conv_action')} + {g4[0].get('conv_action')}",
                f"category '{cat}' has an Ads tag and a GA4 import both primary: one lead counted twice",
                "keep one primary (usually the Ads tag), set the other secondary")
    real = [r for r in prim if not NON_SALES.search(r.get("conv_action") or "")]
    if len(prim) > 3:
        add("C07", "WARN", f"{len(prim)} primary actions", f"{len(prim)} primary actions ({len(real)} look like real leads or sales)",
            "keep primary only for actions that are money or a qualified lead; the rest secondary")
    if not prim and (have("optimization") or have("include")):
        add("C07", "FAIL", "-", "no primary action: smart bidding has nothing to optimise for", "set the real lead or sale action primary")

    total_primary = sum(num(r.get("conv")) for r in prim)
    if owner_leads is not None:
        ratio = total_primary / owner_leads if owner_leads else float("inf")
        state = "FAIL" if ratio > 1.5 or ratio < 0.5 else "PASS"
        add("C10", state, "account vs owner", f"Ads counts {total_primary:g} primary conversions, the business counted {owner_leads}",
            "over 1.5x: duplicates or non-leads are primary; under 0.5x: tags miss leads. Match the lead paths list")

    if campaigns:
        for c in campaigns:
            name = c.get("campaign") or "?"
            bs = (c.get("bid_strategy") or "").lower().replace("_", " ")
            conv = num(c.get("conv"))
            per_month = conv * 30 / days if days else conv
            if ("maximize clicks" in bs or "target spend" in bs) and conv > 0:
                add("C09", "WARN", name, f"Maximize clicks with {conv:g} conversions: it buys clicks, not leads",
                    "after about 15 to 30 conversions a month and clean tracking, test Maximize conversions")
            if any(k in bs for k in ("target cpa", "maximize conversions", "target roas", "conversion value")) and per_month < 15:
                add("C09", "WARN", name, f"smart bidding on about {per_month:.0f} conversions a month",
                    "bidding learns slowly below about 15 to 30 a month; check the primary actions are real first")
    if not out:
        add("ALL", "PASS", "-", "no issues found in the columns provided", "")
    return out, total_primary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("actions", help="conversion actions CSV")
    ap.add_argument("--campaigns", help="campaign report with Bid strategy type and Conversions")
    ap.add_argument("--days", type=int, default=30, help="days the reports cover (default 30)")
    ap.add_argument("--owner-leads", type=int, default=None, help="leads the business itself counted in the same period")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rows, _ = read_report(a.actions, need=("conv_action",))
    camps = read_report(a.campaigns, need=("campaign",))[0] if a.campaigns else []
    out, total = audit(rows, a.days, camps, a.owner_leads)
    fails = [o for o in out if o["state"] == "FAIL"]
    if a.json:
        print(json.dumps({"findings": out, "primary_conversions": total}, indent=2))
    else:
        print("## Conversion actions audit\n")
        print(f"{len(rows)} actions, {sum(1 for r in rows if is_primary(r))} primary, {total:g} primary conversions in {a.days} days.\n")
        print("| Check | State | Action | Finding | Fix |")
        print("|---|---|---|---|---|")
        order = {"FAIL": 0, "WARN": 1, "UNKNOWN": 2, "PASS": 3}
        for o in sorted(out, key=lambda o: (order[o["state"]], o["check"])):
            print(f"| {o['check']} | {o['state']} | {o['action']} | {o['finding']} | {o['fix']} |")
        print("\nAfter any change: re-read the account. In the API, customer_conversion_goal.biddable does not follow "
              "primary_for_goal automatically, so a goal can stay biddable after you set its action secondary.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
