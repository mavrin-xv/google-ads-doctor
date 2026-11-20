---
name: structure-audit
description: Audits a Google Ads account's structure from campaign and keyword exports with ten checks that each return pass, fail, warn or unknown, covering spend concentration, broad match without smart bidding, keywords over 3x target CPA with no conversions, duplicate keywords, oversized ad groups, impression share lost to budget versus rank, Quality Score, Display on Search and stuck campaigns. Use when someone asks for a "Google Ads audit", "is my account set up right", "should I raise the budget", "why is this campaign not spending", or takes over an account.
---

# Structure audit

Answers one question: where does the account setup itself lose money, apart from bad
search terms and bad conversion tracking (those have their own skills).

## Run

```bash
python3 scripts/structure_audit.py --campaigns campaigns.csv --keywords keywords.csv --target-cpa 60
```

Each check S01 to S10 gets a state. The header shows evidence coverage: the share of checks
that had their columns. 80% or more is a solid read, 60 to 79% a partial one, under 60% a
guess; say which in the report. What each check means and why is in `references/checks.md`.

## Order of work

1. Run `conversion-cleanup` first if it has not been run. Every CPA here is only as true as
   the conversion count. If conversions are inflated, S03 and S07 under-report waste.
2. FAIL rows: S03 (keywords past 3x target CPA), S02 (broad on manual or click bidding),
   S07 (campaigns spending with 0 conversions), S01 (one keyword carrying the account).
3. WARN rows that cost money now: S06 budget vs rank, S09 Display on Search.
4. Hygiene: S04 duplicates, S05 large ad groups, S08 Quality Score, S10 stuck campaigns.

## Judge only with enough data

- A keyword or campaign is judged after it spent about 2x target CPA. Below that, 0
  conversions is often luck.
- Never judge under 3 days of data, and never the last 2 to 3 days alone: calls and offline
  imports land late.

## Budget questions

"Should we spend more?" is S06:

- Lost IS (budget) 15% or more and CPA at or under target: more budget should buy more
  leads at a similar cost. Raise in steps of about 20 to 30% a day at most, judge after a week.
- Lost IS (rank) bigger than budget loss: more money buys the worse auctions. Fix ad
  relevance, landing page and bids first.
- Budget loss with CPA over target: fix conversions, terms and keywords before adding money.

## Small budgets

On small budgets, one well-built campaign usually beats many thin ones: smart bidding needs
volume in one place, and splitting by town or service starves each part. Suggest merging
before suggesting new campaigns.

## Report

A table sorted FAIL, WARN, UNKNOWN, PASS with the fix per row, the coverage band, and the
three changes worth the most money. Every change is a proposal for the owner to approve.
