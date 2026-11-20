---
name: negative-keywords
description: Checks negative keyword lists before they go live by simulating exact, phrase and broad negative matching against real search terms and your own keywords, flags negatives that would block converting searches or your keywords, lists missing plural forms, measures how much waste the list covers and writes an Editor-style upload file. Use when someone says "add these negatives", "audit my negative keyword lists", "did a negative block my leads", "why did conversions drop after I added negatives", or after search-terms-audit produced candidates.
---

# Negative keywords

A bad negative is worse than a missing one: waste costs a few dollars, a blocked buyer
costs the sale and never shows up in any report. This skill checks both sides.

## Inputs

- The negatives to check: `candidates.csv` from `search-terms-audit`, the account's current
  lists, or a hand-written file (`Keyword, Match type, Level`; see
  `references/negative-matching.md`).
- `search-terms.csv` and `keywords.csv` for the same account.

## Run

```bash
python3 scripts/negatives_check.py candidates.csv --terms search-terms.csv \
  --keywords keywords.csv --editor upload.csv
```

Exit 1 means at least one HARMFUL negative. `upload.csv` gets only the negatives that passed.

## Read the flags

| Flag | Do |
|---|---|
| HARMFUL: blocks converting term(s) | remove it, or narrow it: a longer phrase, or exact on the bad terms |
| HARMFUL: blocks your keyword(s) | remove it; you are bidding and blocking the same search |
| NO_EFFECT in this report | fine as prevention; check the spelling |
| Add forms | negatives do not cover plurals; add the listed forms if the meaning is the same |

## Rules

1. Match types work differently for negatives: no close variants, no synonyms, no plurals.
   Broad negative = all words present in any order. Phrase = words in that order. Exact =
   the whole search, nothing more. Details in `references/negative-matching.md`.
2. Put recurring themes (jobs, DIY, free) in a shared list attached to every Search campaign.
   Put campaign-specific ones on the campaign. Ad group negatives only to route traffic
   between ad groups.
3. Audit existing lists too, not only new candidates. Old "brand protect" or "cost" negatives
   often block today's best searches.
4. Show the user the table and the HARMFUL rows first. Upload only after a yes for the list.
5. After upload, check the next weekly report: spend on the blocked patterns should go to
   about 0 and conversions should hold. If conversions drop, a negative is the first suspect.

The upload file follows Editor's column idea, but Editor versions name columns differently.
Map the columns on import and check the preview before posting.
