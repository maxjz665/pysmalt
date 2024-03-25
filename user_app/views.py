from django.db import OperationalError
from django.http import HttpRequest
from django.shortcuts import render, redirect

from user_app.forms.user_creation_form import UserCreationForm
from user_app.forms.user_login_form import UserLoginForm


def login(request: HttpRequest):
    """
    Обработка запросов на авторизацию пользователя
    :param request: запрос на авторизацию
    :return: форма или редирект с куками
    """
    form_login_user = UserLoginForm(request.POST)
    form_create_user = UserCreationForm(request.POST)

    if request.method == 'POST':
        # обработка данных формы
        if request.POST.get('action') == 'login':
            if form_login_user.is_valid():
                try:
                    user = form_login_user.authenticate()
                except OperationalError as exception:
                    return render(request, 'user_app/login.html', context={
                        'error_message': str(exception),
                        'form_login_user': form_login_user,
                        'form_create_user': form_create_user
                    })
                return redirect('home')
            return render(request, "user_app/login.html", context={'form_login_user': form_login_user,
                                                                   'form_create_user': form_create_user,
                                                                   'form_login_errors': True})
        if request.POST.get('action') == 'register':
            if form_create_user.is_valid():
                # сохранение пользователя
                user = form_create_user.save()
        return render(request, "user_app/login.html", context={"error_message": "Неизвестное действие",
                                                               'form_login_user': form_login_user,
                                                               'form_create_user': form_create_user})
    else:
        return render(request, "user_app/login.html", context={'form_login_user': form_login_user,
                                                               'form_create_user': form_create_user})
