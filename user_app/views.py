import time

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User, Group
from django.db import OperationalError
from django.http import HttpRequest
from django.shortcuts import render, redirect
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from user_app.forms.user_creation_form import UserCreationForm
from user_app.forms.user_login_form import UserLoginForm
from user_app.models import TblUser


def log_in(request: HttpRequest):
    """
    Обработка запросов на авторизацию пользователя
    :param request: запрос на авторизацию
    :return: форма или редирект с куками
    """
    next_url = request.GET.get("next", "")
    form_login_user = UserLoginForm(request.POST)
    form_create_user = UserCreationForm(request.POST)
    if(len(Group.objects.all()) != 0):
        if(len(Group.objects.filter(name="USERS")) == 0):
            Group.objects.create(name='USERS')
        if (not Group.objects.filter(name="EDITORS")):
            Group.objects.create(name='EDITORS')
        if (not Group.objects.filter(name="MANAGERS")):
            Group.objects.create(name='MANAGERS')
        if (not Group.objects.filter(name="ADMINS")):
            Group.objects.create(name='ADMINS')
        if (not Group.objects.filter(name="RESEARCHERS")):
            Group.objects.create(name='RESEARCHERS')
    else:
        Group.objects.create(name='USERS')
        Group.objects.create(name='EDITORS')
        Group.objects.create(name='MANAGERS')
        Group.objects.create(name='ADMINS')
        Group.objects.create(name='RESEARCHERS')

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
                    time.sleep(settings.LOGIN_DELAY_SECONDS)
                    return render(request, 'user_app/login.html', context={
                        'error_message': "Неверный логин и/или пароль",
                        'form_login_user': form_login_user,
                        'form_create_user': form_create_user,
                        'form_login_errors': True,
                        next: next_url
                    }, status=404)
            else:
                return render(request, 'user_app/login.html', context={
                    'form_login_user': form_login_user,
                    'form_create_user': form_create_user,
                    'form_login_errors': True,
                    next: next_url
                })
            if next_url and next_url != "/":
                return redirect(next_url)
            return redirect('home')
        if request.POST.get('action') == 'register':
            if form_create_user.is_valid():
                # сохранение пользователя
                user = form_create_user.save()
            return redirect('home')
        return render(request, "user_app/login.html", context={"error_message": "Неизвестное действие",
                                                               'form_login_user': form_login_user,
                                                               'form_create_user': form_create_user}, status=404)
    else: # GET
        return render(request, "user_app/login.html", context={'form_login_user': form_login_user,
                                                               'form_create_user': form_create_user, 'next': next_url})


def profile(request: HttpRequest):
    return None


def log_out(request: HttpRequest):
    logout(request)
    next_url = request.GET.get('next', "")
    if next_url and next_url != "/":
        return redirect(next_url)
    return redirect('home')
