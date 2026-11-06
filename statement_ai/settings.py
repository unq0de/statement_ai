import os
from pathlib import Path
from datetime import timedelta
from urllib.parse import urlsplit

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key')
DEBUG = os.environ.get('DEBUG', '0') == '1'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
REDIS_URL = os.environ.get('REDIS_URL')

# GDPR: max. number of days a bank statement (incl. PDF + transactions) is
# retained before it becomes eligible for deletion by the
# `delete_expired_data` management command.
DATA_RETENTION_DAYS = int(os.environ.get('DATA_RETENTION_DAYS') or 365)

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
        'DIRS': [],
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

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
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
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL') or 'webmaster@localhost'
PASSWORD_RESET_TIMEOUT = int(os.environ.get('PASSWORD_RESET_TIMEOUT') or 3600)
PASSWORD_RESET_URL = os.environ.get('PASSWORD_RESET_URL') or (
    'http://localhost:3000/reset-password/' if DEBUG else ''
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

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'CHECK_REVOKE_TOKEN': True,
}