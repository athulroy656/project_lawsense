from django.urls import path
from . import admin_views

urlpatterns = [
    path('admin/me/', admin_views.admin_me, name='admin_me'),
    path('admin/overview/', admin_views.admin_overview, name='admin_overview'),
    path('admin/document-types/', admin_views.admin_document_types, name='admin_document_types'),
    path('admin/system-health/', admin_views.admin_system_health, name='admin_system_health'),
    path('admin/recent-documents/', admin_views.admin_recent_documents, name='admin_recent_documents'),
    path('admin/documents/<int:pk>/delete/', admin_views.admin_delete_document, name='admin_delete_document'),
    path('admin/documents/<int:pk>/rerun/', admin_views.admin_rerun_analysis, name='admin_rerun_analysis'),
    path('admin/users/', admin_views.admin_users_list, name='admin_users_list'),
]
