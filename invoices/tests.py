from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Invoice


class InvoicePipelineTests(TestCase):
    def test_upload_processes_and_syncs_invoice(self):
        payload = (
            b"Vendor: ACME Corp\n"
            b"Invoice Number: INV-123\n"
            b"Currency: USD\n"
            b"Total: 1050.50\n"
            b"VAT: 50.50\n"
        )
        invoice_file = SimpleUploadedFile('invoice.txt', payload, content_type='text/plain')

        response = self.client.post(
            reverse('invoice-ingest'),
            data={'source_name': 'email_attachment', 'file': invoice_file},
        )

        self.assertEqual(response.status_code, 201)
        invoice = Invoice.objects.get(id=response.json()['id'])
        self.assertEqual(invoice.status, Invoice.Status.ERP_SYNCED)
        self.assertEqual(invoice.invoice_number, 'INV-123')
        self.assertEqual(str(invoice.total_amount), '1050.50')

    def test_detail_endpoint_returns_invoice_data(self):
        invoice = Invoice.objects.create(source_name='upload', file='invoices/test.txt', status=Invoice.Status.PROCESSED)

        response = self.client.get(reverse('invoice-detail', kwargs={'invoice_id': invoice.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['id'], invoice.id)
