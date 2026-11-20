#!/usr/bin/env python3
"""adsreport: read Google Ads report exports (UI download, Editor export or API CSV).

Shared by every script in this pack. Each skill ships its own identical copy so the
skills can be installed one by one; keep the copies identical (AGENTS.md has the cmp check).

What it handles, because real exports break naive CSV readers:
  * title rows above the header ("Search terms report", "November 1, 2026 - ...")
  * UTF-16 tab-separated files (the UI "CSV (Excel)" download) and UTF-8 with BOM
  * "Total: Account", "Total: Campaigns" summary rows at the bottom
  * numbers like "1,234.56", "$12.40", "12.5%", "< 10%", "--", " -- "
  * API field names (metrics.cost_micros, search_term_view.search_term) next to UI names
  * cost given in micros (column name contains "micros"): divided by 1,000,000
  * API impression share given as a fraction (0.395): turned into a percent (39.5)

Usage as a library:
    from adsreport import read_report, num
    rows, info = read_report("terms.csv")   # rows: list of dicts with canonical keys

Usage as a tool (prints what it detected, useful when a script says "missing column"):
    python adsreport.py report.csv
"""
import csv
import io
import re
import sys

# canonical key -> accepted header spellings (lowercase, stripped). First match wins.
ALIASES = {
    "term": ["search term", "search_term_view.search_term", "campaign_search_term_view.search_term", "search terms", "query"],
    "campaign": ["campaign", "campaign.name", "campaign name"],
    "campaign_type": ["campaign type", "campaign.advertising_channel_type", "advertising channel type"],
    "campaign_status": ["campaign status", "campaign.status"],
    "ad_group": ["ad group", "ad_group.name", "ad group name"],
    "keyword": ["keyword", "search keyword", "ad_group_criterion.keyword.text", "keyword text", "negative keyword"],
    "match_type": ["match type", "search keyword match type", "keyword match type", "ad_group_criterion.keyword.match_type", "criterion type"],
    "term_match_type": ["search terms match type", "search term match type", "segments.search_term_match_type"],
    "added_excluded": ["added/excluded", "search_term_view.status", "status (search term)"],
    "status": ["status", "keyword status", "ad group status", "ad_group_criterion.status"],
    "level": ["level", "list", "shared set", "negative keyword list", "shared set name"],
    "impr": ["impr.", "impressions", "metrics.impressions", "impr"],
    "clicks": ["clicks", "metrics.clicks"],
    "cost": ["cost", "metrics.cost_micros", "cost (converted currency)", "spend", "cost_micros"],
    "conv": ["conversions", "metrics.conversions", "conv."],
    "all_conv": ["all conv.", "metrics.all_conversions", "all conversions"],
    "conv_value": ["conv. value", "conversion value", "metrics.conversions_value", "conversions value"],
    "qs": ["quality score", "qual. score", "ad_group_criterion.quality_info.quality_score"],
    "bid_strategy": ["bid strategy type", "campaign.bidding_strategy_type", "bid strategy", "bidding strategy type"],
    "budget": ["budget", "campaign_budget.amount_micros", "daily budget", "budget amount"],
    "is": ["search impr. share", "metrics.search_impression_share", "search impression share"],
    "lost_is_budget": ["search lost is (budget)", "metrics.search_budget_lost_impression_share"],
    "lost_is_rank": ["search lost is (rank)", "metrics.search_rank_lost_impression_share"],
    "networks": ["networks", "campaign.network_settings", "network"],
    "conv_action": ["conversion action", "conversion_action.name", "segments.conversion_action_name", "conversion name", "name"],
    "conv_source": ["conversion source", "source", "conversion_action.origin", "origin", "type", "conversion_action.type"],
    "conv_category": ["conversion category", "category", "goal", "conversion_action.category", "conversion goal"],
    "optimization": ["action optimization", "primary/secondary", "conversion_action.primary_for_goal", "primary for goal", "optimization"],
    "include": ["include in \"conversions\"", "include in conversions", "conversion_action.include_in_conversions_metric"],
    "count_type": ["count", "counting type", "conversion_action.counting_type", "counting"],
    "tracking_status": ["tracking status", "conversion_action.status", "action status"],
    "window": ["click-through conversion window", "click-through window", "conversion_action.click_through_lookback_window_days", "conversion window"],
    "value_setting": ["value", "default value", "conversion_action.value_settings.default_value", "value settings"],
    "attribution": ["attribution model", "conversion_action.attribution_model_settings.attribution_model"],
    "date": ["day", "date", "segments.date", "week"],
}
_LOOKUP = {}
for _k, _names in ALIASES.items():
    for _n in _names:
        _LOOKUP.setdefault(_n, _k)

MONEY_KEYS = {"cost", "conv_value", "budget"}


def _norm_header(h):
    return re.sub(r"\s+", " ", (h or "").replace("﻿", "").strip().strip('"').lower())


def num(v, default=0.0):
    """Parse a report number. '--', '' and ' -- ' give `default`. '< 10%' gives 10.0."""
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "").replace(" ", "")
    if s in ("", "--", "-", "n/a", "N/A", "null", "None"):
        return default
    s = s.lstrip("<>")
    s = re.sub(r"[^0-9.,\-eE]", "", s)
    if s.count(",") and s.count("."):
        s = s.replace(",", "")
    elif s.count(",") == 1 and len(s.split(",")[1]) != 3:
        s = s.replace(",", ".")      # decimal comma, e.g. "12,5"
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return default


def _decode(raw):
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def read_report(path, need=()):
    """Return (rows, info). rows are dicts keyed by canonical names (plus 'raw').

    need: canonical keys that must exist; missing ones raise SystemExit with a clear message.
    info: {'columns': {canonical: original header}, 'skipped_totals': n, 'header_row': i,
           'unknown_columns': [...], 'micros': bool}
    """
    with open(path, "rb") as f:
        text = _decode(f.read())
    lines = text.splitlines()
    sample = "\n".join(lines[:15])
    delim = "\t" if sample.count("\t") > sample.count(",") else ","
    table = list(csv.reader(io.StringIO(text), delimiter=delim))

    header_i = None
    for i, row in enumerate(table[:30]):
        hits = sum(1 for c in row if _norm_header(c) in _LOOKUP)
        if hits >= 2:
            header_i = i
            break
    if header_i is None:
        raise SystemExit(f"{path}: no header row found in the first 30 lines "
                         f"(expected columns like Search term, Campaign, Cost, Clicks)")

    header = table[header_i]
    colmap, unknown, micros = {}, [], False
    for j, h in enumerate(header):
        key = _LOOKUP.get(_norm_header(h))
        if key and key not in colmap:
            colmap[key] = j
            if key == "cost" and "micros" in _norm_header(h):
                micros = True
        elif not key and h.strip():
            unknown.append(h.strip())
    share_keys = [k for k in ("is", "lost_is_budget", "lost_is_rank")
                  if k in colmap and _norm_header(header[colmap[k]]).startswith("metrics.")]
    budget_micros = "micros" in _norm_header(header[colmap["budget"]]) if "budget" in colmap else False

    missing = [k for k in need if k not in colmap]
    if missing:
        raise SystemExit(f"{path}: missing column(s) {', '.join(missing)}. "
                         f"Found: {', '.join(h for h in header if h.strip())}. "
                         f"Add the column in the Google Ads table before downloading, "
                         f"or run `python adsreport.py {path}` to see what was detected.")

    rows, totals = [], 0
    for row in table[header_i + 1:]:
        if not row or not any(c.strip() for c in row):
            continue
        first = (row[0] if row else "").strip().lower()
        if first.startswith("total") or any(c.strip().lower().startswith("total:") for c in row[:3]):
            totals += 1
            continue
        rec = {"raw": row}
        for key, j in colmap.items():
            rec[key] = row[j].strip() if j < len(row) else ""
        if micros and "cost" in rec:
            rec["cost"] = num(rec["cost"]) / 1_000_000
        if budget_micros and "budget" in rec:
            rec["budget"] = num(rec["budget"]) / 1_000_000
        for key in share_keys:
            if rec.get(key) not in (None, "", "--"):
                rec[key] = num(rec[key]) * 100
        rows.append(rec)
    info = {"columns": {k: header[j] for k, j in colmap.items()}, "skipped_totals": totals,
            "header_row": header_i, "unknown_columns": unknown, "micros": micros}
    return rows, info


def norm_text(s):
    """Lowercase, collapse spaces, drop punctuation Google ignores in keywords."""
    s = (s or "").lower().strip()
    s = re.sub(r"^[\[\"+]+|[\]\"]+$", "", s)
    s = re.sub(r"[^\w\s&'-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def match_type_of(raw_kw, declared=""):
    """Return (text, 'exact'|'phrase'|'broad') from '[x]', '"x"', 'x' or a declared type."""
    t = (raw_kw or "").strip()
    d = (declared or "").lower()
    if t.startswith("[") and t.endswith("]"):
        return norm_text(t[1:-1]), "exact"
    if t.startswith('"') and t.endswith('"'):
        return norm_text(t[1:-1]), "phrase"
    for m in ("exact", "phrase", "broad"):
        if m in d:
            return norm_text(t), m
    return norm_text(t), "broad"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Show how a Google Ads export is read: header row, mapped columns, row count.")
    ap.add_argument("report")
    a = ap.parse_args(argv)
    rows, info = read_report(a.report)
    print(f"header on line {info['header_row'] + 1}, {len(rows)} data rows, "
          f"{info['skipped_totals']} total rows skipped, cost in micros: {info['micros']}")
    for k, h in info["columns"].items():
        print(f"  {k:16} <- {h}")
    if info["unknown_columns"]:
        print("  not used: " + ", ".join(info["unknown_columns"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
