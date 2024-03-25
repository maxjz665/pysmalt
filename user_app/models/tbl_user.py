"""
Модель пользователя системы
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class TblUser(AbstractUser):
    class Meta:
        db_table = 'sys_users'

    id_user = models.AutoField(primary_key=True)
    login = models.CharField(max_length=200)
    password = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    level = models.IntegerField(default=0)
    researcher = models.IntegerField(default=0)
