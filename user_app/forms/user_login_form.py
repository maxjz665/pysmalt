"""
Модель данных авторизации пользователя
"""
from hashlib import md5

from django import forms

from user_app.models.tbl_user import TblUser


class UserLoginForm(forms.ModelForm):
    """
    Модель данных авторизации пользователя
    """
    class Meta(object):
        model = TblUser
        fields = ('login', 'password')

        widgets = {
            'login': forms.TextInput(attrs={'class': 'form-control',
                                            'required': 'required',
                                            'autocomplete': 'on',
                                            'placeholder': 'Адрес email'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control',
                                                   'required': 'required',
                                                   'autocomplete': 'on',
                                                   'placeholder': 'Пароль'})
        }

        error_messages = {
            'login': { 'required': "Необходимо заполнить поле"},
            "password": {"required": "Необходимо заполнить поле"}
        }

    def authenticate(self):
        """
        Поиск пользователя с такими логином и паролем
        :return:
        """
        hash_pass = md5(md5(self.cleaned_data['password'].encode('utf-8')).hexdigest().encode('utf-8')).hexdigest()
        return TblUser.objects.get(login=self.cleaned_data['login'], password=hash_pass)
