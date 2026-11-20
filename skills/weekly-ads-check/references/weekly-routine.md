# Weekly routine (15 minutes)

## Before (2 min)
- [ ] Open `decisions.md`, read last week's entry and every "Check again on" date that is due.
- [ ] Download campaign reports for this week and last week, same weekdays.

## Numbers (5 min)
- [ ] `weekly_check.py curr.csv prev.csv --target-cpa <T> --log decisions.md`
- [ ] TRACKING flag? Stop here and test the lead path: submit the form, call the tracked
      number, check the conversion shows within a few hours (or the next day for imports).
- [ ] Compare the week's conversions with the owner's leads for the same days. A widening
      gap means tracking drift.

## Causes (5 min)
- [ ] For each SPEND_UP or CPA campaign: search terms for the week, sorted by cost.
- [ ] New waste patterns go to `negative-keywords` as candidates, checked before upload.
- [ ] Change history (Tools > Change history): did anyone change budgets, bids, ads or goals?

## Decide and log (3 min)
- [ ] At most three changes. Each one with: what, why, expected effect, date to check.
- [ ] Changes are made only after the owner said yes to each.

## Monthly, not weekly
- Full `search-terms-audit` on 30 days.
- `conversion-cleanup` re-run (new forms, new site pages, new imports).
- `structure-audit` with keywords.

## Log entry example

```markdown
## 2026-11-30

Account: spend 1201.70 -> 1315.50 (+9%), conversions 20 -> 7, CPA 60.09 -> 187.93

- TRACKING Search - Emergency: conversions 9 -> 0 with clicks 74 -> 78

Decision: test the quote form and phone tap tag; no bid changes this week
Why: clicks steady, conversions to 0 in one campaign points at tracking
Check again on: 2026-12-02
```
