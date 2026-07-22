from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView,
    StatementListView,
    StatementUploadView,
    AnalyticsView,
    TransactionListView,
    StatementDeleteView,
    StatementBulkDeleteView,
)

urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Statements
    path('statements/', StatementListView.as_view(), name='statement_list'),
    path('statements/upload/', StatementUploadView.as_view(), name='statement_upload'),
    path('statements/analytics/', AnalyticsView.as_view(), name='statement_analytics'),
    path('statements/delete-all/', StatementBulkDeleteView.as_view(), name='statement_bulk_delete'), # <-- NEU!
    path('statements/<int:pk>/', StatementDeleteView.as_view(), name='statement_delete'),
    
    # Transactions
    path('transactions/', TransactionListView.as_view(), name='transaction_list'),
]