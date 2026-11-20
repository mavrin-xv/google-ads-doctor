# Lead paths: <account name>

Fill this with the owner before touching conversion actions. Each row is one way a real
lead reaches the business. The question for every row: which conversion action counts it,
and does it count it once?

| Path | Example | Tracked by (conversion action) | Primary? | Counted | Test done (date, result) |
|---|---|---|---|---|---|
| Call from the ad (call extension) | taps "Call" on the ad | | | One | |
| Call from the site | taps the number on the landing page | | | One | |
| Quote or contact form | submits the form, sees the thank-you page | | | One | |
| Online booking | books a slot | | | One | |
| Chat or messenger | starts a chat from the site | | | One | |
| Purchase | pays online | | | Every, with value | |
| Offline: lead became a paid job | marked won in the CRM | | | One | |

Owner's own count of leads, last 30 days: <number> (source: CRM, call log, inbox)
Ads primary conversions, same 30 days: <number>
Ratio Ads / owner: <number>. Between 0.7 and 1.3 is fine; outside 0.5 to 1.5 is a FAIL in
`conversions_audit.py --owner-leads`.

Not leads (should be secondary if tracked): careers or job application, newsletter, page views,
scroll depth, directions clicks, video views.
