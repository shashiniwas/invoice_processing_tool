from django.contrib import admin

from .models import ApprovalAction, Invoice, UserNotification, Workflow, WorkflowStep


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 1


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active', 'created_by', 'created_at')
    inlines = [WorkflowStepInline]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_name', 'uploaded_by', 'workflow', 'current_approval_level', 'approval_state', 'status', 'created_at')
    list_filter = ('status', 'approval_state', 'currency', 'invoice_type')
    search_fields = ('source_name', 'invoice_number', 'vendor_name')
    readonly_fields = ('created_at', 'updated_at', 'extracted_data', 'erp_payload', 'processing_error')


@admin.register(ApprovalAction)
class ApprovalActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice', 'level', 'actor', 'action', 'created_at')
    list_filter = ('action',)


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'invoice', 'message', 'is_read', 'created_at')
    list_filter = ('is_read',)
