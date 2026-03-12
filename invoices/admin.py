from django.contrib import admin
from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_name', 'uploaded_by', 'invoice_number', 'vendor_name', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'currency', 'invoice_type')
    search_fields = ('source_name', 'invoice_number', 'vendor_name')
    readonly_fields = ('created_at', 'updated_at', 'extracted_data', 'erp_payload', 'processing_error')
