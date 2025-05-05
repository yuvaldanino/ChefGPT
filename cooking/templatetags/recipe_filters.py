from django import template
import re

register = template.Library()

@register.filter
def split_last_line(value):
    """Return the last non-empty line from a string."""
    if not value:
        return ''
    lines = [line.strip() for line in value.split('\n') if line.strip()]
    return lines[-1] if lines else ''

@register.filter
def split(value, arg):
    """Split the value on arg and return a list."""
    return value.split(arg) 