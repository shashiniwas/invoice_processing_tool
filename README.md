# Dynamic AI Invoice Processing (Django)

A Django service that ingests invoices of different layouts, extracts structured fields with Mistral AI (with rule fallback), syncs to ERP, and sends email notifications.

## Features
- Browser UI for registration, login, and user dashboard.
- Dashboard invoice uploader (this is where invoices are uploaded from UI).
- Invoice list switcher buttons to show only one table at a time (Pending / Processed / Failed).
- Invoice detail page with PDF.js preview (left), extracted fields (right), zoom in/out controls, extracted table rendering, and diagnostics.
- Upload invoice files through API.
- Dynamic extraction pipeline for many invoice formats.
- Digital PDF text/table extraction via pdfplumber.
- Scanned PDF extraction via docling.
- AI field population via Mistral AI when configured.
- ERP sync support (mock + HTTP endpoint).
- Email notification on success/failure.
- User registration/login/logout/profile APIs.
- Admin UI for monitoring processed invoices.
- Multi-level approval workflows (admin-created) with initiator/approver queues.
- Workflow-level field and table visibility controls.
- Rejection with mandatory remarks and bounce-back to previous approval level.
- Notification bell feed for pending approvals and rejected returns.

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

### Why fields may not populate for some invoices
- The app now extracts text/tables from:
  - text-like files (`.txt`, `.csv`, `.json`, `.xml`, `.html`)
  - digital PDFs using `pdfplumber`
  - scanned PDFs using `docling` OCR pipeline
- If docling is unavailable in your runtime, scanned PDF extraction can still fail and fallback to minimal parsing.
- Invoice detail now shows extraction diagnostics and text preview used by parser.

### Dashboard
- Pending invoices table
- Processed invoices table
- Failed invoices table
- Switch between tables using the three buttons (only one table is visible at a time)
- Click **View** on any row to open invoice detail.

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
- `MISTRAL_API_KEY`: enables AI extraction with Mistral AI.
- `MISTRAL_MODEL`: defaults to `mistral-small-latest`.
- `ERP_PROVIDER`: `mock` (default) or `http`.
- `ERP_ENDPOINT`: ERP URL used when `ERP_PROVIDER=http`.
- `NOTIFICATION_EMAIL`: recipient for processing notifications.
- `EMAIL_BACKEND`: defaults to console backend.


## Approval workflow
- Only admin users can create workflows at `/dashboard/workflows/create/`.
- Workflow includes multiple approver levels (comma-separated usernames in order).
- Admin users should not be part of approval chain; only normal users are accepted as approvers.
- Initiator queues:
  - Pending
  - Sent for Approval
  - Rejected
- Approver queues:
  - Pending Approval
  - Approved
  - Rejected
- Rejection requires remarks and sends invoice back to previous level.
- Final approval triggers ERP sync.
