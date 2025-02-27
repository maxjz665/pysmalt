"""
Фильтр для получения элемента списка по ключу из переменной
"""

from django import template

register = template.Library()


@register.filter(name='list_item', is_safe=True)
def list_item(dictionary: list, key):
    if len(dictionary) == 0:
        return None
    if key in dictionary or str(key) in dictionary:
        return key
    return None
