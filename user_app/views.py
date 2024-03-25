import time

from django.contrib.auth import login, logout
from django.db import OperationalError
from django.http import HttpRequest
from django.shortcuts import render, redirect

from user_app.forms.user_creation_form import UserCreationForm
from user_app.forms.user_login_form import UserLoginForm
from user_app.models import TblUser


def log_in(request: HttpRequest):
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
            if request.POST['login'] == '':
                form_login_user.add_error('login', 'Пожалуйста, введите логин')

            if request.POST['password'] == '':
                form_login_user.add_error('password', 'Пожалуйста, введите пароль')

            if form_login_user.is_valid():
                try:
                    user = form_login_user.authenticate()
                    login(request, user)
                except (OperationalError, TblUser.DoesNotExist):
                    time.sleep(5)
                    return render(request, 'user_app/login.html', context={
                        'error_message': "Неверный логин и/или пароль",
                        'form_login_user': form_login_user,
                        'form_create_user': form_create_user,
                        'form_login_errors': True
                    })
            else:
                return render(request, 'user_app/login.html', context={
                    'form_login_user': form_login_user,
                    'form_create_user': form_create_user,
                    'form_login_errors': True
                })
            return redirect('home')
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


def profile(request: HttpRequest):
    return None


def log_out(request: HttpRequest):
    logout(request)
    return redirect('home')
