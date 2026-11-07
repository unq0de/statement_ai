import hashlib
import hmac
import secrets
import time
from datetime import timedelta

import pyotp
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    TwoFactorLoginChallenge,
    TwoFactorRecoveryCode,
    UserSecuritySettings,
)


def get_security_settings(user, create=True):
    if create:
        return UserSecuritySettings.objects.get_or_create(user=user)[0]
    return UserSecuritySettings.objects.filter(user=user).first()


def _fernet():
    key = settings.TWO_FACTOR_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_totp_secret(secret):
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_totp_secret(encrypted_secret):
    return _fernet().decrypt(encrypted_secret.encode()).decode()


def consume_totp_code(security_settings, secret, code):
    if not isinstance(code, str) or not code.isdigit() or len(code) != 6:
        return False

    totp = pyotp.TOTP(secret)
    current_counter = int(time.time() // totp.interval)
    previous_counter = security_settings.last_totp_counter
    for counter in range(current_counter - 1, current_counter + 2):
        if previous_counter is not None and counter <= previous_counter:
            continue
        if hmac.compare_digest(totp.generate_otp(counter), code):
            security_settings.last_totp_counter = counter
            security_settings.save(update_fields=['last_totp_counter', 'updated_at'])
            return True
    return False


def hash_recovery_code(code):
    normalized = ''.join(character for character in code.upper() if character.isalnum())
    return hmac.new(
        str(settings.SECRET_KEY).encode(),
        normalized.encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_recovery_codes(user):
    TwoFactorRecoveryCode.objects.filter(user=user).delete()
    recovery_codes = []
    for _ in range(settings.TWO_FACTOR_RECOVERY_CODE_COUNT):
        raw_code = secrets.token_hex(8).upper()
        recovery_codes.append(f'{raw_code[:8]}-{raw_code[8:]}')
        TwoFactorRecoveryCode.objects.create(
            user=user,
            code_hash=hash_recovery_code(raw_code),
        )
    return recovery_codes


def consume_recovery_code(user, code):
    code_hash = hash_recovery_code(code)
    recovery_code = TwoFactorRecoveryCode.objects.select_for_update().filter(
        user=user,
        code_hash=code_hash,
        used_at__isnull=True,
    ).first()
    if recovery_code is None:
        return False

    recovery_code.used_at = timezone.now()
    recovery_code.save(update_fields=['used_at'])
    return True


def create_login_challenge(user, auth_version):
    raw_challenge = secrets.token_urlsafe(32)
    TwoFactorLoginChallenge.objects.create(
        user=user,
        challenge_hash=hashlib.sha256(raw_challenge.encode()).hexdigest(),
        auth_version=auth_version,
        expires_at=timezone.now() + timedelta(
            seconds=settings.TWO_FACTOR_CHALLENGE_TIMEOUT_SECONDS
        ),
    )
    return raw_challenge


def issue_token_pair(user, auth_version):
    refresh = RefreshToken.for_user(user)
    refresh['auth_version'] = auth_version
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
