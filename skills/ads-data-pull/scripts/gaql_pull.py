#!/usr/bin/env python3
"""Pull the reports this pack reads straight from the Google Ads API (read-only, stdlib).

Optional path. Everything in the pack also works on CSVs downloaded from the UI
(see references/ui-exports.md). Use this when you have API access and want the same
files every week without clicking.

Reports (--report, repeatable or 'all'):
  terms        search_term_view            -> search-terms.csv
  keywords     keyword_view                -> keywords.csv
  campaigns    campaign + impression share -> campaigns.csv
  conversions  conversion_action + counts  -> conversion-actions.csv

Credentials come from environment variables only (never pass them as arguments):
  GOOGLE_ADS_DEVELOPER_TOKEN  GOOGLE_ADS_CLIENT_ID  GOOGLE_ADS_CLIENT_SECRET
  GOOGLE_ADS_REFRESH_TOKEN    GOOGLE_ADS_CUSTOMER_ID
  GOOGLE_ADS_LOGIN_CUSTOMER_ID  (only when you reach the account through a manager account)
  GOOGLE_ADS_API_VERSION      (default v26; versions retire, check the API release notes)

The script only calls googleAds:search. It never calls a mutate endpoint.

Examples:
  python gaql_pull.py --report all --days 30 --out data/ --dry-run   # print queries, no network
  python gaql_pull.py --report terms --report campaigns --days 30 --out data/
  python gaql_pull.py --report campaigns --start 2026-11-23 --end 2026-11-29 --out week/

Exit codes: 0 ok, 1 API error, 2 bad input or missing credentials.
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

QUERIES = {
    "terms": ("search-terms.csv", """
SELECT search_term_view.search_term, search_term_view.status, campaign.name, ad_group.name,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions, metrics.conversions_value
FROM search_term_view
WHERE segments.date BETWEEN '{start}' AND '{end}'
ORDER BY metrics.cost_micros DESC
LIMIT 5000"""),
    "keywords": ("keywords.csv", """
SELECT ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type, ad_group_criterion.status,
       ad_group_criterion.quality_info.quality_score, campaign.name, ad_group.name,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM keyword_view
WHERE segments.date BETWEEN '{start}' AND '{end}' AND ad_group_criterion.status != 'REMOVED'
ORDER BY metrics.cost_micros DESC"""),
    "campaigns": ("campaigns.csv", """
SELECT campaign.name, campaign.status, campaign.advertising_channel_type, campaign.bidding_strategy_type,
       campaign_budget.amount_micros, campaign.network_settings.target_search_network,
       campaign.network_settings.target_content_network,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions, metrics.conversions_value,
       metrics.search_impression_share, metrics.search_budget_lost_impression_share,
       metrics.search_rank_lost_impression_share
FROM campaign
WHERE segments.date BETWEEN '{start}' AND '{end}' AND campaign.status != 'REMOVED'"""),
    "conversions": ("conversion-actions.csv", """
SELECT conversion_action.name, conversion_action.type, conversion_action.category, conversion_action.status,
       conversion_action.primary_for_goal, conversion_action.counting_type,
       conversion_action.click_through_lookback_window_days, conversion_action.value_settings.default_value
FROM conversion_action
WHERE conversion_action.status != 'REMOVED'"""),
    # counts per action come from a second query: conversion_action has no metrics over a date range
    "_conv_counts": (None, """
SELECT segments.conversion_action_name, metrics.conversions, metrics.all_conversions, metrics.conversions_value
FROM customer
WHERE segments.date BETWEEN '{start}' AND '{end}'"""),
}

ENV = ["GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET",
       "GOOGLE_ADS_REFRESH_TOKEN", "GOOGLE_ADS_CUSTOMER_ID"]


def token():
    data = urllib.parse.urlencode({
        "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"], "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30) as r:
        return json.load(r)["access_token"]


def search(access, query):
    ver = os.environ.get("GOOGLE_ADS_API_VERSION", "v26")
    cid = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
    url = f"https://googleads.googleapis.com/{ver}/customers/{cid}/googleAds:search"
    headers = {"Authorization": f"Bearer {access}", "developer-token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
               "Content-Type": "application/json"}
    if os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"):
        headers["login-customer-id"] = os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"].replace("-", "")
    rows, page = [], None
    while True:
        body = {"query": " ".join(query.split())}
        if page:
            body["pageToken"] = page
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=60) as r:
            j = json.load(r)
        rows += j.get("results", [])
        page = j.get("nextPageToken")
        if not page:
            return rows


def camel(s):
    head, *rest = s.split("_")
    return head + "".join(w.title() for w in rest)


def get(row, field):
    cur = row
    for part in field.split("."):
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(camel(part), cur.get(part, ""))
    return cur


def fields_of(query):
    sel = query.split("SELECT", 1)[1].split("FROM", 1)[0]
    return [f.strip() for f in sel.replace("\n", " ").split(",") if f.strip()]


def write(path, fields, rows, extra=None):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fields + (list(extra[0].keys()) if extra else []))
        for i, r in enumerate(rows):
            vals = [get(r, x) for x in fields]
            w.writerow(vals + (list(extra[i].values()) if extra else []))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="append", choices=["terms", "keywords", "campaigns", "conversions", "all"])
    ap.add_argument("--days", type=int, default=30, help="last N full days (default 30)")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--out", default=".")
    ap.add_argument("--dry-run", action="store_true", help="print the queries, call nothing")
    a = ap.parse_args(argv)
    reports = a.report or ["all"]
    if "all" in reports:
        reports = ["terms", "keywords", "campaigns", "conversions"]
    end = dt.date.fromisoformat(a.end) if a.end else dt.date.today() - dt.timedelta(days=1)
    start = dt.date.fromisoformat(a.start) if a.start else end - dt.timedelta(days=a.days - 1)
    # GAQL has no LAST_90_DAYS literal and date-less metric queries can return 0 rows: always give BETWEEN
    qs = {r: QUERIES[r][1].format(start=start, end=end).strip() for r in reports}
    if "conversions" in reports:
        qs["_conv_counts"] = QUERIES["_conv_counts"][1].format(start=start, end=end).strip()
    if a.dry_run:
        for k, q in qs.items():
            print(f"-- {k} ({start} to {end})\n{q}\n")
        print("dry run: nothing was called")
        return 0
    missing = [e for e in ENV if not os.environ.get(e)]
    if missing:
        print("missing environment variables: " + ", ".join(missing) + " (see references/api-setup.md)", file=sys.stderr)
        return 2
    os.makedirs(a.out, exist_ok=True)
    try:
        access = token()
        counts = {}
        if "_conv_counts" in qs:
            for r in search(access, qs["_conv_counts"]):
                n = get(r, "segments.conversion_action_name")
                c = counts.setdefault(n, {"metrics.conversions": 0.0, "metrics.all_conversions": 0.0, "metrics.conversions_value": 0.0})
                for k in c:
                    c[k] += float(get(r, k) or 0)
        for rep in reports:
            fname, _ = QUERIES[rep]
            rows = search(access, qs[rep])
            fields = fields_of(qs[rep])
            extra = None
            if rep == "conversions":
                extra = [counts.get(get(r, "conversion_action.name"),
                                    {"metrics.conversions": 0, "metrics.all_conversions": 0, "metrics.conversions_value": 0}) for r in rows]
            path = os.path.join(a.out, fname)
            write(path, fields, rows, extra)
            print(f"{rep}: {len(rows)} rows -> {path}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:800]
        print(f"API error {e.code}: {detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"network error: {e.reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
