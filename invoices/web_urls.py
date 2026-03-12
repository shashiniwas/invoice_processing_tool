from django.urls import path

from .web_views import (
    create_workflow,
    dashboard,
    home,
    invoice_detail_page,
    login_page,
    logout_page,
    mark_notifications_read,
    register_page,
)

urlpatterns = [
    path('', home, name='home'),
    path('login/', login_page, name='login'),
    path('register/', register_page, name='register'),
    path('logout/', logout_page, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/invoices/<int:invoice_id>/', invoice_detail_page, name='invoice-detail-page'),
    path('dashboard/notifications/read/', mark_notifications_read, name='mark-notifications-read'),
    path('dashboard/workflows/create/', create_workflow, name='create-workflow'),
]
