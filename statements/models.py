from django.db import models
from django.contrib.auth.models import User

class BankStatement(models.Model):
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='statements')
    file = models.FileField(upload_to='statements/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processing_status = models.CharField(
        max_length=16,
        choices=PROCESSING_STATUS_CHOICES,
        default='pending',
    )
    processing_error = models.TextField(blank=True, default='')
    is_processed = models.BooleanField(default=False)
    ai_evaluation = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Statement ({self.user.username}) - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('INCOME', 'Income'),
        ('TRANSFER_OUT', 'Transfer Out'),
        ('TRANSFER_IN', 'Transfer In'),
        ('DIRECT_DEBIT', 'Direct Debit'),
        ('STANDING_ORDER', 'Standing Order'),
        ('CARD_PAYMENT', 'Card Payment'),
        ('ATM_WITHDRAWAL', 'ATM Withdrawal'),
        ('FEE_CHARGE', 'Fee/Charge'),
    ]

    statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField()
    payee_payer = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    category = models.CharField(max_length=60, default='Uncategorized')

    def __str__(self):
        return f"{self.date} | {self.category} | ${self.amount} ({self.transaction_type})"


class APIUsageRecord(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='api_usage_records',
    )
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.PositiveSmallIntegerField()
    duration_ms = models.PositiveIntegerField()
    request_size_bytes = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['endpoint', 'created_at']),
        ]


class GeminiUsageRecord(models.Model):
    STATUS_CHOICES = [
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='gemini_usage_records',
    )
    statement = models.ForeignKey(
        BankStatement,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='gemini_usage_records',
    )
    model_name = models.CharField(max_length=100)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    prompt_tokens = models.PositiveIntegerField(blank=True, null=True)
    completion_tokens = models.PositiveIntegerField(blank=True, null=True)
    total_tokens = models.PositiveIntegerField(blank=True, null=True)
    duration_ms = models.PositiveIntegerField()
    error_type = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]


class AuditEvent(models.Model):
    OUTCOME_CHOICES = [
        ('success', 'Success'),
        ('failure', 'Failure'),
    ]

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='audit_events',
    )
    event_type = models.CharField(max_length=80)
    outcome = models.CharField(
        max_length=12,
        choices=OUTCOME_CHOICES,
        default='success',
    )
    target_type = models.CharField(max_length=80, blank=True, default='')
    target_id = models.CharField(max_length=64, blank=True, default='')
    request_method = models.CharField(max_length=10, blank=True, default='')
    request_route = models.CharField(max_length=255, blank=True, default='')
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['actor', 'created_at']),
            models.Index(fields=['event_type', 'created_at']),
        ]


class UserSecuritySettings(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='security_settings',
    )
    two_factor_enabled = models.BooleanField(default=False)
    encrypted_totp_secret = models.TextField(blank=True, default='')
    encrypted_pending_totp_secret = models.TextField(blank=True, default='')
    pending_totp_expires_at = models.DateTimeField(blank=True, null=True)
    last_totp_counter = models.BigIntegerField(blank=True, null=True)
    auth_version = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)


class TwoFactorRecoveryCode(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='two_factor_recovery_codes',
    )
    code_hash = models.CharField(max_length=64, unique=True)
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'used_at'])]


class TwoFactorLoginChallenge(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='two_factor_login_challenges',
    )
    challenge_hash = models.CharField(max_length=64, unique=True)
    auth_version = models.PositiveIntegerField()
    expires_at = models.DateTimeField(db_index=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'expires_at'])]