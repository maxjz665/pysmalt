from django import template

register = template.Library()


@register.filter(name='search_color', is_safe=True, needs_autoescape=False)
def search_color(value, arg):
    """
    Подбор цвета из таблицы цветов по номеру позиции
    """
    for item in value:
        if item.get("start") <= arg < item.get("end"):
            if item.get("pros") < 0.33:
                return "background-color:LightGreen"
            elif item.get("pros") < 0.66:
                return ""
            return "background-color:Khaki"

    return ""
