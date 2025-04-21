from django.shortcuts import render

def help_view(request):
    """Отображение справки по генератору текстов"""
    return render(request, "text_generator/help.html")