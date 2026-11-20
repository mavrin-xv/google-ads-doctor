---
name: weekly-ads-check
description: Runs a 15 minute weekly Google Ads check that compares this week with last week per campaign, raises flags in the order to act on them (tracking broke, spend up without conversions, CPA over target, volume collapse, budget loss) and appends a dated entry to a decisions log so each week starts from what was decided. Use when someone says "weekly ads check", "how did ads do this week", "what changed in Google Ads", "conversions suddenly dropped", or wants a repeatable routine for an account.
---

# Weekly ads check

Same routine every week, about 15 minutes, so changes are caught in days instead of at
the end of the month.

## Run

Download the campaign report twice (last 7 days, the 7 days before; see `ads-data-pull`),
then:

```bash
python3 scripts/weekly_check.py campaigns-curr.csv campaigns-prev.csv --target-cpa 60 \
  --log decisions.md
```

Exit 1 when any flag is raised. The log entry has blank `Decision:`, `Why:` and
`Check again on:` lines; fill them with the user before closing the session. Start the log
from `templates/decisions-log.md` at the repo root.

## Flags, in the order to act

| Flag | First move |
|---|---|
| TRACKING | conversions fell to 0 or by 80%+ while clicks held: submit a test lead, check the tag fires, check recent site changes. Do not touch bids until this is cleared |
| SPEND_UP | spend up 25%+ with flat conversions: open the search terms for that campaign (`search-terms-audit`) |
| CPA | over 1.5x target: check terms and keywords; wait if the campaign is in a learning period after a change |
| VOLUME | impressions halved: approvals, budget, billing, bids, policy |
| BUDGET | lost IS budget up 10+ points: see `structure-audit` S06 before raising budget |
| LOW_DATA | under 1x target CPA of spend or under 3 days: no judgement this week |

## The routine

Full checklist in `references/weekly-routine.md`. Short version:

1. Read last week's log entry. Did the change we made do what we expected?
2. Run the script, read flags top down.
3. Search terms for any campaign with SPEND_UP or CPA: new waste patterns since last week.
4. One to three changes, each written in the log with the reason. No more: with several
   changes at once nobody can tell which one worked.
5. Set the date to check each change again (a week for terms and negatives, two weeks for
   bid strategy or goal changes).

## Rules

- Compare equal periods. A 7-day week against a 6-day one creates fake drops.
- Scale winners slowly: about 20 to 30% budget per step, then a week of data.
- Do not judge the last 2 to 3 days: calls and offline imports land late.
