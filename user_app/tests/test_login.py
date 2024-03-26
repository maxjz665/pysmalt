"""
Тесты авторизации пользователя
"""
from hashlib import md5

from django.test import TestCase

from user_app.models import TblUser


class LoginTest(TestCase):
    """
    Тесты авторизации пользователя
    """

    def setUp(self) -> None:
        super().setUp()
        password = md5(md5(b"password").hexdigest().encode()).hexdigest()
        TblUser.objects.create(id=1, login='test', password=password)

    def tearDown(self) -> None:
        TblUser.objects.all().delete()
        super().tearDown()

    def test_login_form(self):
        """
        Проверка формы авторизации
        """
        resp = self.client.get('/user_app/login')
        if resp.status_code != 200:
            print(resp)
        self.assertEqual(resp.status_code, 200)

    def test_no_action(self):
        """
        Проверка запроса без указания акшена
        """
        response = self.client.post('/user_app/login', data={'login': 'test', 'password': 'password'})
        self.assertEqual(response.status_code, 404)

    def test_correct_login(self):
        """
        Проверка успешного логина
        """
        response = self.client.post('/user_app/login', data={'login': 'test', 'password': 'password', 'action': 'login'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/')

    def test_incorrect_login(self):
        """
        Проверка авторизации с неверными данными
        """
        response = self.client.post('/user_app/login', data={'login': 'test234', 'password': 'pas234sword',
                                                             'action': 'login'})
        self.assertEqual(response.status_code, 404)
