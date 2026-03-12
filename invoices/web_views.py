from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

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


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


@require_http_methods(["GET", "POST"])
def register_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Registration successful. Welcome!')
        return redirect('dashboard')

    return render(request, 'auth/register.html', {'form': form})


@require_http_methods(["GET", "POST"])
def login_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        messages.success(request, 'Logged in successfully.')
        return redirect('dashboard')

    return render(request, 'auth/login.html', {'form': form})


@login_required
@require_http_methods(["GET", "POST"])
def dashboard(request):
    upload_form = InvoiceUploadForm()

    if request.method == 'POST':
        upload_form = InvoiceUploadForm(request.POST, request.FILES)
        if upload_form.is_valid():
            invoice = Invoice.objects.create(
                source_name=upload_form.cleaned_data['source_name'],
                file=upload_form.cleaned_data['file'],
                uploaded_by=request.user,
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
                messages.success(request, f'Invoice #{invoice.id} processed and synced successfully.')
            except Exception as exc:
                invoice.status = Invoice.Status.FAILED
                invoice.processing_error = str(exc)
                invoice.save()
                send_invoice_status_email(invoice, synced=False)
                messages.error(request, f'Invoice processing failed: {exc}')

            return redirect('dashboard')

    pending_statuses = [Invoice.Status.UPLOADED, Invoice.Status.PROCESSED]
    user_invoices = Invoice.objects.filter(uploaded_by=request.user)
    pending_invoices = user_invoices.filter(status__in=pending_statuses).order_by('-created_at')
    processed_invoices = user_invoices.filter(status=Invoice.Status.ERP_SYNCED).order_by('-created_at')
    failed_invoices = user_invoices.filter(status=Invoice.Status.FAILED).order_by('-created_at')

    context = {
        'upload_form': upload_form,
        'pending_invoices': pending_invoices,
        'processed_invoices': processed_invoices,
        'failed_invoices': failed_invoices,
        'total_users': User.objects.count(),
        'total_invoices': user_invoices.count(),
    }
    return render(request, 'dashboard.html', context)


@login_required
@require_http_methods(["GET"])
def invoice_detail_page(request, invoice_id: int):
    invoice = get_object_or_404(Invoice, id=invoice_id, uploaded_by=request.user)
    return render(request, 'invoice_detail.html', {'invoice': invoice})


@login_required
@require_http_methods(["POST"])
def logout_page(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("login")
