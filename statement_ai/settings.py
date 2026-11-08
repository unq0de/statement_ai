import os
import base64
import hashlib
from pathlib import Path
from datetime import timedelta
from urllib.parse import urlsplit

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key')
DEBUG = os.environ.get('DEBUG', '0') == '1'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
REDIS_URL = os.environ.get('REDIS_URL')
CELERY_BROKER_URL = os.environ.get(
    'CELERY_BROKER_URL', 'redis://redis:6379/0'
)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# GDPR: max. number of days a bank statement (incl. PDF + transactions) is
# retained before it becomes eligible for deletion by the
# `delete_expired_data` management command.
DATA_RETENTION_DAYS = int(os.environ.get('DATA_RETENTION_DAYS') or 365)
API_USAGE_TRACKING_ENABLED = os.environ.get(
    'API_USAGE_TRACKING_ENABLED', '1'
).strip().lower() in {'1', 'true', 'yes', 'on'}
API_USAGE_RETENTION_DAYS = int(os.environ.get('API_USAGE_RETENTION_DAYS', '90'))
AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', '365'))
GEMINI_MONTHLY_LIMIT_PER_USER = int(
    os.environ.get('GEMINI_MONTHLY_LIMIT_PER_USER', '0')
)
TWO_FACTOR_ENABLED = os.environ.get('TWO_FACTOR_ENABLED', '1').strip().lower() in {
    '1', 'true', 'yes', 'on'
}
TWO_FACTOR_ISSUER = os.environ.get('TWO_FACTOR_ISSUER', 'Statement AI')
TWO_FACTOR_ENCRYPTION_KEY = os.environ.get('TWO_FACTOR_ENCRYPTION_KEY') or (
    base64.urlsafe_b64encode(
        hashlib.sha256(f'{SECRET_KEY}:statement-ai-two-factor'.encode()).digest()
    ).decode()
)
TWO_FACTOR_CHALLENGE_TIMEOUT_SECONDS = int(
    os.environ.get('TWO_FACTOR_CHALLENGE_TIMEOUT_SECONDS', '300')
)
TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS = int(
    os.environ.get('TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS', '5')
)
TWO_FACTOR_RECOVERY_CODE_COUNT = int(
    os.environ.get('TWO_FACTOR_RECOVERY_CODE_COUNT', '10')
)
if API_USAGE_RETENTION_DAYS < 1:
    raise RuntimeError('API_USAGE_RETENTION_DAYS must be at least 1.')
if AUDIT_LOG_RETENTION_DAYS < 1:
    raise RuntimeError('AUDIT_LOG_RETENTION_DAYS must be at least 1.')
if GEMINI_MONTHLY_LIMIT_PER_USER < 0:
    raise RuntimeError('GEMINI_MONTHLY_LIMIT_PER_USER cannot be negative.')
if TWO_FACTOR_CHALLENGE_TIMEOUT_SECONDS < 30:
    raise RuntimeError('TWO_FACTOR_CHALLENGE_TIMEOUT_SECONDS must be at least 30.')
if TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS < 1:
    raise RuntimeError('TWO_FACTOR_MAX_CHALLENGE_ATTEMPTS must be at least 1.')
if TWO_FACTOR_RECOVERY_CODE_COUNT < 1:
    raise RuntimeError('TWO_FACTOR_RECOVERY_CODE_COUNT must be at least 1.')

if not DEBUG:
    if not SECRET_KEY or SECRET_KEY == 'fallback-secret-key':
        raise RuntimeError("SECRET_KEY must be set via environment variable in production.")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY must be set in production.")
    ALLOWED_HOSTS = [h for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h]
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [o for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if o]
else:
    ALLOWED_HOSTS = ['*']
    CORS_ALLOW_ALL_ORIGINS = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    # Local apps
    'statements',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'statements.middleware.APIUsageTrackingMiddleware',
    'statements.middleware.APIRateLimitMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'statement_ai.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'statement_ai.wsgi.application'

# --------------------------------------------------------------------------
# Database
#
# Two modes, controlled by DB_ENGINE:
#   - "local"    (default) -> the docker-compose "db" Postgres container
#   - "supabase" -> a hosted Supabase Postgres instance
#
# Both are plain PostgreSQL under the hood, so the same Django models /
# migrations work unchanged either way - only the connection details differ.
# --------------------------------------------------------------------------
DB_ENGINE = os.environ.get('DB_ENGINE', 'local')

if DB_ENGINE == 'supabase':
    # Values come from Supabase Dashboard -> Project Settings -> Database
    # -> "Connection parameters" (use the "Session pooler" or "Transaction
    # pooler" host for most deployments; the direct host also works for
    # low-traffic / single-instance setups).
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('SUPABASE_DB_NAME', 'postgres'),
            'USER': os.environ.get('SUPABASE_DB_USER'),
            'PASSWORD': os.environ.get('SUPABASE_DB_PASSWORD'),
            'HOST': os.environ.get('SUPABASE_DB_HOST'),
            'PORT': os.environ.get('SUPABASE_DB_PORT', '5432'),
            'OPTIONS': {
                # Supabase requires TLS on all connections.
                'sslmode': os.environ.get('SUPABASE_DB_SSLMODE', 'require'),
            },
            'CONN_MAX_AGE': int(os.environ.get('SUPABASE_DB_CONN_MAX_AGE', '60')),
        }
    }
    if not DEBUG and not all([
        DATABASES['default']['USER'],
        DATABASES['default']['PASSWORD'],
        DATABASES['default']['HOST'],
    ]):
        raise RuntimeError(
            "DB_ENGINE=supabase requires SUPABASE_DB_HOST, SUPABASE_DB_USER "
            "and SUPABASE_DB_PASSWORD to be set."
        )
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'statement_ai_db'),
            'USER': os.environ.get('POSTGRES_USER', 'statement_ai_user'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'statement_ai_password'),
            'HOST': os.environ.get('POSTGRES_HOST', 'db'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }

PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', '12'))
if PASSWORD_MIN_LENGTH < 1:
    raise RuntimeError('PASSWORD_MIN_LENGTH must be at least 1.')


def _password_check_enabled(name):
    return os.environ.get(name, '1').strip().lower() in {'1', 'true', 'yes', 'on'}


AUTH_PASSWORD_VALIDATORS = []
if _password_check_enabled('PASSWORD_CHECK_USER_ATTRIBUTES'):
    AUTH_PASSWORD_VALIDATORS.append(
        {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}
    )
AUTH_PASSWORD_VALIDATORS.append({
    'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    'OPTIONS': {'min_length': PASSWORD_MIN_LENGTH},
})
if _password_check_enabled('PASSWORD_CHECK_COMMON'):
    AUTH_PASSWORD_VALIDATORS.append(
        {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}
    )
if _password_check_enabled('PASSWORD_CHECK_NUMERIC'):
    AUTH_PASSWORD_VALIDATORS.append(
        {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}
    )
if _password_check_enabled('PASSWORD_CHECK_SPECIAL_CHARACTERS'):
    AUTH_PASSWORD_VALIDATORS.append(
        {'NAME': 'statements.password_validators.SpecialCharacterValidator'}
    )

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'statements.authentication.SecurityVersionJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # Ensures unhandled exceptions (e.g. a refresh token pointing at a
    # since-deleted user) come back as a clean JSON error instead of a
    # raw Django debug page / opaque 500. See statements/exceptions.py.
    'EXCEPTION_HANDLER': 'statements.exceptions.custom_exception_handler',
    'NUM_PROXIES': int(os.environ.get('NUM_PROXIES', '0')),
}

API_RATE_LIMITS = {
    'anonymous': {'limit': 60, 'window_seconds': 60},
    'authenticated': {'limit': 120, 'window_seconds': 60},
    'registration': {'limit': 5, 'window_seconds': 60 * 60},
    'registration_confirmation': {'limit': 10, 'window_seconds': 60 * 60},
    'registration_confirmation_email': {'limit': 3, 'window_seconds': 60 * 60},
    'two_factor_management': {'limit': 10, 'window_seconds': 60 * 60},
    'two_factor_login': {'limit': 10, 'window_seconds': 60 * 60},
    'login': {'limit': 10, 'window_seconds': 60},
    'password_reset': {'limit': 5, 'window_seconds': 60 * 60},
    'password_reset_email': {'limit': 3, 'window_seconds': 60 * 60},
    'password_reset_confirm': {'limit': 10, 'window_seconds': 60 * 60},
    'upload': {'limit': 5, 'window_seconds': 60 * 60},
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

if REDIS_URL:
    CACHES['default'] = {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 2,
            'SOCKET_TIMEOUT': 2,
        },
        'KEY_PREFIX': 'statement_ai',
    }
elif not DEBUG:
    raise RuntimeError('REDIS_URL must be set in production for shared rate limits.')

EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND') or (
    'django.core.mail.backends.console.EmailBackend'
    if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT') or 587)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '').lower() in {'1', 'true', 'yes'}
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', '').lower() in {'1', 'true', 'yes'}
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT') or 10)
EMAIL_USE_HTML_TEMPLATES = os.environ.get(
    'EMAIL_USE_HTML_TEMPLATES', '0'
).strip().lower() in {'1', 'true', 'yes', 'on'}
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL') or 'webmaster@localhost'
PASSWORD_RESET_TIMEOUT = int(os.environ.get('PASSWORD_RESET_TIMEOUT') or 3600)
PASSWORD_RESET_URL = os.environ.get('PASSWORD_RESET_URL') or (
    'http://localhost:3000/reset-password/' if DEBUG else ''
)
REGISTRATION_CONFIRMATION_URL = os.environ.get('REGISTRATION_CONFIRMATION_URL') or (
    'http://localhost:3000/confirm-email/' if DEBUG else ''
)

if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise RuntimeError('EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled.')

if not DEBUG:
    if not EMAIL_HOST or DEFAULT_FROM_EMAIL == 'webmaster@localhost':
        raise RuntimeError('EMAIL_HOST and DEFAULT_FROM_EMAIL must be set in production.')
    if not EMAIL_USE_TLS and not EMAIL_USE_SSL:
        raise RuntimeError('EMAIL_USE_TLS or EMAIL_USE_SSL must be enabled in production.')
    reset_url = urlsplit(PASSWORD_RESET_URL)
    if reset_url.scheme != 'https' or not reset_url.netloc:
        raise RuntimeError('PASSWORD_RESET_URL must be an absolute HTTPS URL in production.')
    confirmation_url = urlsplit(REGISTRATION_CONFIRMATION_URL)
    if confirmation_url.scheme != 'https' or not confirmation_url.netloc:
        raise RuntimeError(
            'REGISTRATION_CONFIRMATION_URL must be an absolute HTTPS URL in production.'
        )

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'CHECK_REVOKE_TOKEN': True,
}