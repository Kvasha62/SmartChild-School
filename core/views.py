import logging

from django.db import Error, connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def live(request):
    """Indicate that the Django process can respond; this does not check the DB."""
    return JsonResponse({"status": "ok"})


def ready(request):
    """Indicate readiness only when PostgreSQL accepts a simple query."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Error:
        logger.warning("Readiness check failed", exc_info=True)
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
