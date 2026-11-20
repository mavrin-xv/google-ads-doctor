---
name: search-terms-audit
description: Finds where Google Ads search spend leaks by mining the search terms report into 1 to 3 word n-grams, intent classes (jobs, DIY, product shoppers, cheap or free, competitors) and ranked negative keyword candidates with the spend behind each. Use when someone asks "where is my ad money going", "which searches are wasting budget", "mine my search terms", "find negative keywords", "my CPA is too high", or pastes a search terms report.
---

# Search terms audit

Goal: a short list of word patterns that cost money and never convert, with proof, ready
for `negative-keywords` to check before anything goes live.

## Inputs

- `search-terms.csv` for 30 days or more (see `ads-data-pull`).
- A target CPA: what one lead or sale may cost. Ask for it. If the user has none, the script
  uses the account CPA, which is weaker; say so in the report.
- Brand words (never negated) and competitor names (grouped, decision left to the user).

## Run

```bash
python3 scripts/ngrams.py search-terms.csv --target-cpa 60 --brand "northwind" \
  --competitors "acme rooter" --csv candidates.csv
```

Output: account summary, n-gram table with a verdict per row, intent classes, top
non-converting terms. `--csv` writes the NEGATIVE rows (plus plural or singular forms seen
in the data) in the format `negatives_check.py` reads. `--json` for further processing.

## Read the verdicts

| Verdict | Means | Do |
|---|---|---|
| NEGATIVE | 0 conversions, spend at or over target CPA, no converting term contains it | candidate, after reading its example terms |
| REVIEW | waste is real but converting terms share the word | negate the bad full terms as exact, not the word |
| WATCH | 0 conversions, spend under target CPA | wait for data, do not negate on this alone |

Rules in `references/decision-rules.md`. The short version:

1. Read every candidate's example terms before proposing it. A single word like "toilet" can
   be waste in one account and a service you sell in another; the script cannot know that.
2. One converting term inside an n-gram makes it REVIEW, never NEGATIVE.
3. Intent classes are pattern matches. "cheap", "free" and "reviews" often convert.
4. Competitor terms are a business decision. Show the spend and conversions, let the owner pick.
5. Already-excluded terms are skipped so the same waste is not counted twice.

## Report to the user

Lead with the money: spend on 0-conversion terms and how much of it the NEGATIVE rows
explain. Then a table of candidates with example terms, then REVIEW items with the exact
terms to negate. End with the next step: run `negative-keywords` on `candidates.csv` with the
keyword report, so nothing blocks a keyword you bid on.

Never add negatives to the account from this skill. Proposals only.
