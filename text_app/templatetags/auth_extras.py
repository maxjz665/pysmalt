from django.contrib.auth.models import User, Group

from django import template

register = template.Library()

@register.filter(name='has_level')
def has_level(user, level):
    levels = {
        "LEVEL_USER": 0,
        "LEVEL_EDITOR": 1,
        "LEVEL_MANAGER": 2,
        "LEVEL_ADMIN": 3,
    }
    return user.has_level(levels[level])