from django import forms

from .models import Workflow


class InvoiceUploadForm(forms.Form):
    source_name = forms.CharField(max_length=255)
    workflow = forms.ModelChoiceField(queryset=Workflow.objects.filter(is_active=True), required=False)
    file = forms.FileField()


class WorkflowCreateForm(forms.Form):
    name = forms.CharField(max_length=120)
    approver_usernames = forms.CharField(
        help_text='Comma-separated usernames in approval order (e.g. manager1,finance1,cfo).'
    )

    show_vendor_name = forms.BooleanField(required=False, initial=True)
    show_invoice_number = forms.BooleanField(required=False, initial=True)
    show_invoice_date = forms.BooleanField(required=False, initial=True)
    show_due_date = forms.BooleanField(required=False, initial=True)
    show_currency = forms.BooleanField(required=False, initial=True)
    show_total_amount = forms.BooleanField(required=False, initial=True)
    show_tax_amount = forms.BooleanField(required=False, initial=True)
    show_invoice_type = forms.BooleanField(required=False, initial=True)
    show_table_data = forms.BooleanField(required=False, initial=True)
