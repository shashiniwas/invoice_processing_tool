from django.conf import settings
from django.core.mail import send_mail


def send_invoice_status_email(invoice, synced: bool) -> None:
    subject = f"Invoice {invoice.id} {'synced to ERP' if synced else 'processing failed'}"
    body = (
        f"Source: {invoice.source_name}\n"
        f"Status: {invoice.status}\n"
        f"Invoice Number: {invoice.invoice_number}\n"
        f"Vendor: {invoice.vendor_name}\n"
        f"Total: {invoice.total_amount} {invoice.currency}\n"
        f"Error: {invoice.processing_error or 'None'}"
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.NOTIFICATION_EMAIL], fail_silently=True)
