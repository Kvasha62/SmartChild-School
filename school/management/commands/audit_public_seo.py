"""Read-only audit of public Wagtail pages for common SEO/content issues."""

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from html.parser import HTMLParser
from urllib.parse import urlsplit

from django.core.management.base import BaseCommand
from wagtail.models import Page

from school.models import LessonPage


class _ImageMarkupParser(HTMLParser):
    """Collect image markup and whether a contextual alt attribute is present."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []

    def handle_starttag(self, tag, attrs):
        self._record_image(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self._record_image(tag, attrs)

    def _record_image(self, tag, attrs):
        attributes = dict(attrs)
        if tag not in {"embed", "img"}:
            return
        if tag == "embed" and attributes.get("embedtype") != "image":
            return

        self.images.append(
            {
                "has_alt": "alt" in attributes,
                "alt": attributes.get("alt") or "",
            }
        )


def _public_path(page):
    """Return a site-relative URL path without requiring a public domain."""
    try:
        public_url = page.url
    except (AttributeError, LookupError, ValueError):
        public_url = None

    if public_url:
        path = urlsplit(public_url).path
        if path:
            return path
    return page.url_path or "/"


def _iter_rich_text_sources(value, location):
    """Yield raw rich-text source strings nested inside Wagtail StreamField values."""
    source = getattr(value, "source", None)
    if isinstance(source, str):
        yield location, source
        return

    if isinstance(value, (str, bytes, bytearray)) or value is None:
        return

    if hasattr(value, "block_type") and hasattr(value, "value"):
        yield from _iter_rich_text_sources(
            value.value, f"{location}.{value.block_type}"
        )
        return

    if isinstance(value, Mapping) or callable(getattr(value, "items", None)):
        for key, child in value.items():
            yield from _iter_rich_text_sources(child, f"{location}.{key}")
        return

    if isinstance(value, Iterable):
        for index, child in enumerate(value):
            yield from _iter_rich_text_sources(child, f"{location}[{index}]")


def audit_pages(pages):
    """Return a stable, JSON-serializable inventory and review findings."""
    pages = list(pages)
    inventory = []
    findings = []
    titles = defaultdict(list)
    descriptions = defaultdict(list)

    def add_finding(code, path, detail, severity="review"):
        findings.append(
            {
                "code": code,
                "severity": severity,
                "path": path,
                "detail": detail,
            }
        )

    for page in pages:
        path = _public_path(page)
        title = (getattr(page, "seo_title", "") or page.title or "").strip()
        explicit_description = (
            getattr(page, "search_description", "") or ""
        ).strip()
        intro = (getattr(page, "intro", "") or "").strip()

        if title:
            titles[" ".join(title.split()).casefold()].append((path, title))

        if explicit_description:
            description_key = " ".join(explicit_description.split()).casefold()
            descriptions[description_key].append((path, explicit_description))

        image_count = 0
        body = getattr(page, "body", None)
        if body is not None:
            for location, source in _iter_rich_text_sources(body, "body"):
                parser = _ImageMarkupParser()
                parser.feed(source)
                image_count += len(parser.images)
                for index, image in enumerate(parser.images, start=1):
                    if not image["has_alt"]:
                        add_finding(
                            "image_alt_needs_review",
                            path,
                            (
                                f"{location} image {index} has no explicit alt "
                                "attribute; review its contextual description or "
                                "mark it decorative in Wagtail."
                            ),
                        )

        inventory.append(
            {
                "path": path,
                "title": page.title,
                "page_type": type(page).__name__,
                "has_custom_seo_title": bool(
                    (getattr(page, "seo_title", "") or "").strip()
                ),
                "has_explicit_search_description": bool(explicit_description),
                "has_intro": bool(intro),
                "image_count": image_count,
            }
        )

        if isinstance(page, LessonPage) and not explicit_description and not intro:
            add_finding(
                "generic_meta_description_fallback",
                path,
                (
                    "This lesson has neither an explicit Wagtail SEO description "
                    "nor an intro, so the site-wide generic meta description is used."
                ),
            )

    for group in titles.values():
        if len(group) < 2:
            continue
        paths = [path for path, _title in group]
        for path, title in group:
            other_paths = [other for other in paths if other != path]
            add_finding(
                "duplicate_effective_title",
                path,
                f"Effective SEO title {title!r} is also used at: {', '.join(other_paths)}.",
            )

    for group in descriptions.values():
        if len(group) < 2:
            continue
        paths = [path for path, _description in group]
        for path, description in group:
            other_paths = [other for other in paths if other != path]
            add_finding(
                "duplicate_explicit_search_description",
                path,
                (
                    f"Explicit Wagtail search description {description!r} is also "
                    f"used at: {', '.join(other_paths)}."
                ),
            )

    inventory.sort(key=lambda item: item["path"])
    findings.sort(key=lambda item: (item["path"], item["code"], item["detail"]))

    counts = defaultdict(int)
    for finding in findings:
        counts[finding["code"]] += 1

    return {
        "pages_audited": len(inventory),
        "findings_count": len(findings),
        "findings_by_code": dict(sorted(counts.items())),
        "pages": inventory,
        "findings": findings,
    }


class Command(BaseCommand):
    help = (
        "Read-only audit of live, publicly viewable Wagtail page metadata "
        "and contextual alt attributes in lesson rich text."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            dest="output_format",
            choices=("text", "json"),
            default="text",
            help="Output as human-readable text or JSON (default: text).",
        )

    def handle(self, *args, **options):
        pages = Page.objects.live().public().specific().order_by("path")
        report = audit_pages(pages)

        if options["output_format"] == "json":
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
            return

        self.stdout.write(f"Public live pages audited: {report['pages_audited']}")
        self.stdout.write(f"Review findings: {report['findings_count']}")
        for code, count in report["findings_by_code"].items():
            self.stdout.write(f"  {code}: {count}")

        if not report["findings"]:
            self.stdout.write("No review findings in the inspected page set.")
            return

        self.stdout.write("")
        for finding in report["findings"]:
            self.stdout.write(
                f"[{finding['severity'].upper()}] {finding['path']} "
                f"{finding['code']}: {finding['detail']}"
            )
