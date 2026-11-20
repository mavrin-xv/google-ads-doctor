# Fix playbook

Each fix: the change, the risk, how to prove it worked.

| Check | Change | Risk | Proof |
|---|---|---|---|
| C01 dead primary | find why it stopped (tag removed, URL changed). If retired, set Secondary | none if retired; if it was the main lead action, bidding loses its signal | non-zero count within 7 days, or Secondary and ignored |
| C02 bad status | fix tag or import; use Tag Assistant or a test lead | none | status turns Recording and the count moves |
| C03 lead counted Every | set Count to One | reported conversions drop; tell the owner before, it is not a performance drop | count closer to the owner's lead count |
| C04 tag + GA4 both primary | keep the Ads tag primary, set the GA4 import Secondary (or the other way, never both) | short dip in reported conversions | primary count stops being about 2x the owner's count |
| C05 non-sales primary | set Secondary | bidding loses volume it thought it had | fewer junk leads within 2 weeks |
| C06 purchase without value | pass the order value in the tag | none | Conv. value non-zero |
| C07 too many primary | keep 1 to 3 real actions primary | fewer reported conversions | CPA reflects real leads |
| C08 local actions primary | set Secondary for lead businesses | big drop in reported conversions | owner count and Ads count converge |
| C09 strategy vs volume | Maximize clicks to Maximize conversions after about 15 to 30 real conversions a month; below about 15, keep it simple and fix tracking first | learning period, a week or two of noisy CPA | CPA after the learning window |
| C10 count vs owner | trace which paths are missing or doubled using the lead paths map | none | ratio between 0.7 and 1.3 |

## Thresholds are working rules

About 30 conversions a month per campaign for target CPA, about 15 to 30 to leave Maximize
clicks and about 60 imported offline conversions in 90 days before making them primary are
practitioner rules, not Google floors. Smaller accounts can still use smart bidding; expect
slower and noisier learning.

## Offline conversions

When the business knows which leads became paying jobs, importing them (by GCLID or enhanced
conversions for leads) is the single biggest quality jump. Start them as Secondary, compare
with the form counts for a few weeks, promote to Primary once the volume is steady.

## Values

Do not put made-up values on lead actions that mix good and bad leads. Either leave values
off, or use real averages per action once offline data shows what a lead is worth.
