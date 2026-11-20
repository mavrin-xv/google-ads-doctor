# Contributing

Thanks for helping. Small, tested changes are the easiest to merge.

## Good first contributions

- Header aliases for report columns in other UI languages, with a small sample file.
- A Performance Max search term insights reader (categories, not terms).
- A Shopping or Performance Max structure check set next to S01 to S10.
- An Editor import file that matches the current Editor column names exactly, tested on a
  real import preview.
- More intent classes for `ngrams.py` in other industries (B2B, ecommerce, local services).

## How

1. Open an issue first for anything that changes a verdict rule or a threshold.
2. Keep the scripts stdlib-only and read-only towards the ads account.
3. Change `adsreport.py` in `skills/search-terms-audit/scripts/`, copy it to the other skills.
4. Run the commands in `AGENTS.md` and paste their output in the PR.
5. Plain English. No hype words, no invented numbers. If a number is in the docs, say where it
   came from, and mark working rules as working rules.

## Credit

If your change is based on someone else's method or repo, add it to the Credits section of the
README with the URL and license.
