import logging

from django.db import Error, connection
from django.http import HttpResponse, JsonResponse
from django.urls import reverse

logger = logging.getLogger(__name__)


def robots_txt(request):
    """Allow crawling and advertise the configured site's sitemap URL."""
    from wagtail.models import Site

    site = Site.find_for_request(request)
    default_port = 443 if request.scheme == "https" else 80
    port = "" if site.port == default_port else f":{site.port}"
    sitemap_url = (
        f"{request.scheme}://{site.hostname}{port}{reverse('sitemap')}"
    )
    content = f"User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n"
    return HttpResponse(
        content,
        content_type="text/plain; charset=utf-8",
    )


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
