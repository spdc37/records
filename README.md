# My records collection

## Test locally

With Python 3.10+ and requests module installed:
```bash
export GOOGLE_SERVICE_ACCOUNT_JSON=$(cat google-sa-key.json)
export SPREADSHEET_ID="someId"
python fetch_sheets.py
python -m http.server 8000
```
