from django.urls import path
from .views import InvoiceDetailView, InvoiceIngestionView

urlpatterns = [
    path('', InvoiceIngestionView.as_view(), name='invoice-ingest'),
    path('<int:invoice_id>/', InvoiceDetailView.as_view(), name='invoice-detail'),
]
