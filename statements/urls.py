from django.urls import path
from .views import (
    LoginView,
    TwoFactorDisableView,
    TwoFactorEnableView,
    TwoFactorLoginView,
    TwoFactorRecoveryCodesView,
    TwoFactorSetupView,
    TwoFactorStatusView,
    RegistrationConfirmView,
    RegistrationConfirmationRequestView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordRevokingTokenRefreshView,
    RegisterView,
    StatementListView,
    StatementDetailView,
    StatementUploadView,
    StatementProcessingStatusView,
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
    path('auth/register/confirm/', RegistrationConfirmView.as_view(), name='auth_register_confirm'),
    path('auth/register/resend-confirmation/', RegistrationConfirmationRequestView.as_view(), name='auth_register_resend_confirmation'),
    path('auth/login/', LoginView.as_view(), name='token_obtain_pair'),
    path('auth/login/2fa/', TwoFactorLoginView.as_view(), name='token_obtain_pair_2fa'),
    path('auth/2fa/', TwoFactorStatusView.as_view(), name='two_factor_status'),
    path('auth/2fa/setup/', TwoFactorSetupView.as_view(), name='two_factor_setup'),
    path('auth/2fa/enable/', TwoFactorEnableView.as_view(), name='two_factor_enable'),
    path('auth/2fa/disable/', TwoFactorDisableView.as_view(), name='two_factor_disable'),
    path('auth/2fa/recovery-codes/', TwoFactorRecoveryCodesView.as_view(), name='two_factor_recovery_codes'),
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('auth/refresh/', PasswordRevokingTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/account/', AccountDeleteView.as_view(), name='account_delete'),
    path('auth/export/', DataExportView.as_view(), name='data_export'),

    # Statements
    path('statements/', StatementListView.as_view(), name='statement_list'),
    path('statements/upload/', StatementUploadView.as_view(), name='statement_upload'),
    path('statements/<int:pk>/status/', StatementProcessingStatusView.as_view(), name='statement_processing_status'),
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