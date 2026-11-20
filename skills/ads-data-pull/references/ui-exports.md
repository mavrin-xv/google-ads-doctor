# UI exports, click by click

Google moves menus around. If a path below no longer matches, search the Google Ads help
for the report name; the column names matter more than the path.

Set the date range first (top right), 30 days or more for audits. Then for each report:
Columns icon > Modify columns > add the columns below > Apply > Download icon > CSV.
"CSV (Excel)" is fine too: it is UTF-16 with tabs and the reader handles it.

## Search terms (`search-terms.csv`)

Campaigns > Insights and reports > Search terms (older UI: Keywords > Search terms).

Columns: Search term, Match type, Added/Excluded, Campaign, Ad group, Clicks, Impr., Cost,
Conversions. Optional: Conv. value, Cost / conv.

Performance Max search terms live in a separate insights view and are grouped into
categories, so they are not in this report.

## Keywords (`keywords.csv`)

Campaigns > Audiences, keywords and content > Search keywords.

Columns: Keyword, Match type, Campaign, Ad group, Status, Clicks, Impr., Cost, Conversions,
Quality Score.

## Campaigns (`campaigns.csv`)

Campaigns > Campaigns.

Columns: Campaign, Campaign type, Campaign status, Bid strategy type, Budget, Networks,
Clicks, Impr., Cost, Conversions, Search impr. share, Search lost IS (rank),
Search lost IS (budget).

For the weekly check download it twice: last 7 days and the 7 days before.

## Conversion actions (`conversion-actions.csv`)

Goals > Conversions > Summary.

Columns: Conversion action, Conversion source, Conversion category, Action optimization
(Primary / Secondary), Count (One / Every), Tracking status, Click-through conversion window,
Conversions, All conv., Conv. value.

## Negatives (`negatives.csv`)

Tools > Shared library > Negative keyword lists, and each campaign's Negative keywords tab.
Or write the file by hand: columns `Keyword, Match type, Level`, where Level is
`list: <name>` or `campaign: <name>`. `[x]` means exact and `"x"` phrase if Match type is empty.
