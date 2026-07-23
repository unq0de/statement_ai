import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Project-wide DRF exception handler.

    Ensures every API error - including ones DRF itself doesn't normally
    handle - comes back as a clean `{"error": "..."}` JSON response instead
    of leaking a raw Django debug traceback (or an opaque 500) to the client.

    Concretely this fixes cases like `POST /api/auth/refresh/` raising
    `User.DoesNotExist`: the refresh token is cryptographically valid but
    references a user that no longer exists in the currently connected
    database (e.g. after switching DB_ENGINE, resetting the DB, or the
    account having been deleted). That's a client-side "your token is no
    longer valid" situation, not a server bug, so it's surfaced as a normal
    401 rather than a 500.
    """
    # Let DRF handle everything it already knows about (ValidationError,
    # NotAuthenticated, PermissionDenied, Http404, simplejwt's
    # InvalidToken/TokenError, etc.) first.
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    # A `<Model>.DoesNotExist` (e.g. raised by simplejwt when the user
    # embedded in a refresh/access token no longer exists) is a
    # `django.core.exceptions.ObjectDoesNotExist` subclass but isn't caught
    # by DRF's default handler above, so it would otherwise bubble up as a
    # raw 500. Treat it as an authentication problem.
    if isinstance(exc, (ObjectDoesNotExist, Http404)):
        logger.info("Resource referenced by request no longer exists: %s", exc)
        return Response(
            {"error": "Invalid or expired token."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Anything else is a genuine unexpected server error. Log it with the
    # full traceback for debugging, but never leak internal details to the
    # client - keep the response generic and consistent with the rest of
    # the API's error format.
    logger.exception("Unhandled exception in API view", exc_info=exc)
    return Response(
        {"error": "An unexpected server error occurred."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )