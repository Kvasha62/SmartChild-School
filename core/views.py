from django.db import DatabaseError, connection
from django.http import JsonResponse


def live(request):
    """Indicate that the Django process can respond; this does not check the DB."""
    return JsonResponse({"status": "ok"})


def ready(request):
    """Indicate readiness only when PostgreSQL accepts a simple query."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
