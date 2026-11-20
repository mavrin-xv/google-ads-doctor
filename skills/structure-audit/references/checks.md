# Structure checks

| ID | Check | Needs | Why it matters |
|---|---|---|---|
| S01 | one keyword over 50% of keyword spend | keywords: cost | a single broad head term often hides most of the waste; one change there moves the account |
| S02 | broad match in a campaign without conversion-based bidding | keywords: match type, campaign; campaigns: bid strategy | broad matches loosely and relies on bidding signals; on manual CPC or Maximize clicks it buys loose traffic at full price |
| S03 | keyword 0 conversions at 3x target CPA (FAIL), 1x to 3x (WARN), CPA over 3x target (FAIL) | keywords: cost, conversions | kill rule; below 1x it is noise |
| S04 | same keyword and match type in several ad groups | keywords: ad group | they compete and split data; Google picks one anyway |
| S05 | ad group with over 20 keywords | keywords: ad group | the ad text cannot fit all of them; usually several intents in one group |
| S06 | lost IS budget 15% or more; rank loss bigger than budget loss; rank loss 40% or more | campaigns: lost IS columns | tells "more money" apart from "better ads" |
| S07 | enabled campaign with spend at or over target CPA and 0 conversions | campaigns: status, cost, conversions | check tracking before blaming the campaign |
| S08 | Quality Score 4 or below with spend | keywords: Quality Score | low QS raises CPC; usually ad or landing page mismatch |
| S09 | Search campaign on Display Network or Search Partners | campaigns: networks, type | Display inside Search campaigns is rarely intended; partners vary by account |
| S10 | enabled campaign with 0 impressions | campaigns: status, impressions | stuck: approvals, budget, bids, targeting |

States: PASS ran clean, FAIL fix now, WARN look at it, UNKNOWN the export lacked the column.
Coverage = checks that ran / 10.

## Facts to keep straight

- Lost IS (budget) is a campaign-level number. Do not read it per keyword for budget decisions.
- Bid strategy names: read the name the export gives (for example "Maximize clicks", or
  `TARGET_SPEND` in the API, which is Maximize clicks). Do not map numeric enum codes by hand.
- Performance Max has no keywords and no search IS columns; most checks do not apply to it.
- Quality Score shows "--" when there is too little data. That is UNKNOWN, not a low score.

## Thresholds

3x target CPA, 50% concentration, 20 keywords per ad group, 15% lost IS budget and QS 4 are
working rules. Change them in the script for accounts where they do not fit, and say so in
the report.
