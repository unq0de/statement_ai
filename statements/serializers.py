from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import BankStatement, Transaction

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )

class AccountDeleteSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'date', 'payee_payer', 'description', 'amount', 'transaction_type', 'category']

class BankStatementSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = BankStatement
        fields = ['id', 'file', 'uploaded_at', 'is_processed', 'ai_evaluation', 'transactions']
        read_only_fields = ['is_processed', 'uploaded_at', 'ai_evaluation']