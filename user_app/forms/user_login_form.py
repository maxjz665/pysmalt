"""
Модель данных авторизации пользователя
"""
from hashlib import md5

from django import forms
from django.core.exceptions import ValidationError

from user_app.models.tbl_user import TblUser


class UserLoginForm(forms.Form):
    """
    Модель данных авторизации пользователя
    """
    login = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control',
                                                          'autocomplete': 'on',
                                                          'unique': 'false',
                                                          'placeholder': 'Адрес email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control',
                                                                 'autocomplete': 'on',
                                                                 'placeholder': 'Пароль'}))

    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)
        self.fields['login'].required = False
        self.fields['password'].required = False

    def authenticate(self):
        """
        Поиск пользователя с такими логином и паролем
        :return:
        """
        hash_pass = md5(md5(self.cleaned_data['password'].encode('utf-8')).hexdigest().encode('utf-8')).hexdigest()
        return TblUser.objects.get(login=self.cleaned_data['login'], password=hash_pass)
