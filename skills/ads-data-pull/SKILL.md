---
name: ads-data-pull
description: Gets the Google Ads data the other google-ads-doctor skills read, either as UI CSV downloads (no access needed beyond a login) or through a read-only Google Ads API pull with credentials from environment variables. Use when someone wants to audit a Google Ads account, says "export my search terms", "pull the campaign report", "I have API access", "the script says missing column", or before running any search-terms, negatives, conversions, structure or weekly check.
---

# Ads data pull

Every check in this pack runs on four files. Get them first, for the same date range.

| File | What it holds | Used by |
|---|---|---|
| `search-terms.csv` | what people typed, cost, conversions | search-terms-audit, negative-keywords |
| `keywords.csv` | your keywords, match type, Quality Score | negative-keywords, structure-audit |
| `campaigns.csv` | bid strategy, budget, impression share, networks | structure-audit, conversion-cleanup, weekly-ads-check |
| `conversion-actions.csv` | every conversion action, primary or not, counting | conversion-cleanup |

## Path A: download from the UI (default)

Follow `references/ui-exports.md` click by click. It lists the exact columns to add before
downloading, because a missing column turns a check into UNKNOWN.

Then check each file reads cleanly:

```bash
python3 scripts/adsreport.py search-terms.csv
```

It prints the header row it found, how each column was mapped and how many total rows it
skipped. Title rows, UTF-16 "CSV (Excel)" files and "Total:" rows are handled.

## Path B: API pull (optional)

Only when the user already has a developer token and OAuth credentials. Setup is in
`references/api-setup.md`. Credentials go in environment variables, never in arguments,
files in the repo or chat.

```bash
python3 scripts/gaql_pull.py --report all --days 30 --out data/ --dry-run   # show queries first
python3 scripts/gaql_pull.py --report all --days 30 --out data/
```

The script only calls `googleAds:search`. It has no write path. Output column names are
the API field names; `adsreport.py` maps them, turns `cost_micros` into money and impression
share fractions into percents.

## Rules

- Same date range for every file. For a weekly check, two equal periods.
- At least 30 days for audits. Under 3 days of data, judge nothing.
- Always scope API metric queries with `segments.date BETWEEN`: there is no `LAST_90_DAYS`
  literal and a query without dates can come back empty.
- Never ask the user to paste tokens into chat. If they do, tell them to rotate it.
- The API campaign query does not return a "Networks" text column, so structure check S09
  shows UNKNOWN on API data. Use a UI campaign export for that one check.

Next: `search-terms-audit` is the usual first audit.
