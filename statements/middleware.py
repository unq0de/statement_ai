import json
import hashlib
import hmac
import logging
import math
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.throttling import BaseThrottle
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_api_settings
from rest_framework_simplejwt.tokens import AccessToken

from .audit import record_audit_event

logger = logging.getLogger(__name__)


class APIUsageTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            not settings.API_USAGE_TRACKING_ENABLED
            or not request.path_info.startswith('/api/')
        ):
            return self.get_response(request)

        started_at = time.monotonic()
        try:
            response = self.get_response(request)
        except Exception:
            self._record(request, 500, started_at)
            raise

        self._record(request, response.status_code, started_at)
        return response

    @staticmethod
    def _record(request, status_code, started_at):
        from .models import APIUsageRecord

        try:
            user = getattr(request, 'user', None)
            user_state = getattr(user, '_state', None)
            if (
                not getattr(user, 'is_authenticated', False)
                or getattr(user, 'pk', None) is None
                or getattr(user_state, 'adding', False)
            ):
                user_id = APIRateLimitMiddleware._get_access_token_user_id(request)
                user = None
                if user_id is not None:
                    user = get_user_model().objects.filter(pk=user_id).only('pk').first()

            route = getattr(getattr(request, 'resolver_match', None), 'route', None)
            endpoint = route or 'unmatched'
            try:
                request_size = max(0, int(request.META.get('CONTENT_LENGTH') or 0))
            except (TypeError, ValueError):
                request_size = 0

            APIUsageRecord.objects.create(
                user=user,
                endpoint=endpoint[:255],
                method=request.method[:10],
                status_code=status_code,
                duration_ms=max(0, int((time.monotonic() - started_at) * 1000)),
                request_size_bytes=request_size,
            )
        except Exception:
            logger.exception('Could not save API usage record for %s.', request.path_info)


class APIRateLimitMiddleware:
    endpoint_rules = {
        ('POST', '/api/auth/register/'): ('registration', 'ip'),
        ('POST', '/api/auth/register/confirm/'): ('registration_confirmation', 'ip'),
        ('POST', '/api/auth/register/resend-confirmation/'): ('registration_confirmation', 'ip'),
        ('POST', '/api/auth/login/'): ('login', 'ip'),
        ('POST', '/api/auth/password-reset/'): ('password_reset', 'ip'),
        ('POST', '/api/auth/password-reset/confirm/'): ('password_reset_confirm', 'ip'),
        ('POST', '/api/auth/login/2fa/'): ('two_factor_login', 'ip'),
        ('POST', '/api/auth/2fa/setup/'): ('two_factor_management', 'user'),
        ('POST', '/api/auth/2fa/enable/'): ('two_factor_management', 'user'),
        ('POST', '/api/auth/2fa/disable/'): ('two_factor_management', 'user'),
        ('POST', '/api/auth/2fa/recovery-codes/'): ('two_factor_management', 'user'),
        ('POST', '/api/statements/upload/'): ('upload', 'user'),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info.startswith('/api/'):
            limited_response = self._throttle_request(request)
            if limited_response is not None:
                user_id = self._get_access_token_user_id(request)
                actor = None
                if user_id is not None:
                    actor = get_user_model().objects.filter(pk=user_id).only('pk').first()
                record_audit_event(
                    'api.rate_limit.exceeded',
                    request=request,
                    actor=actor,
                    outcome='failure',
                    details={'status_code': limited_response.status_code},
                )
                return limited_response

        return self.get_response(request)

    def _throttle_request(self, request):
        client_ip = BaseThrottle().get_ident(request)
        user_id = self._get_access_token_user_id(request)
        identity = f'user:{user_id}' if user_id is not None else f'ip:{client_ip}'
        global_scope = 'authenticated' if user_id is not None else 'anonymous'

        response = self._check_limit(global_scope, identity)
        if response is not None:
            return response

        endpoint_rule = self.endpoint_rules.get((request.method, request.path_info))
        if endpoint_rule is None:
            return None

        scope, identity_type = endpoint_rule
        if identity_type == 'user' and user_id is not None:
            endpoint_identity = f'user:{user_id}'
        else:
            endpoint_identity = f'ip:{client_ip}'

        response = self._check_limit(scope, endpoint_identity)
        if response is not None:
            return response

        if scope == 'password_reset':
            return self._check_email_limit(request, 'password_reset_email')
        if (
            scope == 'registration_confirmation'
            and request.path_info.endswith('/resend-confirmation/')
        ):
            return self._check_email_limit(
                request, 'registration_confirmation_email'
            )

        return None

    @staticmethod
    def _check_email_limit(request, scope):
        if request.content_type != 'application/json':
            return None

        try:
            if int(request.META.get('CONTENT_LENGTH') or 0) > 4096:
                return None
            payload = json.loads(request.body)
        except (UnicodeDecodeError, ValueError):
            return None

        email = payload.get('email') if isinstance(payload, dict) else None
        if not isinstance(email, str) or not email.strip():
            return None

        return APIRateLimitMiddleware._check_limit(
            scope, f'email:{email.strip().casefold()}'
        )

    @staticmethod
    def _get_access_token_user_id(request):
        authorization = request.META.get('HTTP_AUTHORIZATION', '').split()
        valid_header_types = {header.lower() for header in jwt_api_settings.AUTH_HEADER_TYPES}
        if len(authorization) != 2 or authorization[0].lower() not in valid_header_types:
            return None

        try:
            token = AccessToken(authorization[1])
        except (TokenError, TypeError, ValueError):
            return None

        return token.get(jwt_api_settings.USER_ID_CLAIM)

    @staticmethod
    def _check_limit(scope, identity):
        rule = settings.API_RATE_LIMITS[scope]
        now = time.time()
        window_start = math.floor(now / rule['window_seconds'])
        window_end = (window_start + 1) * rule['window_seconds']
        retry_after = max(1, math.ceil(window_end - now))

        digest = hmac.new(
            str(settings.SECRET_KEY).encode(),
            identity.encode(),
            hashlib.sha256,
        ).hexdigest()
        cache_key = f'api_rate_{scope}_{digest}_{window_start}'

        if cache.add(cache_key, 1, timeout=retry_after + 1):
            request_count = 1
        else:
            try:
                request_count = cache.incr(cache_key)
            except ValueError:
                cache.add(cache_key, 1, timeout=retry_after + 1)
                request_count = 1

        if request_count <= rule['limit']:
            return None

        return JsonResponse(
            {'error': 'Rate limit exceeded.'},
            status=429,
            headers={'Retry-After': str(retry_after)},
        )