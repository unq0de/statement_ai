import json
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import BankStatement, Transaction

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

    def test_register_and_login_success(self):
        response = self.client.post(
            '/api/auth/register/',
            {'username': 'charlie', 'email': 'charlie@example.com', 'password': 'StrongPass789!'},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)

        login = self.client.post(
            '/api/auth/login/',
            {'username': 'charlie', 'password': 'StrongPass789!'},
            format='json',
        )
        self.assertEqual(login.status_code, 200, login.content)
        self.assertIn('access', login.data)
        self.assertIn('refresh', login.data)

    def test_registration_rejects_password_shorter_than_twelve_characters(self):
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
