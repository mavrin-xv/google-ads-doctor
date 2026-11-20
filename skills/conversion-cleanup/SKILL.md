---
name: conversion-cleanup
description: Audits Google Ads conversion actions so Smart Bidding optimises for real leads and sales, catching dead primary actions, double counting (Ads tag plus GA4 import), leads counted Every, careers or newsletter forms set primary, local actions inflating conversions and bid strategies that do not match conversion volume. Use when someone says "my conversions look too high", "conversions dropped to zero", "Google says 90 leads but we got 30", "which conversions should be primary", "clean up conversion actions", or before changing bid strategy.
---

# Conversion cleanup

Bidding buys more of whatever is primary. If a careers form, a directions click and a
double-counted GA4 import are primary, the account gets very good at buying those.

## Step 1: map the real lead paths

Before any export, ask the owner how leads actually arrive and fill
`templates/lead-paths.md`: calls from ads, calls from the site, forms, bookings, chat,
walk-ins. Ask for their own lead count for the last 30 days. That count is the ground truth
the account is compared with.

## Step 2: audit

```bash
python3 scripts/conversions_audit.py conversion-actions.csv --campaigns campaigns.csv \
  --days 30 --owner-leads 34
```

Columns needed are in `references/export-columns.md`. Checks C01 to C10 return FAIL, WARN,
UNKNOWN or PASS; exit 1 on any FAIL.

## Step 3: propose fixes, one by one

Use `references/fix-playbook.md`. For each FAIL write the exact change ("set Careers -
application sent to Secondary") and why. Ask for a yes per change. Never use "Apply all" on
the Recommendations page.

Order: fix what makes the count wrong first (C04 duplicates, C05 non-sales, C03 counting,
C08 local actions), then dead and broken actions (C01, C02), then bid strategy (C09).
Bid strategy changes come last because they depend on a correct count.

## Step 4: prove it

A green "Recording conversions" status is not proof. Proof is data:

- Within 7 days of a tag fix, the action shows a non-zero count that roughly matches the
  owner's leads for the same days.
- After changing primary actions, re-read the account. In the API,
  `customer_conversion_goal.biddable` is not derived from `primary_for_goal`; a goal can stay
  biddable after the action went secondary.
- Log the change in the decisions log with the date. Smart bidding needs one to two weeks
  to settle after a goal change; do not judge CPA in that window.

## Rules

- Do not delete conversion actions. Removal cannot be undone and history disappears from
  reports. Set them secondary.
- Primary means a real lead or sale. Everything else is secondary, observed but not bid on.
- Leads count One per click. Purchases count Every.
- When conversions drop to 0 overnight while clicks hold, it is almost always tracking
  (a site change, a form plugin update, consent settings). Send the user to tracking-doctor
  style checks before touching bids.
