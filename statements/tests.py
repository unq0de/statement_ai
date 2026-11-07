import json
import time
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

import pyotp
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import (
    APIUsageRecord,
    AuditEvent,
    BankStatement,
    GeminiUsageRecord,
    Transaction,
    UserSecuritySettings,
)
from .services import process_pdf_statement_with_gemini
from .tasks import process_statement_task

User = get_user_model()


class StatementApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='StrongPass123!',
        )
        self.other_user = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='StrongPass456!',
        )
        mail.outbox.clear()

    def request_password_reset(self, email='alice@example.com'):
        return self.client.post(
            '/api/auth/password-reset/',
            {'email': email},
            format='json',
        )

    def authenticate(self, username='alice', password='StrongPass123!'):
        response = self.client.post(
            '/api/auth/login/',
            {'username': username, 'password': password},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='security@example.com',
        REGISTRATION_CONFIRMATION_URL='https://app.example.test/confirm-email/',
    )
    def test_registration_requires_email_confirmation_before_login(self):
        response = self.client.post(
            '/api/auth/register/',
            {'username': 'charlie', 'email': 'charlie@example.com', 'password': 'StrongPass789!'},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(len(mail.outbox), 1)

        user = User.objects.get(username='charlie')
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='auth.registration.created',
                target_id=str(user.pk),
            ).exists()
        )
        self.assertFalse(user.is_active)

        login = self.client.post(
            '/api/auth/login/',
            {'username': 'charlie', 'password': 'StrongPass789!'},
            format='json',
        )
        self.assertEqual(login.status_code, 401)

        confirmation_link = mail.outbox[0].body.split(
            'Confirm your email address using this link:\n', 1
        )[1].splitlines()[0]
        query = parse_qs(urlsplit(confirmation_link).fragment)
        payload = {'uid': query['uid'][0], 'token': query['token'][0]}
        confirmation = self.client.post(
            '/api/auth/register/confirm/', payload, format='json'
        )
        self.assertEqual(confirmation.status_code, 200, confirmation.content)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='auth.registration.confirmed',
                actor=user,
                target_id=str(user.pk),
            ).exists()
        )

        reused = self.client.post(
            '/api/auth/register/confirm/', payload, format='json'
        )
        self.assertEqual(reused.status_code, 400)

        login = self.client.post(
            '/api/auth/login/',
            {'username': 'charlie', 'password': 'StrongPass789!'},
            format='json',
        )
        self.assertEqual(login.status_code, 200, login.content)
        self.assertIn('access', login.data)
        self.assertIn('refresh', login.data)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='security@example.com',
        REGISTRATION_CONFIRMATION_URL='https://app.example.test/confirm-email/',
    )
    def test_registration_confirmation_resend_does_not_reveal_account_existence(self):
        self.client.post(
            '/api/auth/register/',
            {'username': 'charlie', 'email': 'charlie@example.com', 'password': 'StrongPass789!'},
            format='json',
        )
        mail.outbox.clear()

        existing = self.client.post(
            '/api/auth/register/resend-confirmation/',
            {'email': 'charlie@example.com'},
            format='json',
        )
        unknown = self.client.post(
            '/api/auth/register/resend-confirmation/',
            {'email': 'unknown@example.com'},
            format='json',
        )
        self.assertEqual(existing.status_code, 200)
        self.assertEqual(existing.data, unknown.data)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='security@example.com',
        EMAIL_USE_HTML_TEMPLATES=True,
        REGISTRATION_CONFIRMATION_URL='https://app.example.test/confirm-email/',
    )
    def test_registration_confirmation_sends_html_and_text_alternatives(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'html-user',
                'email': 'html-user@example.com',
                'password': 'StrongPass789!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)

        message = mail.outbox[0]
        self.assertIn('Confirm your email address using this link:', message.body)
        self.assertEqual(len(message.alternatives), 1)
        html_body, content_type = message.alternatives[0]
        self.assertEqual(content_type, 'text/html')
        self.assertIn('Confirm email address', html_body)
        self.assertIn('href="https://app.example.test/confirm-email/#uid=', html_body)

    def test_registration_rejects_password_shorter_than_configured_minimum(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'short-password-user',
                'email': 'short@example.com',
                'password': 'Short1!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)

    def test_registration_rejects_password_similar_to_username(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'samepassword',
                'email': 'similar@example.com',
                'password': 'SamePassword123!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)

    def test_registration_rejects_password_without_special_character(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'plain-password-user',
                'email': 'plain@example.com',
                'password': 'AnotherStrongPass987',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)
        self.assertIn('special character', response.data['password'][0].lower())

    def test_existing_weak_password_requires_reset_without_counting_as_failure(self):
        User.objects.create_user(
            username='legacy',
            email='legacy@example.com',
            password='Weak1!',
        )
        for _ in range(4):
            response = self.client.post(
                '/api/auth/login/',
                {'username': 'legacy', 'password': 'IncorrectPass123!'},
                format='json',
            )
            self.assertEqual(response.status_code, 401)

        response = self.client.post(
            '/api/auth/login/',
            {'username': 'legacy', 'password': 'Weak1!'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['detail'].code, 'password_reset_required')

        next_failure = self.client.post(
            '/api/auth/login/',
            {'username': 'legacy', 'password': 'IncorrectPass123!'},
            format='json',
        )
        self.assertEqual(next_failure.status_code, 401)

    @override_settings(TWO_FACTOR_ENABLED=True)
    def test_optional_two_factor_setup_login_recovery_and_disable(self):
        initial_login = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(initial_login.status_code, 200)
        old_access = initial_login.data['access']
        old_refresh = initial_login.data['refresh']

        setup = self.client.post(
            '/api/auth/2fa/setup/',
            {'password': 'StrongPass123!'},
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {old_access}",
        )
        self.assertEqual(setup.status_code, 200, setup.content)
        secret = setup.data['secret']
        self.assertIn('otpauth://totp/', setup.data['otpauth_url'])

        setup_code = pyotp.TOTP(secret).generate_otp(int(time.time() // 30) - 1)
        enabled = self.client.post(
            '/api/auth/2fa/enable/',
            {'code': setup_code},
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {old_access}",
        )
        self.assertEqual(enabled.status_code, 200, enabled.content)
        self.assertEqual(len(enabled.data['recovery_codes']), 10)
        security_settings = UserSecuritySettings.objects.get(user=self.user)
        self.assertNotEqual(security_settings.encrypted_totp_secret, secret)
        self.assertTrue(security_settings.two_factor_enabled)

        old_access_result = self.client.get(
            '/api/statements/',
            HTTP_AUTHORIZATION=f"Bearer {old_access}",
        )
        self.assertEqual(old_access_result.status_code, 401)
        old_refresh_result = self.client.post(
            '/api/auth/refresh/', {'refresh': old_refresh}, format='json'
        )
        self.assertEqual(old_refresh_result.status_code, 401)

        login = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.data['mfa_required'])
        self.assertNotIn('access', login.data)
        self.assertNotIn('refresh', login.data)

        totp_login = self.client.post(
            '/api/auth/login/2fa/',
            {
                'challenge': login.data['challenge'],
                'code': pyotp.TOTP(secret).now(),
            },
            format='json',
        )
        self.assertEqual(totp_login.status_code, 200, totp_login.content)
        self.assertIn('access', totp_login.data)

        replay = self.client.post(
            '/api/auth/login/2fa/',
            {
                'challenge': login.data['challenge'],
                'code': pyotp.TOTP(secret).now(),
            },
            format='json',
        )
        self.assertEqual(replay.status_code, 401)

        recovery_login = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'StrongPass123!'},
            format='json',
        )
        recovery_code = enabled.data['recovery_codes'][0]
        recovery_result = self.client.post(
            '/api/auth/login/2fa/',
            {
                'challenge': recovery_login.data['challenge'],
                'recovery_code': recovery_code,
            },
            format='json',
        )
        self.assertEqual(recovery_result.status_code, 200)

        reused_recovery_login = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'StrongPass123!'},
            format='json',
        )
        reused_recovery = self.client.post(
            '/api/auth/login/2fa/',
            {
                'challenge': reused_recovery_login.data['challenge'],
                'recovery_code': recovery_code,
            },
            format='json',
        )
        self.assertEqual(reused_recovery.status_code, 401)

        disable_code = pyotp.TOTP(secret).generate_otp(int(time.time() // 30) + 1)
        disabled = self.client.post(
            '/api/auth/2fa/disable/',
            {'password': 'StrongPass123!', 'code': disable_code},
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {recovery_result.data['access']}",
        )
        self.assertEqual(disabled.status_code, 200, disabled.content)
        invalidated = self.client.get(
            '/api/statements/',
            HTTP_AUTHORIZATION=f"Bearer {recovery_result.data['access']}",
        )
        self.assertEqual(invalidated.status_code, 401)

        final_login = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(final_login.status_code, 200)
        self.assertIn('access', final_login.data)
        self.assertNotIn('mfa_required', final_login.data)

    @override_settings(TWO_FACTOR_ENABLED=True, TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS=2)
    def test_two_factor_challenge_is_consumed_after_failed_attempt_limit(self):
        login = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'StrongPass123!'},
            format='json',
        )
        setup = self.client.post(
            '/api/auth/2fa/setup/',
            {'password': 'StrongPass123!'},
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
        )
        secret = setup.data['secret']
        setup_code = pyotp.TOTP(secret).generate_otp(int(time.time() // 30) - 1)
        enabled = self.client.post(
            '/api/auth/2fa/enable/',
            {'code': setup_code},
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
        )
        self.assertEqual(enabled.status_code, 200)

        challenge = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'StrongPass123!'},
            format='json',
        ).data['challenge']
        for _ in range(2):
            failed = self.client.post(
                '/api/auth/login/2fa/',
                {'challenge': challenge, 'code': 'abcdef'},
                format='json',
            )
            self.assertEqual(failed.status_code, 401)

        after_limit = self.client.post(
            '/api/auth/login/2fa/',
            {'challenge': challenge, 'code': pyotp.TOTP(secret).now()},
            format='json',
        )
        self.assertEqual(after_limit.status_code, 401)

    @override_settings(TWO_FACTOR_ENABLED=False)
    def test_two_factor_can_be_globally_disabled(self):
        login = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'StrongPass123!'},
            format='json',
        )

        self.assertEqual(login.status_code, 200)
        self.assertIn('access', login.data)
        setup = self.client.post(
            '/api/auth/2fa/setup/',
            {},
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
        )
        self.assertEqual(setup.status_code, 404)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='security@example.com',
        PASSWORD_RESET_URL='https://app.example.test/reset-password/',
    )
    def test_password_reset_request_does_not_reveal_account_existence(self):
        existing = self.request_password_reset()
        self.assertEqual(existing.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        unknown = self.request_password_reset('unknown@example.com')
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(unknown.data, existing.data)
        self.assertEqual(len(mail.outbox), 1)

        reset_link = mail.outbox[0].body.split(
            'Reset your password using this link:\n', 1
        )[1].splitlines()[0]
        self.assertTrue(reset_link.startswith('https://app.example.test/'))
        self.assertIn('uid=', reset_link)
        self.assertIn('token=', reset_link)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='security@example.com',
        EMAIL_USE_HTML_TEMPLATES=True,
        PASSWORD_RESET_URL='https://app.example.test/reset-password/',
    )
    def test_password_reset_sends_html_and_text_alternatives(self):
        response = self.request_password_reset()
        self.assertEqual(response.status_code, 200)

        message = mail.outbox[0]
        self.assertIn('Reset your password using this link:', message.body)
        self.assertEqual(len(message.alternatives), 1)
        html_body, content_type = message.alternatives[0]
        self.assertEqual(content_type, 'text/html')
        self.assertIn('Reset password', html_body)
        self.assertIn('href="https://app.example.test/reset-password/#uid=', html_body)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='security@example.com',
        EMAIL_USE_HTML_TEMPLATES=False,
        PASSWORD_RESET_URL='https://app.example.test/reset-password/',
    )
    def test_password_reset_sends_plain_text_when_html_is_disabled(self):
        response = self.request_password_reset()
        self.assertEqual(response.status_code, 200)

        message = mail.outbox[0]
        self.assertEqual(message.content_subtype, 'plain')
        self.assertEqual(message.alternatives, [])

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='security@example.com',
        PASSWORD_RESET_URL='https://app.example.test/reset-password/',
    )
    def test_password_reset_is_single_use_and_revokes_existing_jwts(self):
        login = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(login.status_code, 200)
        old_access = login.data['access']
        old_refresh = login.data['refresh']

        request = self.request_password_reset()
        self.assertEqual(request.status_code, 200)
        reset_link = mail.outbox[0].body.split(
            'Reset your password using this link:\n', 1
        )[1].splitlines()[0]
        query = parse_qs(urlsplit(reset_link).fragment)
        payload = {
            'uid': query['uid'][0],
            'token': query['token'][0],
            'new_password': 'AnotherStrongPass987!',
        }

        reset = self.client.post(
            '/api/auth/password-reset/confirm/', payload, format='json'
        )
        self.assertEqual(reset.status_code, 200, reset.content)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='auth.password_reset.completed',
                actor=self.user,
                target_id=str(self.user.pk),
            ).exists()
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload['new_password']))

        old_access_response = self.client.get(
            '/api/statements/',
            HTTP_AUTHORIZATION=f'Bearer {old_access}',
        )
        self.assertEqual(old_access_response.status_code, 401)

        old_refresh_response = self.client.post(
            '/api/auth/refresh/', {'refresh': old_refresh}, format='json'
        )
        self.assertEqual(old_refresh_response.status_code, 401)

        reused = self.client.post(
            '/api/auth/password-reset/confirm/', payload, format='json'
        )
        self.assertEqual(reused.status_code, 400)

        new_login = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': payload['new_password']},
            format='json',
        )
        self.assertEqual(new_login.status_code, 200)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='security@example.com',
        PASSWORD_RESET_URL='https://app.example.test/reset-password/',
    )
    def test_password_reset_enforces_password_validators(self):
        self.request_password_reset()
        reset_link = mail.outbox[0].body.split(
            'Reset your password using this link:\n', 1
        )[1].splitlines()[0]
        query = parse_qs(urlsplit(reset_link).fragment)

        response = self.client.post(
            '/api/auth/password-reset/confirm/',
            {
                'uid': query['uid'][0],
                'token': query['token'][0],
                'new_password': 'Short1!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('new_password', response.data)
        self.assertTrue(self.user.check_password('StrongPass123!'))

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='security@example.com',
        PASSWORD_RESET_URL='https://app.example.test/reset-password/',
    )
    def test_password_reset_requires_special_character(self):
        self.request_password_reset()
        reset_link = mail.outbox[0].body.split(
            'Reset your password using this link:\n', 1
        )[1].splitlines()[0]
        query = parse_qs(urlsplit(reset_link).fragment)

        response = self.client.post(
            '/api/auth/password-reset/confirm/',
            {
                'uid': query['uid'][0],
                'token': query['token'][0],
                'new_password': 'AnotherStrongPass987',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('new_password', response.data)
        self.assertTrue(self.user.check_password('StrongPass123!'))

    def test_password_reset_rejects_malformed_uid(self):
        response = self.client.post(
            '/api/auth/password-reset/confirm/',
            {
                'uid': 'not-a-valid-user-id',
                'token': 'invalid-token',
                'new_password': 'AnotherStrongPass987!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_password_reset_requests_are_rate_limited(self):
        for _ in range(3):
            response = self.request_password_reset()
            self.assertEqual(response.status_code, 200)

        blocked = self.client.post(
            '/api/auth/password-reset/',
            {'email': 'Alice@Example.com'},
            format='json',
            REMOTE_ADDR='192.0.2.2',
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertIn('Retry-After', blocked)
        self.assertIn('error', json.loads(blocked.content))

    def test_registration_is_rate_limited(self):
        for attempt in range(5):
            response = self.client.post(
                '/api/auth/register/',
                {
                    'username': f'new-user-{attempt}',
                    'email': f'new-user-{attempt}@example.com',
                    'password': 'StrongPass789!',
                },
                format='json',
            )
            self.assertEqual(response.status_code, 201, response.content)

        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'blocked-user',
                'email': 'blocked-user@example.com',
                'password': 'StrongPass789!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='api.rate_limit.exceeded',
                request_route='api/auth/register/',
                outcome='failure',
            ).exists()
        )

    def test_anonymous_requests_are_rate_limited(self):
        for _ in range(60):
            response = self.client.get('/api/statements/')
            self.assertEqual(response.status_code, 401)

        response = self.client.get('/api/statements/')
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)

    def test_authenticated_requests_are_rate_limited(self):
        self.authenticate()

        for _ in range(120):
            response = self.client.get('/api/statements/')
            self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/statements/')
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)

    def test_failed_logins_are_limited_per_ip_and_username(self):
        for _ in range(5):
            response = self.client.post(
                '/api/auth/login/',
                {'username': 'alice', 'password': 'IncorrectPass123!'},
                format='json',
            )
            self.assertEqual(response.status_code, 401)

        blocked = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'IncorrectPass123!'},
            format='json',
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertIn('Retry-After', blocked)
        self.assertIn('error', blocked.data)

        other_username = self.client.post(
            '/api/auth/login/',
            {'username': 'bob', 'password': 'IncorrectPass123!'},
            format='json',
        )
        self.assertEqual(other_username.status_code, 401)

    def test_login_rejects_non_object_payload(self):
        response = self.client.post(
            '/api/auth/login/', ['alice'], format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_successful_login_clears_failed_login_count(self):
        for _ in range(4):
            response = self.client.post(
                '/api/auth/login/',
                {'username': 'alice', 'password': 'IncorrectPass123!'},
                format='json',
            )
            self.assertEqual(response.status_code, 401)

        response = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        for _ in range(5):
            response = self.client.post(
                '/api/auth/login/',
                {'username': 'alice', 'password': 'IncorrectPass123!'},
                format='json',
            )
            self.assertEqual(response.status_code, 401)

    def test_uploads_are_rate_limited_per_user(self):
        self.authenticate()

        for _ in range(5):
            response = self.client.post(
                '/api/statements/upload/', {}, format='multipart'
            )
            self.assertEqual(response.status_code, 400)

        response = self.client.post(
            '/api/statements/upload/', {}, format='multipart'
        )
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)

    def test_protected_endpoints_require_auth(self):
        response = self.client.get('/api/statements/')
        self.assertEqual(response.status_code, 401)

    def test_api_usage_records_authenticated_route_without_query_string(self):
        self.authenticate()

        response = self.client.get('/api/statements/?q=private-value')

        self.assertEqual(response.status_code, 200)
        usage = APIUsageRecord.objects.get(
            user=self.user,
            endpoint='api/statements/',
            method='GET',
            status_code=200,
        )
        self.assertGreaterEqual(usage.duration_ms, 0)
        self.assertNotIn('private-value', usage.endpoint)

    @override_settings(API_USAGE_TRACKING_ENABLED=False)
    def test_api_usage_tracking_can_be_disabled(self):
        response = self.client.get('/api/statements/')

        self.assertEqual(response.status_code, 401)
        self.assertFalse(APIUsageRecord.objects.exists())

    def test_audit_log_records_failed_and_successful_logins(self):
        failed = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'IncorrectPass123!'},
            format='json',
        )
        successful = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'StrongPass123!'},
            format='json',
        )

        self.assertEqual(failed.status_code, 401)
        self.assertEqual(successful.status_code, 200)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='auth.login.failed', outcome='failure'
            ).exists()
        )
        login_event = AuditEvent.objects.get(
            event_type='auth.login.succeeded', actor=self.user
        )
        self.assertEqual(login_event.request_route, 'api/auth/login/')
        self.assertEqual(login_event.details, {})

    def test_upload_rejects_non_pdf_content_even_if_content_type_matches(self):
        self.authenticate()
        fake_pdf = SimpleUploadedFile(
            'fake.pdf',
            b'NOT A REAL PDF CONTENT',
            content_type='application/pdf',
        )

        response = self.client.post(
            '/api/statements/upload/',
            {'file': fake_pdf},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(BankStatement.objects.filter(user=self.user).exists())

    def test_upload_rejects_large_pdf(self):
        self.authenticate()
        payload = b'%PDF-1.4\n' + (b'A' * (10 * 1024 * 1024 + 10))
        fake_pdf = SimpleUploadedFile('large.pdf', payload, content_type='application/pdf')

        response = self.client.post(
            '/api/statements/upload/',
            {'file': fake_pdf},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)

    @patch('statements.views.process_statement_task.delay')
    def test_upload_queues_statement_and_returns_status_url(self, enqueue_task):
        self.authenticate()

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                fake_pdf = SimpleUploadedFile(
                    'statement.pdf',
                    b'%PDF-1.4\n',
                    content_type='application/pdf',
                )
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.post(
                        '/api/statements/upload/',
                        {'file': fake_pdf},
                        format='multipart',
                    )

                self.assertEqual(response.status_code, 202, response.content)
                statement_id = response.data['statement_id']
                enqueue_task.assert_called_once_with(statement_id)
                self.assertEqual(response.data['processing_status'], 'pending')
                self.assertTrue(
                    AuditEvent.objects.filter(
                        event_type='statement.upload.accepted',
                        actor=self.user,
                        target_id=str(statement_id),
                    ).exists()
                )
                self.assertEqual(
                    response.data['status_url'],
                    f'/api/statements/{statement_id}/status/',
                )

                status_response = self.client.get(response.data['status_url'])
                self.assertEqual(status_response.status_code, 200)
                self.assertEqual(
                    status_response.data['processing_status'], 'pending'
                )

    @override_settings(GEMINI_MONTHLY_LIMIT_PER_USER=1)
    @patch('statements.views.process_statement_task.delay')
    def test_monthly_gemini_limit_rejects_excess_statement_uploads(self, enqueue_task):
        self.authenticate()

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                with self.captureOnCommitCallbacks(execute=True):
                    first = self.client.post(
                        '/api/statements/upload/',
                        {
                            'file': SimpleUploadedFile(
                                'first.pdf',
                                b'%PDF-1.4\n',
                                content_type='application/pdf',
                            )
                        },
                        format='multipart',
                    )

                second = self.client.post(
                    '/api/statements/upload/',
                    {
                        'file': SimpleUploadedFile(
                            'second.pdf',
                            b'%PDF-1.4\n',
                            content_type='application/pdf',
                        )
                    },
                    format='multipart',
                )

        self.assertEqual(first.status_code, 202, first.content)
        self.assertEqual(second.status_code, 429, second.content)
        self.assertIn('Retry-After', second)
        self.assertEqual(second.data['used'], 1)
        enqueue_task.assert_called_once_with(first.data['statement_id'])

    @patch('statements.services.types.Part.from_bytes', return_value='pdf part')
    @patch('statements.services._get_gemini_client')
    def test_gemini_usage_records_tokens_and_duration(self, get_client, from_bytes):
        response = SimpleNamespace(
            text='{"ai_evaluation":"Summary","transactions":[]}',
            usage_metadata=SimpleNamespace(
                prompt_token_count=12,
                candidates_token_count=7,
                total_token_count=19,
            ),
        )
        get_client.return_value.models.generate_content.return_value = response

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                statement = BankStatement.objects.create(
                    user=self.user,
                    file=SimpleUploadedFile(
                        'usage.pdf', b'%PDF-1.4\n', content_type='application/pdf'
                    ),
                )
                process_pdf_statement_with_gemini(statement)

        usage = GeminiUsageRecord.objects.get(statement=statement)
        self.assertEqual(usage.user, self.user)
        self.assertEqual(usage.model_name, 'gemini-3.5-flash-lite')
        self.assertEqual(usage.status, 'succeeded')
        self.assertEqual(usage.prompt_tokens, 12)
        self.assertEqual(usage.completion_tokens, 7)
        self.assertEqual(usage.total_tokens, 19)
        self.assertGreaterEqual(usage.duration_ms, 0)
        from_bytes.assert_called_once()

    @patch('statements.services.types.Part.from_bytes', return_value='pdf part')
    @patch('statements.services._get_gemini_client')
    def test_failed_gemini_call_is_recorded(self, get_client, from_bytes):
        get_client.return_value.models.generate_content.side_effect = TimeoutError

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                statement = BankStatement.objects.create(
                    user=self.user,
                    file=SimpleUploadedFile(
                        'failed-usage.pdf',
                        b'%PDF-1.4\n',
                        content_type='application/pdf',
                    ),
                )
                with self.assertRaises(TimeoutError):
                    process_pdf_statement_with_gemini(statement)

        usage = GeminiUsageRecord.objects.get(statement=statement)
        self.assertEqual(usage.status, 'failed')
        self.assertEqual(usage.error_type, 'TimeoutError')
        self.assertIsNone(usage.total_tokens)

    def test_user_cannot_access_another_users_statement_status(self):
        self.authenticate()
        other_statement = BankStatement.objects.create(
            user=self.other_user,
            file='statements/other/private.pdf',
        )

        response = self.client.get(
            f'/api/statements/{other_statement.pk}/status/'
        )

        self.assertEqual(response.status_code, 404)

    @patch('statements.tasks.process_pdf_statement_with_gemini')
    def test_statement_task_marks_statement_completed(self, process_statement):
        statement = BankStatement.objects.create(
            user=self.user,
            file='statements/user/queued.pdf',
        )

        process_statement_task.apply(args=[statement.pk], throw=True)

        statement.refresh_from_db()
        self.assertEqual(statement.processing_status, 'completed')
        self.assertTrue(statement.is_processed)
        self.assertEqual(statement.processing_error, '')
        process_statement.assert_called_once()
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='statement.processing.completed',
                actor=self.user,
                target_id=str(statement.pk),
            ).exists()
        )

    def test_audit_log_keeps_account_deletion_event(self):
        self.authenticate()
        deleted_user_id = self.user.pk

        response = self.client.delete(
            '/api/auth/account/',
            {'password': 'StrongPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        event = AuditEvent.objects.get(
            event_type='account.deleted',
            target_type='user',
            target_id=str(deleted_user_id),
        )
        self.assertIsNone(event.actor_id)

    def test_user_cannot_access_other_users_statements(self):
        self.authenticate('alice', 'StrongPass123!')
        other_statement = BankStatement.objects.create(
            user=self.other_user,
            file='statements/other/test.pdf',
        )
        response = self.client.delete(f'/api/statements/{other_statement.id}/')
        self.assertEqual(response.status_code, 404)

    def test_bulk_delete_only_removes_current_users_statements(self):
        self.authenticate()
        self.user_statement = BankStatement.objects.create(
            user=self.user,
            file='statements/user/test.pdf',
        )
        BankStatement.objects.create(
            user=self.other_user,
            file='statements/other/test.pdf',
        )

        response = self.client.delete('/api/statements/delete-all/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(BankStatement.objects.filter(user=self.user).exists())
        self.assertTrue(BankStatement.objects.filter(user=self.other_user).exists())

    def test_transactions_are_scoped_to_owner(self):
        self.authenticate()
        statement = BankStatement.objects.create(
            user=self.user,
            file='statements/user/test.pdf',
        )
        Transaction.objects.create(
            statement=statement,
            date='2024-01-01',
            description='Lunch',
            amount='12.50',
            payee_payer='Cafe',
            transaction_type='CARD_PAYMENT',
            category='Dining Out & Cafes',
        )

        response = self.client.get('/api/transactions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['description'], 'Lunch')
        self.assertEqual(len(response.data), 1)

    def test_statement_and_transaction_detail_endpoints_work(self):
        self.authenticate()
        statement = BankStatement.objects.create(
            user=self.user,
            file='statements/user/detail.pdf',
            processing_status='completed',
            is_processed=True,
            ai_evaluation='Healthy budget.',
        )
        transaction = Transaction.objects.create(
            statement=statement,
            date='2024-01-02',
            description='Salary deposit',
            amount='2500.00',
            payee_payer='Employer',
            transaction_type='INCOME',
            category='Salary & Main Income',
        )

        statement_response = self.client.get(f'/api/statements/{statement.id}/')
        self.assertEqual(statement_response.status_code, 200)
        self.assertEqual(statement_response.data['id'], statement.id)
        self.assertEqual(statement_response.data['transactions'][0]['id'], transaction.id)

        transaction_response = self.client.get(f'/api/transactions/{transaction.id}/')
        self.assertEqual(transaction_response.status_code, 200)
        self.assertEqual(transaction_response.data['id'], transaction.id)
        self.assertEqual(transaction_response.data['description'], 'Salary deposit')

    def test_transactions_support_filters_and_sorting(self):
        self.authenticate()
        statement = BankStatement.objects.create(
            user=self.user,
            file='statements/user/filter.pdf',
        )
        Transaction.objects.create(
            statement=statement,
            date='2024-01-01',
            description='Groceries',
            amount='25.00',
            payee_payer='Supermarket',
            transaction_type='CARD_PAYMENT',
            category='Groceries & Food',
        )
        Transaction.objects.create(
            statement=statement,
            date='2024-01-05',
            description='Rental income',
            amount='1500.00',
            payee_payer='Tenant',
            transaction_type='INCOME',
            category='Salary & Main Income',
        )

        response = self.client.get(
            '/api/transactions/?category=Groceries%20%26%20Food&ordering=-date'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['description'], 'Groceries')
