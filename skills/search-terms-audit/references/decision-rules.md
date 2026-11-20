# Decision rules for search terms

These are working rules, not Google rules. Tune the thresholds to the account.

## When a pattern has enough data

- Judge a term or n-gram only after it spent about 1x target CPA. Below that, 0 conversions is
  normal noise: at a 10% conversion rate, 5 clicks with no lead happen about 59% of the time.
- 2x to 3x target CPA with 0 conversions is a strong signal. Over 3x is the kill line used in
  `structure-audit` (S03) for keywords.
- Never judge data under 3 days old: conversions arrive late (calls, offline imports).

## N-grams before single terms

Most accounts have thousands of terms that each spent a few dollars. One by one, none crosses
the threshold. Grouped by the words they share, "jobs", "how to" and "for sale" show up as the
real leak. That is why the script ranks n-grams by share of 0-conversion spend first.

Shorter n-grams that cover the same terms win: if "jobs" already covers "plumber jobs" and
"plumbing jobs near me", propose "jobs" once. The script hides the longer ones in the text
report (they stay in `--json`).

## Classes that are usually waste for a local service business

| Class | Typical words | Usually |
|---|---|---|
| jobs | jobs, careers, hiring, salary, apprenticeship, course | waste: they want to work for you |
| diy | how to, diy, tutorial, video | waste for emergency services, maybe content for others |
| product | for sale, parts, buy, rental, supply | waste for service businesses, gold for shops |
| cheap_free | cheap, free, discount | mixed: "free estimate" often converts |
| research | reviews, vs, best, what is | mixed: early stage, read the terms |
| competitor | other company names | owner decides; often low conversion rate, sometimes worth it |

## What the report cannot see

- Searches you never paid for: a negative can still block a good search that has not
  happened yet. That is what `negatives_check.py --keywords` partly covers.
- Performance Max search terms (separate insights view, grouped into categories).
- Terms Google hides for privacy: the report total is lower than campaign spend. If the gap
  is large, say so; the audit covers only the visible part.

## Logging decisions

For every candidate the user accepts or rejects, write one line in the decisions log
(`templates/decisions-log.md` at the repo root): the word, the verdict, why. Next month's audit
starts by reading it, so a rejected word is not proposed again.
