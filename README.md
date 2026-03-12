# Dynamic AI Invoice Processing (Django)

A Django service that ingests invoices of different layouts, extracts structured fields with AI (with fallback parsing), syncs to ERP, and sends email notifications.

## Features
- Upload invoice files through API.
- Dynamic extraction pipeline for many invoice formats.
- AI extraction via OpenAI when configured.
- ERP sync support (mock + HTTP endpoint).
- Email notification on success/failure.
- Admin UI for monitoring processed invoices.

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```

## API
### Ingest invoice
`POST /api/invoices/`
- multipart fields:
  - `source_name` (string)
  - `file` (file)

### Get invoice result
`GET /api/invoices/<invoice_id>/`

## Configuration
Set environment variables:
- `OPENAI_API_KEY`: enables AI extraction with OpenAI.
- `ERP_PROVIDER`: `mock` (default) or `http`.
- `ERP_ENDPOINT`: ERP URL used when `ERP_PROVIDER=http`.
- `NOTIFICATION_EMAIL`: recipient for processing notifications.
- `EMAIL_BACKEND`: defaults to console backend.
