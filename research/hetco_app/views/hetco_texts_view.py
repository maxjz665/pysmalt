from django.http import JsonResponse
from text_app.models.tbl_textlist import TblTextListDescription

def get_texts_for_list(request):
    list_id = request.GET.get('list_id')
    text_list = TblTextListDescription.get_item(request.user, int(list_id))
    texts = [{'id': item.text.id, 'title': item.text.title} for item in text_list.items]
    return JsonResponse({'texts': texts})