from django.db import models
from django.contrib.auth.models import User

class BankStatement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='statements')
    file = models.FileField(upload_to='statements/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
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