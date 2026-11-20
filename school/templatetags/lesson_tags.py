from uuid import uuid4

from django import template

register = template.Library()


@register.simple_tag
def unique_dom_id():
    """Return a per-render UUID for unique, accessible component IDs."""
    return uuid4().hex
