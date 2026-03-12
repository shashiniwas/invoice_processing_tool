import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import ApprovalAction, Invoice, Workflow, WorkflowStep
from .services.ai_processor import AIInvoiceProcessor


class InvoicePipelineTests(TestCase):
    def test_upload_processes_invoice(self):
        payload = b"Vendor: ACME Corp\nInvoice Number: INV-123\nCurrency: USD\nTotal: 1050.50\nVAT: 50.50\n"
        invoice_file = SimpleUploadedFile('invoice.txt', payload, content_type='text/plain')

        response = self.client.post(reverse('invoice-ingest'), data={'source_name': 'email_attachment', 'file': invoice_file})

        self.assertEqual(response.status_code, 201)
        invoice = Invoice.objects.get(id=response.json()['id'])
        self.assertEqual(invoice.invoice_number, 'INV-123')


class AuthenticationTests(TestCase):
    def test_register_login_profile_and_logout(self):
        self.client.post(reverse('auth-register'), data=json.dumps({'username': 'alice', 'email': 'alice@example.com', 'password': 's3cr3t-pass'}), content_type='application/json')
        self.client.post(reverse('auth-login'), data=json.dumps({'username': 'alice', 'password': 's3cr3t-pass'}), content_type='application/json')
        self.assertEqual(self.client.get(reverse('auth-profile')).status_code, 200)
        self.client.post(reverse('auth-logout'))
        self.assertEqual(self.client.get(reverse('auth-profile')).status_code, 401)


class WorkflowWebUITests(TestCase):
    def setUp(self):
        self.initiator = User.objects.create_user(username='init', password='pass12345')
        self.approver1 = User.objects.create_user(username='ap1', password='pass12345')
        self.approver2 = User.objects.create_user(username='ap2', password='pass12345')
        self.admin = User.objects.create_superuser(username='admin', password='admin12345', email='admin@example.com')

        self.workflow = Workflow.objects.create(name='WF1', created_by=self.admin)
        WorkflowStep.objects.create(workflow=self.workflow, level=1, approver=self.approver1)
        WorkflowStep.objects.create(workflow=self.workflow, level=2, approver=self.approver2)

    def test_admin_can_create_workflow_page(self):
        self.client.login(username='admin', password='admin12345')
        response = self.client.post(
            reverse('create-workflow'),
            data={'name': 'WF2', 'approver_usernames': 'ap1,ap2', 'show_vendor_name': 'on', 'show_invoice_number': 'on', 'show_table_data': 'on'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Workflow.objects.filter(name='WF2').exists())

    def test_initiator_upload_send_and_approver_approve_reject(self):
        self.client.login(username='init', password='pass12345')
        invoice_file = SimpleUploadedFile('invoice.txt', b"Vendor: V\nInvoice Number: I-1\nTotal: 10.00", content_type='text/plain')
        upload_response = self.client.post(
            reverse('dashboard'),
            data={'action': 'upload_invoice', 'source_name': 'src', 'workflow': self.workflow.id, 'file': invoice_file},
            follow=True,
        )
        self.assertEqual(upload_response.status_code, 200)
        invoice = Invoice.objects.filter(uploaded_by=self.initiator).latest('id')

        send_response = self.client.post(
            reverse('invoice-detail-page', kwargs={'invoice_id': invoice.id}),
            data={'action': 'send_for_approval', 'remarks': 'please review'},
            follow=True,
        )
        self.assertEqual(send_response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.approval_state, Invoice.ApprovalState.IN_APPROVAL)
        self.assertEqual(invoice.current_approval_level, 1)

        self.client.logout()
        self.client.login(username='ap1', password='pass12345')
        approve_response = self.client.post(
            reverse('invoice-detail-page', kwargs={'invoice_id': invoice.id}),
            data={'action': 'approve', 'remarks': 'ok'},
            follow=True,
        )
        self.assertEqual(approve_response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.current_approval_level, 2)

        self.client.logout()
        self.client.login(username='ap2', password='pass12345')
        reject_response = self.client.post(
            reverse('invoice-detail-page', kwargs={'invoice_id': invoice.id}),
            data={'action': 'reject', 'remarks': 'need correction'},
            follow=True,
        )
        self.assertEqual(reject_response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.approval_state, Invoice.ApprovalState.REJECTED)
        self.assertEqual(invoice.current_approval_level, 1)
        self.assertTrue(ApprovalAction.objects.filter(invoice=invoice, action=ApprovalAction.Action.REJECTED).exists())

    def test_reject_requires_remarks(self):
        invoice = Invoice.objects.create(source_name='x', uploaded_by=self.initiator, workflow=self.workflow, file='invoices/x.pdf', approval_state=Invoice.ApprovalState.IN_APPROVAL, current_approval_level=1)
        self.client.login(username='ap1', password='pass12345')
        response = self.client.post(reverse('invoice-detail-page', kwargs={'invoice_id': invoice.id}), data={'action': 'reject', 'remarks': ''}, follow=True)
        self.assertEqual(response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.approval_state, Invoice.ApprovalState.IN_APPROVAL)


class AIProcessorTests(TestCase):
    def test_rule_parser_extracts_common_invoice_fields(self):
        processor = AIInvoiceProcessor()
        data = processor._extract_with_rules("Vendor: Tools Inc\nInvoice Number: TI-700\nTotal Amount: $1,250.30\nVAT: $50.30\nCurrency: USD")
        self.assertEqual(data['vendor_name'], 'Tools Inc')
        self.assertEqual(data['invoice_number'], 'TI-700')

    @patch('invoices.services.ai_processor.AIInvoiceProcessor._extract_from_digital_pdf_with_pdfplumber')
    def test_pdf_uses_pdf_extraction_path(self, mock_pdf_extract):
        mock_pdf_extract.return_value = ('Vendor: PDF Corp\nInvoice Number: PDF-1\nTotal: 100.00', [])
        processor = AIInvoiceProcessor()
        with patch('pathlib.Path.read_text', return_value=''):
            result = processor.extract('/tmp/sample.pdf')
        self.assertEqual(result['invoice_number'], 'PDF-1')
