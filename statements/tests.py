from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import BankStatement, Transaction

User = get_user_model()


class StatementApiTests(TestCase):
    def setUp(self):
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
