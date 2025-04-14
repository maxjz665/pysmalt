"""
Модель пользователя системы
"""
from django.contrib.auth.models import AbstractBaseUser
from django.db import models


class TblUser(AbstractBaseUser):
    """
    Модель пользователя системы
    """

    LEVEL_USER = 0
    LEVEL_EDITOR = 1
    LEVEL_MANAGER = 2
    LEVEL_ADMIN = 3

    class Meta:
        db_table = 'sys_users'

    # отключаем встроенные поля в AbstractBaseUser для пользователя
    user_permissions = None
    last_login = None
    is_superuser = None
    groups = None

    # поле требуется для AbstractBaseUser
    USERNAME_FIELD = 'login'

    id = models.AutoField(primary_key=True)
    login = models.CharField(max_length=200, unique=True, blank=False, null=False)
    password = models.CharField(max_length=200, blank=False, null=False)
    name = models.CharField(max_length=200)
    level = models.IntegerField(default=0)
    researcher = models.IntegerField(default=0)

    def has_level(self, level):
        """
        Проверка наличия заданного уровня доступа
        """
        return self.level >= level

    @property
    def is_researcher(self):
        """
        Является ли пользователь исследователем
        """
        return self.researcher > 0 or self.has_level(self.LEVEL_ADMIN)

    @property
    def has_manager(self):
        """
        Является ли пользователь менеджером
        """
        return self.has_level(self.LEVEL_MANAGER)

    @property
    def has_admin(self):
        """
        Является ли пользователь администратором
        """
        return self.has_level(self.LEVEL_ADMIN)
