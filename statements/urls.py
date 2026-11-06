from django.urls import path
from .views import (
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordRevokingTokenRefreshView,
    RegisterView,
    StatementListView,
    StatementDetailView,
    StatementUploadView,
    AnalyticsView,
    TransactionListView,
    TransactionDetailView,
    StatementBulkDeleteView,
    StatementFileDownloadView,
    AccountDeleteView,
    DataExportView,
)

urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', LoginView.as_view(), name='token_obtain_pair'),
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('auth/refresh/', PasswordRevokingTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/account/', AccountDeleteView.as_view(), name='account_delete'),
    path('auth/export/', DataExportView.as_view(), name='data_export'),

    # Statements
    path('statements/', StatementListView.as_view(), name='statement_list'),
    path('statements/upload/', StatementUploadView.as_view(), name='statement_upload'),
    path('statements/analytics/', AnalyticsView.as_view(), name='statement_analytics'),
    path('statements/delete-all/', StatementBulkDeleteView.as_view(), name='statement_bulk_delete'),
    path('statements/<int:pk>/', StatementDetailView.as_view(), name='statement_detail'),
    path('statements/<int:pk>/file/', StatementFileDownloadView.as_view(), name='statement_file_download'),

    # Transactions
    path('transactions/', TransactionListView.as_view(), name='transaction_list'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction_detail'),

    # Compatibility aliases
    path('analytics/', AnalyticsView.as_view(), name='analytics_alias'),
]