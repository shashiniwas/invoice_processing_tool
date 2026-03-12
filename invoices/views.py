from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .forms import InvoiceUploadForm
from .models import Invoice
from .services.ai_processor import AIInvoiceProcessor
from .services.erp import ERPSyncService
from .services.notifications import send_invoice_status_email


def _to_decimal(value):
    if value in [None, '']:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


@method_decorator(csrf_exempt, name='dispatch')
class InvoiceIngestionView(View):
    def post(self, request):
        form = InvoiceUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return JsonResponse({'errors': form.errors}, status=400)

        invoice = Invoice.objects.create(
            source_name=form.cleaned_data['source_name'],
            file=form.cleaned_data['file'],
        )

        processor = AIInvoiceProcessor()
        erp = ERPSyncService()

        try:
            extracted = processor.extract(invoice.file.path)
            invoice.vendor_name = extracted.get('vendor_name', '')
            invoice.invoice_number = extracted.get('invoice_number', '')
            invoice.currency = extracted.get('currency', 'USD')
            invoice.invoice_type = extracted.get('invoice_type', '')
            invoice.total_amount = _to_decimal(extracted.get('total_amount'))
            invoice.tax_amount = _to_decimal(extracted.get('tax_amount'))
            invoice.extracted_data = extracted
            invoice.status = Invoice.Status.PROCESSED

            payload = erp.build_payload(extracted)
            invoice.erp_payload = payload
            erp.send(payload)
            invoice.status = Invoice.Status.ERP_SYNCED
            invoice.save()
            send_invoice_status_email(invoice, synced=True)
        except Exception as exc:
            invoice.status = Invoice.Status.FAILED
            invoice.processing_error = str(exc)
            invoice.save()
            send_invoice_status_email(invoice, synced=False)
            return JsonResponse({'id': invoice.id, 'status': invoice.status, 'error': str(exc)}, status=500)

        return JsonResponse(
            {
                'id': invoice.id,
                'status': invoice.status,
                'invoice_number': invoice.invoice_number,
                'vendor_name': invoice.vendor_name,
                'total_amount': str(invoice.total_amount) if invoice.total_amount is not None else None,
            },
            status=201,
        )


class InvoiceDetailView(View):
    def get(self, request, invoice_id: int):
        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            return JsonResponse({'error': 'Invoice not found'}, status=404)

        return JsonResponse(
            {
                'id': invoice.id,
                'source_name': invoice.source_name,
                'status': invoice.status,
                'invoice_number': invoice.invoice_number,
                'vendor_name': invoice.vendor_name,
                'currency': invoice.currency,
                'total_amount': str(invoice.total_amount) if invoice.total_amount is not None else None,
                'tax_amount': str(invoice.tax_amount) if invoice.tax_amount is not None else None,
                'extracted_data': invoice.extracted_data,
                'erp_payload': invoice.erp_payload,
                'processing_error': invoice.processing_error,
            }
        )
