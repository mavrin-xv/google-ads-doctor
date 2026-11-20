# How it works

Google Ads loses money in four places, and they have to be fixed in a fixed order, because
each one distorts the numbers the next one reads.

1. **Conversion tracking** decides what bidding buys. If a careers form is primary, or one
   lead is counted twice, every CPA in the account is wrong. `conversion-cleanup` goes first.
2. **Search terms** are what you actually pay for. Waste hides in thousands of small terms
   and only shows up when they are grouped by the words they share. `search-terms-audit`.
3. **Negatives** stop the waste, and a wrong one silently blocks buyers. `negative-keywords`
   checks every negative against converting terms and your own keywords before upload.
4. **Structure** decides where budget and bids go: broad match on the wrong bidding, keywords
   past the kill line, budget versus rank limits. `structure-audit`.

After the first pass, `weekly-ads-check` keeps it from drifting back, and the decisions log
keeps the reasons.

## Data flow

```text
UI downloads (CSV, TSV, UTF-16)  ┐
                                 ├─► adsreport.py (header aliases, number parsing) ─► each audit script
gaql_pull.py (API, read-only)    ┘

conversion-actions.csv ─► conversions_audit.py ─► fix list (C01..C10)
search-terms.csv ─► ngrams.py ─► candidates.csv ─► negatives_check.py (+ keywords.csv) ─► upload.csv
campaigns.csv + keywords.csv ─► structure_audit.py ─► S01..S10 + coverage
campaigns (this week, last week) ─► weekly_check.py ─► flags + decisions.md entry
```

## Why a shared parser

Google Ads exports change shape: a title row and date row above the header, totals at the
bottom, UTF-16 tab-separated files from some download options, "1,234.56" numbers, "--" for
no data, percentages like "< 10%", and API column names (`metrics.cost_micros`) instead of
UI ones. `adsreport.py` handles these once. It is copied into each skill's `scripts/` folder
so every skill works on its own after install. The copies must stay identical; `AGENTS.md`
has the check.

Run `python3 adsreport.py yourfile.csv` to see which columns it recognised. When a column is
missing, the audits mark the checks that need it UNKNOWN instead of guessing.

## What the scripts never do

They do not write to the Google Ads account. `gaql_pull.py` only calls the search endpoint.
Every change is a proposal the account owner approves and makes, in the UI or Editor, one at
a time, with a line in the decisions log.
