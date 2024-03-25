"""
Форма добавления нового пользователя
"""
from django import forms

from user_app.models.tbl_user import TblUser


class UserCreationForm(forms.ModelForm):
    """
    Форма добавления нового пользователя
    """

    class Meta:
        model = TblUser
        fields = ('name', 'login', 'password', 'level', 'researcher')
