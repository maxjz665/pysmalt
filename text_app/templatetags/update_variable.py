from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def update_variable(value):
    """Allows to update existing variable in template"""
    return value
