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
    path('research/r_tree/', include('research.r_tree_app.urls')),  # работа с деревьями решений
    path('research/r_bigrams/', include('research.r_ngrams_app.urls')),  # работа с деревьями решений
    path('research/text_generator/', include('research.text_generator.urls')), # работа с генерацией текстов
    path('research/hetco_app/', include('research.hetco_app.urls')),  # работа с модулем Хетсо
    path('research/authorship/', include('research.authorship.urls')),  # определение авторства текста
]

# включение адресов для консоли джанго если оно установлено в системе
try:
    from debug_toolbar.toolbar import debug_toolbar_urls
    urlpatterns += debug_toolbar_urls()
except ImportError:
    pass
