"""
Формирование библиографического описания
:return: строка с библиографическим описанием
"""
from django.urls import reverse
from django.utils.safestring import mark_safe

from text_app.models.tbl_text import TblText
from django import template

register = template.Library()


@register.simple_tag(name='bib_item')
def bib_item(value: TblText, url: str = None, *args, **kwargs):
    """
    Формирование библиографического описания
    :return: строка с библиографическим описанием
    """
    text_data = value

    if text_data.idkey is None:
        ret = "[] "
    else:
        ret = f"[{text_data.idkey}] "
    if text_data.author is not None:
        ret += text_data.author.name
        if text_data.author.name[-1] == '.':
            ret += " "
        else:
            ret += ". "

    # печать названия.
    if url is not None and len(url) > 0:
        ret += f' <a href="{reverse(url, args=args)}">{text_data.title}</a>'
    else:
        ret += text_data.title

    # печать перечня авторов. TODO: перевернуть ФИО на ИОФ
    has_author = False
    if text_data.author is not None:
        ret += " / " + text_data.author.name
        has_author = True
    if text_data.author2 is not None:
        if not has_author:
            ret += " / "
            has_author = True
        else:
            ret += ", "
        ret += text_data.author2.name
    if text_data.author3 is not None:
        if not has_author:
            ret += " / "
        else:
            ret += ", "
            ret += text_data.author3.name

    # печать журнала если он есть
    ret += " // "
    if text_data.magazine is not None:
        ret += text_data.magazine.title + "."

    # дата публикации
    if text_data.publication_date is not None:
        ret += f" - {text_data.publication_date.year}."

    # раздел журнала если есть
    if text_data.magazine_section is not None:
        ret += f" - Разд. {text_data.magazine_section}."

    # том журнала если есть
    if text_data.magazine_volume is not None:
        ret += f" - Т. {text_data.magazine_volume}."

    # номер журнала если есть
    if text_data.magazine_no is not None:
        ret += f" - № {text_data.magazine_no}."

    # номера страниц если есть
    if text_data.pages is not None:
        ret += f" - с. {text_data.pages}."

    return mark_safe(ret)
