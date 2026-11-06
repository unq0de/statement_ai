import hashlib
import hmac
import math
import time

from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import BaseThrottle

FAILED_LOGIN_LIMIT = 5
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60


def _login_failure_cache_keys(request, username):
    if request is None or not isinstance(username, str) or not username.strip():
        return None, None

    client_ip = BaseThrottle().get_ident(request)
    if not client_ip:
        return None, None

    identity = f'{client_ip}\0{username.strip().casefold()}'
    digest = hmac.new(
        str(settings.SECRET_KEY).encode(), identity.encode(), hashlib.sha256
    ).hexdigest()
    key_prefix = f'login_failure_{digest}'
    return f'{key_prefix}_count', f'{key_prefix}_started'


class FailedLoginThrottle(BaseThrottle):
    def allow_request(self, request, view):
        request_data = request.data
        count_key, started_key = _login_failure_cache_keys(
            request,
            request_data.get('username') if hasattr(request_data, 'get') else None,
        )
        self.wait_seconds = None
        if count_key is None:
            return True

        if cache.get(count_key, 0) < FAILED_LOGIN_LIMIT:
            return True

        started = cache.get(started_key)
        self.wait_seconds = (
            FAILED_LOGIN_WINDOW_SECONDS
            if started is None
            else max(
                1,
                math.ceil(
                    FAILED_LOGIN_WINDOW_SECONDS - (time.time() - started)
                ),
            )
        )
        return False

    def wait(self):
        return self.wait_seconds


def record_failed_login(request, username):
    count_key, started_key = _login_failure_cache_keys(request, username)
    if count_key is None:
        return

    if cache.add(count_key, 1, timeout=FAILED_LOGIN_WINDOW_SECONDS):
        cache.add(started_key, time.time(), timeout=FAILED_LOGIN_WINDOW_SECONDS)
        return

    try:
        cache.incr(count_key)
    except ValueError:
        if cache.add(count_key, 1, timeout=FAILED_LOGIN_WINDOW_SECONDS):
            cache.add(started_key, time.time(), timeout=FAILED_LOGIN_WINDOW_SECONDS)


def clear_failed_logins(request, username):
    count_key, started_key = _login_failure_cache_keys(request, username)
    if count_key is not None:
        cache.delete_many((count_key, started_key))