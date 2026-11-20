# Example: Northwind Plumbing (invented)

A made-up plumbing company with four campaigns and planted problems, so every script has
something to find. No real account, company or person.

| File | Shape | Planted problems |
|---|---|---|
| `search-terms.csv` | UI download with title rows and a Total row | jobs, DIY, parts, cheap and competitor terms with spend and no conversions; one converting "leaking" term |
| `keywords.csv` | UTF-16 tab-separated, like some UI downloads | broad keywords on Maximize clicks, a keyword past 3x target CPA, a duplicate, low Quality Scores |
| `campaigns-month.csv` | campaign report, 30 days | budget-limited campaigns, Display on Search, an enabled campaign with 0 impressions |
| `campaigns-week-prev.csv`, `campaigns-week-curr.csv` | two weeks | conversions to 0 in one campaign while clicks hold |
| `conversion-actions.csv` | conversion summary | dead primary, Ads tag plus GA4 import both primary, careers form primary, lead counted Every |
| `negatives-draft.csv` | a hand-made negatives list | "plumber", "cost" and "free" block converting terms or own keywords |
| `candidates.csv` | output of `ngrams.py --csv` | "toilet" is a trap: its terms never converted, but it blocks the keyword "toilet repair" |

Run the commands in `AGENTS.md` at the repo root to see each script's output on this data.
