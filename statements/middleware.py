import json
import hashlib
import hmac
import math
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.throttling import BaseThrottle
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_api_settings
from rest_framework_simplejwt.tokens import AccessToken


class APIRateLimitMiddleware:
    endpoint_rules = {
        ('POST', '/api/auth/register/'): ('registration', 'ip'),
        ('POST', '/api/auth/login/'): ('login', 'ip'),
        ('POST', '/api/auth/password-reset/'): ('password_reset', 'ip'),
        ('POST', '/api/auth/password-reset/confirm/'): ('password_reset_confirm', 'ip'),
        ('POST', '/api/statements/upload/'): ('upload', 'user'),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info.startswith('/api/'):
            limited_response = self._throttle_request(request)
            if limited_response is not None:
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
            return self._check_password_reset_email_limit(request)

        return None

    @staticmethod
    def _check_password_reset_email_limit(request):
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
            'password_reset_email', f'email:{email.strip().casefold()}'
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