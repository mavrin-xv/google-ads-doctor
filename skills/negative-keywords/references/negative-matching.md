# How negative keywords match

Source: Google Ads help, "About negative keywords". Re-check it when results look off.

| Negative | Blocks | Does not block |
|---|---|---|
| broad `plumber jobs` | "plumber jobs near me", "jobs for a plumber" | "plumber job", "plumbing jobs" |
| phrase `"plumber jobs"` | "local plumber jobs" | "jobs for a plumber", "plumber job" |
| exact `[plumber jobs]` | "plumber jobs" | "plumber jobs near me" |

What that means in practice:

- **No plurals, no misspellings beyond casing, no synonyms.** `job` and `jobs` are separate
  negatives. The checker lists the other form when it appears in your data.
- **Single-word phrase and broad negatives behave the same.** Phrase only matters from two words.
- **Exact negatives are surgical.** Use them in REVIEW cases where the word also appears in
  converting searches.
- **Negatives match the search, not your keyword.** A negative can block your own keyword's
  traffic; the `--keywords` check catches that.
- **Some symbols are ignored**, and very long negatives (more than 10 words) may not apply.

## Levels

| Level | Use for | Note |
|---|---|---|
| Shared list | themes for the whole account (jobs, DIY, free) | attach it to each Search campaign; new campaigns do not get it automatically |
| Campaign | services one campaign does not sell | |
| Ad group | steering searches to the right ad group | the most fragile level; document why |

Account-level negatives exist too and also apply to Performance Max. Check the current
options in your account, they have changed over time.

## Limits

Google documents caps such as 20 shared negative lists per account, 5,000 negatives per list
and 10,000 negatives per campaign. These change; check the current help page. The checker
warns when a level in your file passes 80% of the list or campaign cap.

## Input file format

```csv
Keyword,Match type,Level
jobs,Phrase,list: Jobs
[how to unclog a drain],Exact,campaign: Search - Drain
free,Broad,campaign: Search - Emergency
```

Match type can be empty when the keyword carries `[ ]` or `" "`. Level is free text; start it
with `list:` or `campaign:` so the upload file fills the right column.
