from django.shortcuts import render

def hetco_app_view(request):
    """Отображение модуля Хетсо"""
    return render(request, "hetco_app/hetco_app_form.html")