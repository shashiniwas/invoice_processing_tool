# Dynamic AI Invoice Processing (Django)

A Django service that ingests invoices of different layouts, extracts structured fields with AI (with fallback parsing), syncs to ERP, and sends email notifications.

## Features
- Browser UI for registration, login, and user dashboard.
- Dashboard invoice uploader (this is where invoices are uploaded from UI).
- Invoice tables segmented into pending, processed, and failed statuses.
- Invoice detail page with extracted fields + invoice file preview/download.
- Upload invoice files through API.
- Dynamic extraction pipeline for many invoice formats.
- AI extraction via OpenAI when configured.
- ERP sync support (mock + HTTP endpoint).
- Email notification on success/failure.
- User registration/login/logout/profile APIs.
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

Then open:
- `http://127.0.0.1:8000/register/` for account creation
- `http://127.0.0.1:8000/login/` for login
- `http://127.0.0.1:8000/dashboard/` for invoice upload and tables

## Web UI
### Where to upload invoice?
Use the **Upload Invoice** section on `/dashboard/`.

### Dashboard
- Pending invoices table
- Processed invoices table
- Failed invoices table
- Click **View** on any row to open the invoice detail page with extracted data + file access.

## API
### Authentication
- `POST /api/invoices/auth/register/` with JSON body:
  - `username`
  - `password`
  - `email` (optional)
- `POST /api/invoices/auth/login/` with JSON body:
  - `username`
  - `password`
- `POST /api/invoices/auth/logout/`
- `GET /api/invoices/auth/profile/`

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
