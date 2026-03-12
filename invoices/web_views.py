from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import InvoiceUploadForm, WorkflowCreateForm
from .models import ApprovalAction, Invoice, UserNotification, Workflow, WorkflowStep
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


def _notify(user, invoice, message):
    if user:
        UserNotification.objects.create(user=user, invoice=invoice, message=message)


def _next_step(invoice: Invoice):
    if not invoice.workflow:
        return None
    return invoice.workflow.steps.filter(level=invoice.current_approval_level).first()


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

    if request.method == 'POST' and request.POST.get('action') == 'upload_invoice':
        upload_form = InvoiceUploadForm(request.POST, request.FILES)
        if upload_form.is_valid():
            invoice = Invoice.objects.create(
                source_name=upload_form.cleaned_data['source_name'],
                workflow=upload_form.cleaned_data.get('workflow'),
                file=upload_form.cleaned_data['file'],
                uploaded_by=request.user,
            )

            processor = AIInvoiceProcessor()
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
                invoice.approval_state = Invoice.ApprovalState.DRAFT
                invoice.save()
                messages.success(request, f'Invoice #{invoice.id} uploaded and parsed. Send for approval when ready.')
            except Exception as exc:
                invoice.status = Invoice.Status.FAILED
                invoice.processing_error = str(exc)
                invoice.save()
                send_invoice_status_email(invoice, synced=False)
                messages.error(request, f'Invoice processing failed: {exc}')

            return redirect('dashboard')

    initiator_invoices = Invoice.objects.filter(uploaded_by=request.user)
    initiator_pending = initiator_invoices.filter(approval_state__in=[Invoice.ApprovalState.DRAFT, Invoice.ApprovalState.REJECTED]).order_by('-created_at')
    initiator_sent = initiator_invoices.filter(approval_state=Invoice.ApprovalState.IN_APPROVAL).order_by('-created_at')
    initiator_rejected = initiator_invoices.filter(approval_state=Invoice.ApprovalState.REJECTED).order_by('-created_at')

    approver_pending = Invoice.objects.filter(
        approval_state=Invoice.ApprovalState.IN_APPROVAL,
        workflow__steps__level=F('current_approval_level'),
        workflow__steps__approver=request.user,
    ).distinct().order_by('-created_at')
    approver_approved = Invoice.objects.filter(approval_actions__actor=request.user, approval_actions__action=ApprovalAction.Action.APPROVED).distinct().order_by('-created_at')
    approver_rejected = Invoice.objects.filter(approval_actions__actor=request.user, approval_actions__action=ApprovalAction.Action.REJECTED).distinct().order_by('-created_at')

    unread_notifications = UserNotification.objects.filter(user=request.user, is_read=False)

    context = {
        'upload_form': upload_form,
        'initiator_pending': initiator_pending,
        'initiator_sent': initiator_sent,
        'initiator_rejected': initiator_rejected,
        'approver_pending': approver_pending,
        'approver_approved': approver_approved,
        'approver_rejected': approver_rejected,
        'notification_count': unread_notifications.count(),
        'notifications': unread_notifications[:10],
        'total_users': User.objects.count(),
        'total_invoices': initiator_invoices.count(),
    }
    return render(request, 'dashboard.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def invoice_detail_page(request, invoice_id: int):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    if invoice.uploaded_by != request.user and not request.user.is_superuser:
        step = invoice.workflow.steps.filter(level=invoice.current_approval_level, approver=request.user).first() if invoice.workflow else None
        if not step:
            messages.error(request, 'Not authorized.')
            return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_fields' and invoice.uploaded_by == request.user and invoice.approval_state in [Invoice.ApprovalState.DRAFT, Invoice.ApprovalState.REJECTED]:
            invoice.vendor_name = request.POST.get('vendor_name', '')
            invoice.invoice_number = request.POST.get('invoice_number', '')
            invoice.currency = request.POST.get('currency', '')
            invoice.invoice_type = request.POST.get('invoice_type', '')
            invoice.total_amount = _to_decimal(request.POST.get('total_amount'))
            invoice.tax_amount = _to_decimal(request.POST.get('tax_amount'))
            invoice.save()
            messages.success(request, 'Invoice fields updated.')
            return redirect('invoice-detail-page', invoice_id=invoice.id)

        if action == 'send_for_approval' and invoice.uploaded_by == request.user:
            if not invoice.workflow or not invoice.workflow.steps.exists():
                messages.error(request, 'Workflow missing or has no approval steps.')
                return redirect('invoice-detail-page', invoice_id=invoice.id)

            invoice.approval_state = Invoice.ApprovalState.IN_APPROVAL
            invoice.current_approval_level = 1
            invoice.save()
            ApprovalAction.objects.create(invoice=invoice, level=0, actor=request.user, action=ApprovalAction.Action.SUBMITTED, remarks=request.POST.get('remarks', ''))
            next_step = _next_step(invoice)
            if next_step:
                _notify(next_step.approver, invoice, f'Invoice #{invoice.id} pending your approval.')
            messages.success(request, 'Invoice sent for approval.')
            return redirect('invoice-detail-page', invoice_id=invoice.id)

        if action in ['approve', 'reject']:
            current_step = _next_step(invoice)
            if not current_step or current_step.approver != request.user:
                messages.error(request, 'You are not current approver for this invoice.')
                return redirect('invoice-detail-page', invoice_id=invoice.id)

            remarks = (request.POST.get('remarks') or '').strip()
            if action == 'reject' and not remarks:
                messages.error(request, 'Remarks are mandatory for rejection.')
                return redirect('invoice-detail-page', invoice_id=invoice.id)

            if action == 'approve':
                ApprovalAction.objects.create(invoice=invoice, level=invoice.current_approval_level, actor=request.user, action=ApprovalAction.Action.APPROVED, remarks=remarks)
                next_level = invoice.current_approval_level + 1
                next_step = invoice.workflow.steps.filter(level=next_level).first() if invoice.workflow else None
                if next_step:
                    invoice.current_approval_level = next_level
                    invoice.approval_state = Invoice.ApprovalState.IN_APPROVAL
                    invoice.save()
                    _notify(next_step.approver, invoice, f'Invoice #{invoice.id} moved to your approval level.')
                    messages.success(request, 'Approved and moved to next level.')
                else:
                    invoice.approval_state = Invoice.ApprovalState.FINAL_APPROVED
                    invoice.save()
                    erp = ERPSyncService()
                    try:
                        payload = erp.build_payload(invoice.extracted_data)
                        invoice.erp_payload = payload
                        erp.send(payload)
                        invoice.status = Invoice.Status.ERP_SYNCED
                        invoice.save()
                        send_invoice_status_email(invoice, synced=True)
                        _notify(invoice.uploaded_by, invoice, f'Invoice #{invoice.id} has final approval and synced to ERP.')
                        messages.success(request, 'Final approval done and synced to ERP.')
                    except Exception as exc:
                        invoice.status = Invoice.Status.FAILED
                        invoice.processing_error = str(exc)
                        invoice.save()
                        send_invoice_status_email(invoice, synced=False)
                        messages.error(request, f'Final approval done but ERP sync failed: {exc}')
            else:
                ApprovalAction.objects.create(invoice=invoice, level=invoice.current_approval_level, actor=request.user, action=ApprovalAction.Action.REJECTED, remarks=remarks)
                invoice.approval_state = Invoice.ApprovalState.REJECTED
                invoice.current_approval_level = max(invoice.current_approval_level - 1, 0)
                invoice.save()

                if invoice.current_approval_level == 0:
                    _notify(invoice.uploaded_by, invoice, f'Invoice #{invoice.id} rejected and returned to initiator.')
                else:
                    prev_step = invoice.workflow.steps.filter(level=invoice.current_approval_level).first() if invoice.workflow else None
                    if prev_step:
                        _notify(prev_step.approver, invoice, f'Invoice #{invoice.id} rejected back to your level.')
                messages.warning(request, 'Invoice rejected and routed to previous level.')

            return redirect('invoice-detail-page', invoice_id=invoice.id)

    notifications = UserNotification.objects.filter(user=request.user, is_read=False)
    workflow = invoice.workflow
    actions = invoice.approval_actions.select_related('actor').all().order_by('-created_at')
    return render(
        request,
        'invoice_detail.html',
        {
            'invoice': invoice,
            'workflow': workflow,
            'actions': actions,
            'is_initiator': invoice.uploaded_by == request.user,
            'current_step_user': _next_step(invoice).approver if _next_step(invoice) else None,
            'can_approve': bool(_next_step(invoice) and _next_step(invoice).approver == request.user and invoice.approval_state == Invoice.ApprovalState.IN_APPROVAL),
            'notification_count': notifications.count(),
        },
    )


@login_required
@require_http_methods(["POST"])
def mark_notifications_read(request):
    UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('dashboard')


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["GET", "POST"])
def create_workflow(request):
    form = WorkflowCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        workflow = Workflow.objects.create(
            name=form.cleaned_data['name'],
            created_by=request.user,
            show_vendor_name=form.cleaned_data['show_vendor_name'],
            show_invoice_number=form.cleaned_data['show_invoice_number'],
            show_invoice_date=form.cleaned_data['show_invoice_date'],
            show_due_date=form.cleaned_data['show_due_date'],
            show_currency=form.cleaned_data['show_currency'],
            show_total_amount=form.cleaned_data['show_total_amount'],
            show_tax_amount=form.cleaned_data['show_tax_amount'],
            show_invoice_type=form.cleaned_data['show_invoice_type'],
            show_table_data=form.cleaned_data['show_table_data'],
        )
        usernames = [u.strip() for u in form.cleaned_data['approver_usernames'].split(',') if u.strip()]
        level = 1
        for username in usernames:
            user = User.objects.filter(username=username, is_superuser=False).first()
            if user:
                WorkflowStep.objects.create(workflow=workflow, level=level, approver=user)
                level += 1

        messages.success(request, f'Workflow "{workflow.name}" created with {max(level-1, 0)} approval levels.')
        return redirect('create-workflow')

    return render(request, 'workflow_create.html', {'form': form})


@login_required
@require_http_methods(["POST"])
def logout_page(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("login")
