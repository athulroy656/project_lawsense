from django.urls import path
from . import views

urlpatterns = [
    path('documents/', views.list_documents),
    path('documents/upload/', views.upload_document),
    path('documents/<int:document_id>/', views.delete_document),
    path('documents/<int:document_id>/clauses/', views.document_clauses),
    path('documents/<int:document_id>/risk-summary/', views.document_risk_summary),
    path('documents/<int:document_id>/report/', views.document_report),
    path('ask/', views.ask_question),
]