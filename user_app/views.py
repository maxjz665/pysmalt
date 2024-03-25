from django.http import HttpRequest
from django.shortcuts import render


def login(request: HttpRequest):
    """
    Обработка запросов на авторизацию пользователя
    :param request: запрос на авторизацию
    :return: форма или редирект с куками
    """
    if request.method == 'POST':
        # обработка данных формы
        pass
    else:
        return render(request, "user_app/login.html", context={})
