from django.conf import settings
from django.db import models


class Invoice(models.Model):
    class Status(models.TextChoices):
        UPLOADED = 'uploaded', 'Uploaded'
        PROCESSED = 'processed', 'Processed'
        ERP_SYNCED = 'erp_synced', 'ERP Synced'
        FAILED = 'failed', 'Failed'

    source_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    file = models.FileField(upload_to='invoices/')
    vendor_name = models.CharField(max_length=255, blank=True)
    invoice_number = models.CharField(max_length=120, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=12, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    invoice_type = models.CharField(max_length=120, blank=True)
    extracted_data = models.JSONField(default=dict, blank=True)
    erp_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    processing_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source_name} ({self.status})"
