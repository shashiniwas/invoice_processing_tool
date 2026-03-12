import json

from django.contrib.auth.models import User
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


class AuthenticationTests(TestCase):
    def test_register_login_profile_and_logout(self):
        register_response = self.client.post(
            reverse('auth-register'),
            data=json.dumps({'username': 'alice', 'email': 'alice@example.com', 'password': 's3cr3t-pass'}),
            content_type='application/json',
        )
        self.assertEqual(register_response.status_code, 201)

        login_response = self.client.post(
            reverse('auth-login'),
            data=json.dumps({'username': 'alice', 'password': 's3cr3t-pass'}),
            content_type='application/json',
        )
        self.assertEqual(login_response.status_code, 200)

        profile_response = self.client.get(reverse('auth-profile'))
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.json()['username'], 'alice')

        logout_response = self.client.post(reverse('auth-logout'))
        self.assertEqual(logout_response.status_code, 200)

        profile_after_logout = self.client.get(reverse('auth-profile'))
        self.assertEqual(profile_after_logout.status_code, 401)

    def test_register_duplicate_username_fails(self):
        self.client.post(
            reverse('auth-register'),
            data=json.dumps({'username': 'bob', 'password': 'pw123456'}),
            content_type='application/json',
        )
        duplicate_response = self.client.post(
            reverse('auth-register'),
            data=json.dumps({'username': 'bob', 'password': 'pw999999'}),
            content_type='application/json',
        )
        self.assertEqual(duplicate_response.status_code, 409)


class WebUITests(TestCase):
    def test_user_can_register_and_see_dashboard(self):
        response = self.client.post(
            reverse('register'),
            data={
                'username': 'webuser',
                'password1': 'VeryStrongPass123',
                'password2': 'VeryStrongPass123',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Dashboard')

    def test_dashboard_upload_and_invoice_detail_page(self):
        user = User.objects.create_user(username='dash', password='SecurePass123')
        self.client.login(username='dash', password='SecurePass123')

        payload = (
            b"Vendor: Bright Supplies\n"
            b"Invoice Number: INV-778\n"
            b"Currency: USD\n"
            b"Total: 800.00\n"
        )
        invoice_file = SimpleUploadedFile('invoice2.txt', payload, content_type='text/plain')

        response = self.client.post(
            reverse('dashboard'),
            data={'source_name': 'dashboard_upload', 'file': invoice_file},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Processed Invoices')

        invoice = Invoice.objects.get(invoice_number='INV-778')
        detail_response = self.client.get(reverse('invoice-detail-page', kwargs={'invoice_id': invoice.id}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Extracted Fields')
        self.assertContains(detail_response, 'Open / Download Invoice')
