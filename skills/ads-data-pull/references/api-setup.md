# API setup (read-only use)

You need five things. Getting them is a one-time job and Google's own guides are the
source of truth; this page is the checklist.

1. **Developer token.** Google Ads manager account > Admin > API Center. A test-level token
   only works on test accounts; real accounts need Basic access, which Google reviews.
2. **OAuth client.** Google Cloud console > a project > enable "Google Ads API" > OAuth
   consent screen > Credentials > OAuth client ID (Desktop app). Gives a client ID and secret.
3. **Refresh token.** Run Google's OAuth flow once with scope
   `https://www.googleapis.com/auth/adwords` (the official client libraries ship a helper
   script for this). If the OAuth consent screen is still in "Testing" status, refresh tokens
   expire after 7 days; publish the app (internal or production) to keep one working.
4. **Customer ID.** The 10-digit account number, dashes allowed.
5. **Login customer ID.** Only when access goes through a manager account: the manager's ID.

Put them in your shell or an untracked `.env` file you source:

```bash
export GOOGLE_ADS_DEVELOPER_TOKEN=...
export GOOGLE_ADS_CLIENT_ID=...
export GOOGLE_ADS_CLIENT_SECRET=...
export GOOGLE_ADS_REFRESH_TOKEN=...
export GOOGLE_ADS_CUSTOMER_ID=...
export GOOGLE_ADS_LOGIN_CUSTOMER_ID=...      # optional
export GOOGLE_ADS_API_VERSION=v26            # optional; versions retire, check release notes
```

`.gitignore` in this repo already ignores `.env` and `data/`.

## What the script calls

- `POST https://oauth2.googleapis.com/token` to swap the refresh token for an access token.
- `POST https://googleads.googleapis.com/<version>/customers/<id>/googleAds:search` with a
  GAQL query, following `nextPageToken` until done.

Headers: `Authorization: Bearer`, `developer-token`, and `login-customer-id` when set.

## Errors you will see

| Error | Usually means |
|---|---|
| 401 / UNAUTHENTICATED | refresh token revoked or client ID and secret from another project |
| DEVELOPER_TOKEN_NOT_APPROVED | test token used on a real account |
| USER_PERMISSION_DENIED | missing or wrong login customer ID for a manager-linked account |
| 404 on the URL | API version retired: set GOOGLE_ADS_API_VERSION to a current one |
| 0 rows | date range has no traffic, or the query lost its date filter |

## Changes are not done by script

This pack reads only. When an audit says "set X secondary" or "add these negatives", make
the change in the UI or Editor after the owner says yes to that exact change. If you build
your own write path, keep the same rule: propose, get a yes per change, re-read the account.
