# Conversion actions export: columns

Goals > Conversions > Summary, set the date range, add these columns, download CSV.

| Column | Why the audit needs it |
|---|---|
| Conversion action | name, used for non-sales detection (C05) |
| Conversion source | Website, Calls from ads, Google Analytics 4, Google hosted, Import (C04, C08) |
| Conversion category | Submit lead form, Phone call lead, Purchase (C03, C04, C06) |
| Action optimization | Primary or Secondary; without it most checks are UNKNOWN |
| Count | One or Every (C03) |
| Tracking status | Recording, No recent conversions, Inactive, Unverified (C02) |
| Click-through conversion window | context only |
| Conversions | primary count in the range (C01) |
| All conv. | includes secondary; 0 in both means truly dead (C01) |
| Conv. value | purchase value check (C06) |

API equivalents (from `gaql_pull.py --report conversions`): `conversion_action.name`,
`.type`, `.category`, `.status`, `.primary_for_goal`, `.counting_type`, plus counts from a
second query on `customer` segmented by `segments.conversion_action_name`.

Names in the UI change over time ("Include in Conversions" became "Action optimization").
`adsreport.py` knows both; run `python3 scripts/adsreport.py file.csv` to see the mapping.
