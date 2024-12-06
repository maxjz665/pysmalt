"""
URL configuration for shower project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', include('text_app.urls')),  # работа с текстом (просмотр и редактирование)
    path('', include('user_app.urls')),  # профили пользователя + авторизация
    path('research/r_tree/', include('r_tree_app.urls')),  # работа с деревьями решений
    path('research/r_bigrams/', include('r_bigrams_app.urls'))  # работа с деревьями решений
]
