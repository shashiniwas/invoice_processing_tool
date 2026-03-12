from django.urls import path

from .auth_views import LoginView, LogoutView, ProfileView, RegisterView
from .views import InvoiceDetailView, InvoiceIngestionView

urlpatterns = [
    path('', InvoiceIngestionView.as_view(), name='invoice-ingest'),
    path('<int:invoice_id>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/profile/', ProfileView.as_view(), name='auth-profile'),
]
