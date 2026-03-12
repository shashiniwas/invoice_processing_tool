from django.conf import settings
from django.db import models


class Workflow(models.Model):
    name = models.CharField(max_length=120, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    show_vendor_name = models.BooleanField(default=True)
    show_invoice_number = models.BooleanField(default=True)
    show_invoice_date = models.BooleanField(default=True)
    show_due_date = models.BooleanField(default=True)
    show_currency = models.BooleanField(default=True)
    show_total_amount = models.BooleanField(default=True)
    show_tax_amount = models.BooleanField(default=True)
    show_invoice_type = models.BooleanField(default=True)
    show_table_data = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class WorkflowStep(models.Model):
    workflow = models.ForeignKey(Workflow, related_name='steps', on_delete=models.CASCADE)
    level = models.PositiveIntegerField()
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='approval_steps', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('workflow', 'level')
        ordering = ['level']

    def __str__(self):
        return f'{self.workflow.name} L{self.level} - {self.approver.username}'


class Invoice(models.Model):
    class Status(models.TextChoices):
        UPLOADED = 'uploaded', 'Uploaded'
        PROCESSED = 'processed', 'Processed'
        ERP_SYNCED = 'erp_synced', 'ERP Synced'
        FAILED = 'failed', 'Failed'

    class ApprovalState(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        IN_APPROVAL = 'in_approval', 'In Approval'
        REJECTED = 'rejected', 'Rejected'
        FINAL_APPROVED = 'final_approved', 'Final Approved'

    source_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    workflow = models.ForeignKey(Workflow, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    current_approval_level = models.PositiveIntegerField(default=0)
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
    approval_state = models.CharField(max_length=20, choices=ApprovalState.choices, default=ApprovalState.DRAFT)
    processing_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source_name} ({self.status})"


class ApprovalAction(models.Model):
    class Action(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    invoice = models.ForeignKey(Invoice, related_name='approval_actions', on_delete=models.CASCADE)
    level = models.PositiveIntegerField(default=0)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class UserNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='invoice_notifications', on_delete=models.CASCADE)
    invoice = models.ForeignKey(Invoice, related_name='notifications', on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
