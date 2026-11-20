# AGENTS.md

Notes for coding agents (Claude Code, Codex, Cursor, others) working on this repository.

## What this is

A skill pack that audits Google Ads accounts from report exports. Six skills in `skills/`,
each with SKILL.md, `references/` and `scripts/`. Scripts are Python 3.8+ standard library
only. Nothing in the repo writes to an ads account; `gaql_pull.py` only reads.

## Layout

- `skills/<name>/scripts/adsreport.py`: the shared report parser (header aliases, encodings,
  number formats, micros, API column names). The same file sits in all six skills so each
  skill works alone after install. Edit the copy in `search-terms-audit`, then copy it to
  the other five.
- `examples/northwind-plumbing/`: invented account data with planted problems.
- `templates/`: decisions log and lead paths map. `docs/how-it-works.md`: data flow.

## Rules

- SKILL.md frontmatter has only `name` (same as the folder) and `description` (under 1024
  characters, says what and "Use when"). Bodies under 500 lines; detail goes to `references/`.
- A new column goes into `ALIASES` in `adsreport.py` with both the UI name and the API name.
- A check that lacks its columns returns UNKNOWN. Never guess a missing value as 0.
- Thresholds are working rules. When you change one, change the SKILL.md and reference text
  that quotes it.
- No mutate calls, no credentials in arguments or files. Credentials come from environment
  variables only.
- Examples use invented businesses only.
- Run before you finish:

```bash
S=skills; E=examples/northwind-plumbing
for d in negative-keywords conversion-cleanup structure-audit weekly-ads-check ads-data-pull; do
  cmp $S/search-terms-audit/scripts/adsreport.py $S/$d/scripts/adsreport.py; done
python3 $S/search-terms-audit/scripts/ngrams.py $E/search-terms.csv --target-cpa 60 --brand northwind --competitors acme
python3 $S/negative-keywords/scripts/negatives_check.py $E/candidates.csv --terms $E/search-terms.csv --keywords $E/keywords.csv
python3 $S/negative-keywords/scripts/negatives_check.py $E/negatives-draft.csv --terms $E/search-terms.csv --keywords $E/keywords.csv
python3 $S/conversion-cleanup/scripts/conversions_audit.py $E/conversion-actions.csv --campaigns $E/campaigns-month.csv --owner-leads 34
python3 $S/structure-audit/scripts/structure_audit.py --campaigns $E/campaigns-month.csv --keywords $E/keywords.csv --target-cpa 60
python3 $S/weekly-ads-check/scripts/weekly_check.py $E/campaigns-week-curr.csv $E/campaigns-week-prev.csv --target-cpa 60
python3 $S/ads-data-pull/scripts/gaql_pull.py --report all --dry-run
```

Expected: `cmp` silent; ngrams exit 0 (11 NEGATIVE rows, 1 REVIEW); negatives_check on
candidates exit 1 (only "toilet" HARMFUL), on the draft exit 1 (plumber, cost, free HARMFUL);
conversions_audit exit 1 (8 FAIL rows); structure_audit exit 1 (S02, S03 FAIL, coverage
100%); weekly_check exit 1 (TRACKING first); gaql_pull dry run exit 0.
