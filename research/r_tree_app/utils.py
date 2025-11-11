"""
Общие функции, требуемые для модуля
"""
from text_app.models.tbl_menu_items import TblMenuItems
from text_app.models.tbl_menu_params import TblMenuParams


def get_pos():
    """
    Получение перечня частей речи
    """
    menu_items = TblMenuItems.objects.all()
    menu_params = TblMenuParams.objects.all()
    param_row = menu_params.get(id=0)
    values = []
    for i in range(1, param_row.items_count + 1):
        item_value = getattr(param_row, 'item_' + str(i))
        value_row = menu_items.get(id=item_value)
        values.append(value_row.item_caption)
    return values

def generate_subslice(record: list, len_pos: int, sector_size: float) -> list:
    """
    Генерация записей с поворотами, т.е. (sector_size*x + (100-sector_size)*y)/100 и (sector_size*x - (100-sector_size)*y)/100
    """
    pos_ret = []
    neg_ret = []
    for i in range(len_pos):
        for j in range(len_pos):
            if i == j:
                continue
            pos_ret.append((sector_size * record[i] + (100 - sector_size) * record[j]) / 100)
            neg_ret.append((sector_size * record[i] - (100 - sector_size) * record[j]) / 100)
    return [*pos_ret, *neg_ret]
