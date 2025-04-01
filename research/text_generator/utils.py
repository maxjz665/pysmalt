import logging
import random
import re
from typing import Optional, List

from research.text_generator.dataclasses import *
from text_app.models.tbl_text import TblText

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

random.seed(42)


def get_shifts_for_word(words: List[TextWord], pos: int) -> WordShifts:
    """Возвращает возможные сдвиги влево и вправо для позиции."""
    # Проверяем границы
    if pos >= len(words) or pos < 0:
        return WordShifts(L=0, R=0)

    pos_sentence = words[pos].sentence_index
    pos_paragraph = words[pos].paragraph_index
    pos_chapter = words[pos].chapter_index
    
    # Ищем левую границу
    count = pos
    while (count >= 0 and 
           words[count].sentence_index == pos_sentence and
           words[count].paragraph_index == pos_paragraph and 
           words[count].chapter_index == pos_chapter):
        count -= 1
    left = count - pos + 1
    
    # Ищем правую границу
    count = pos  
    while (count < len(words) and
           words[count].sentence_index == pos_sentence and
           words[count].paragraph_index == pos_paragraph and
           words[count].chapter_index == pos_chapter):
        count += 1
    right = count - pos - 1
    
    return WordShifts(L=left, R=right)


def get_new_fragment_positions(
    text: TextContent, 
    start_pos: int, 
    end_pos: int, 
    s_lr: WordShifts, 
    e_lr: WordShifts, 
    last_end_pos: int = -1
) -> FragmentPosition:
    """Корректирует позиции чтобы они попадали на границы предложений."""
    BORDER_SHIFT_MAX = 10  
    MIN_FRAGMENT_SIZE = 5
    text_size = text.length

    # Выбираем минимальный и максимальный сдвиги для начальной позиции
    if abs(s_lr.L) == abs(s_lr.R):
        min_sh_s = {'side': 'R', 'val': s_lr.R}  # Всегда R для начала
        max_sh_s = {'side': 'L', 'val': s_lr.L}  # Всегда L для конца
    else:
        if abs(s_lr.L) < abs(s_lr.R):
            min_sh_s = {'side': 'L', 'val': s_lr.L}
            max_sh_s = {'side': 'R', 'val': s_lr.R}
        else:  
            min_sh_s = {'side': 'R', 'val': s_lr.R}
            max_sh_s = {'side': 'L', 'val': s_lr.L}

    # Выбираем минимальный и максимальный сдвиги для конечной позиции
    if abs(e_lr.L) == abs(e_lr.R):
        min_sh_e = {'side': 'L', 'val': e_lr.L}  # Всегда L для конца
        max_sh_e = {'side': 'R', 'val': e_lr.R}  # Всегда R для начала
    else:
        if abs(e_lr.L) < abs(e_lr.R):
            min_sh_e = {'side': 'L', 'val': e_lr.L}
            max_sh_e = {'side': 'R', 'val': e_lr.R}
        else:
            min_sh_e = {'side': 'R', 'val': e_lr.R}
            max_sh_e = {'side': 'L', 'val': e_lr.L}

    # Формируем массивы допустимых сдвигов  
    s_items = []
    e_items = []
    
    if abs(min_sh_s['val']) <= BORDER_SHIFT_MAX:
        s_items.append(min_sh_s)
    if abs(max_sh_s['val']) <= BORDER_SHIFT_MAX:
        s_items.append(max_sh_s)
    if abs(min_sh_e['val']) <= BORDER_SHIFT_MAX:
        e_items.append(min_sh_e)
    if abs(max_sh_e['val']) <= BORDER_SHIFT_MAX:
        e_items.append(max_sh_e)

    # Массивы для хранения результатов
    results = []
    ext_results = []

    # Если есть допустимые сдвиги для обеих позиций
    if s_items and e_items:
        for s_item in s_items:
            for e_item in e_items:
                end_pos_res = end_pos
                start_pos_res = start_pos
                start_pos_res += s_item['val'] 
                end_pos_res += e_item['val']

                if s_item['side'] == 'R':
                    start_pos_res += 1
                if e_item['side'] == 'L':
                    end_pos_res -= 1

                if (end_pos_res - start_pos_res >= MIN_FRAGMENT_SIZE and
                    start_pos_res > last_end_pos and 
                    end_pos_res < text_size):
                    results.append((start_pos_res, end_pos_res + 1))
                else:
                    # Пробуем альтернативные варианты
                    if abs(s_item['val']) > abs(e_item['val']):
                        end_pos_res = end_pos
                        start_pos_res = start_pos
                        start_pos_res += e_item['val']
                        end_pos_res += e_item['val']
                        if e_item['side'] == 'L':
                            end_pos_res -= 1
                            start_pos_res -= 1
                        if (start_pos_res > last_end_pos and 
                            end_pos_res < text_size):
                            ext_results.append((start_pos_res, end_pos_res + 1))
                    else:
                        end_pos_res = end_pos
                        start_pos_res = start_pos
                        start_pos_res += s_item['val']
                        end_pos_res += s_item['val']
                        if s_item['side'] == 'R':
                            end_pos_res += 1
                            start_pos_res += 1
                        if (start_pos_res > last_end_pos and
                            end_pos_res < text_size):
                            ext_results.append((start_pos_res, end_pos_res + 1))
    
    # Если есть только допустимые сдвиги для начальной позиции
    elif s_items:
        for s_item in s_items:
            end_pos_res = end_pos
            start_pos_res = start_pos
            start_pos_res += s_item['val']
            end_pos_res += s_item['val']
            if s_item['side'] == 'R':
                start_pos_res += 1
                end_pos_res += 1
            if (end_pos_res - start_pos_res >= MIN_FRAGMENT_SIZE and
                start_pos_res > last_end_pos and
                end_pos_res < text_size):
                results.append((start_pos_res, end_pos_res + 1))

    # Если есть только допустимые сдвиги для конечной позиции
    elif e_items:
        for e_item in e_items:
            end_pos_res = end_pos
            start_pos_res = start_pos
            start_pos_res += e_item['val']
            end_pos_res += e_item['val']
            if e_item['side'] == 'L':
                end_pos_res -= 1
                start_pos_res -= 1
            if (end_pos_res - start_pos_res >= MIN_FRAGMENT_SIZE and
                start_pos_res > last_end_pos and
                end_pos_res < text_size):
                results.append((start_pos_res, end_pos_res + 1))

    # Выбираем лучший результат
    best_result = (start_pos, end_pos + 1)
    
    if results:
        min_size = float('inf')
        for result in results:
            size = result[1] - result[0]
            if 0 < size < min_size:
                min_size = size
                best_result = result
    elif ext_results:
        min_size = float('inf')
        for result in ext_results:
            size = result[1] - result[0]
            if 0 < size < min_size:
                min_size = size 
                best_result = result

    return FragmentPosition(start=best_result[0], end=best_result[1])


def generate_text_code(
    base_text: TextContent,
    other_text: TextContent,
    fragment_size: int,
    percent_of_inserts: float,
    bind_borders: bool = False
) -> CodeGen:
    """
    Генерирует код для вставки текста.
    
    Args:
        base_text: Базовый текст
        other_text: Вставляемый текст
        fragment_size: Размер фрагмента для вставки
        percent_of_inserts: Доля вставок (0.0-1.0)
        bind_borders: Привязывать ли границы к предложениям
        
    Returns:
        str: Сгенерированный код вставок
    """

    # Проверяем параметры
    valid, error_msg = check_params(
        base_text.length,
        other_text.length,
        percent_of_inserts,
        fragment_size
    )
    if not valid:
        logger.error(f"Ошибка параметров check_params:{error_msg}")
        raise ValueError(error_msg)

    # Используем атрибуты из TextContent
    base_id = base_text.id 
    other_id = other_text.id
    base_length = base_text.length
    other_length = other_text.length
    
    logger.debug(
        f"Входные параметры: base_id={base_id}, other_id={other_id}, base_length={base_length}, other_length={other_length}")
    logger.debug(f"Тип базового текста: {type(base_text)}")
    logger.debug(f"Тип вставляемого текста: {type(other_text)}")

    logger.debug("Базовый текст в сыром виде")
    base_text_content = base_text

    logger.debug("Вставляемый текст в сыром виде")
    other_text_content = other_text

    logger.debug(f"Тип содержимого базового текста: {type(base_text_content)}")
    logger.debug(f"Тип содержимого вставляемого текста: {type(other_text_content)}")

    # Вычисляем количество вставок для базового текста
    ins_count_base = max(1, round(base_length * percent_of_inserts / fragment_size))
    logger.debug(f"Начальное количество вставок для базового текста: {ins_count_base}")

    # Корректируем количество вставок, если их слишком много
    while ins_count_base * fragment_size > base_length:
        ins_count_base -= 1
    logger.debug(f"Скорректированное количество вставок для базового текста: {ins_count_base}")

    # Вычисляем максимальный шаг для базового текста
    max_base_step_size = (
        (base_length - (ins_count_base * fragment_size)) // ins_count_base
        if ins_count_base else 0
    )
    logger.debug(f"Максимальный шаг для базового текста: {max_base_step_size}")

    # Проверяем особый случай с малым шагом
    lim_shift_base = False
    shifts_base = []
    if max_base_step_size < 1:
        lim_shift_base = True
        max_count_base_sh = base_length - (ins_count_base * fragment_size)
        shifts_base = get_array_of_shifts(ins_count_base, max_count_base_sh)

    # Вычисляем количество вставок для второго текста
    ins_count_other = min(ins_count_base, other_length // fragment_size)
    logger.debug(f"Количество вставок для второго текста: {ins_count_other}")

    # Вычисляем максимальный шаг для второго текста
    max_other_step_size = (
        (other_length - (ins_count_other * fragment_size)) // ins_count_other
        if ins_count_other else 0
    )
    logger.debug(f"Максимальный шаг для второго текста: {max_other_step_size}")

    start_base_pos = 0
    start_other_pos = 0
    code = CodeGen()
    count_b = 0
    count_o = 0

    while count_b < ins_count_base:
        logger.debug(f"Итерация цикла: {count_b}")
        logger.debug(f"Начальная позиция в базовом тексте: {start_base_pos}, длина базового текста: {base_length}")

        # Вычисляем позиции для базового текста
        if base_length > fragment_size:
            if lim_shift_base:
                # Если шаг мал, используем массив сдвигов
                start_base_pos = start_base_pos + 1 if shifts_base[count_b] else start_base_pos
            else:
                # Иначе используем rintExt для более равномерного распределения
                start_base_pos = rint_ext(start_base_pos, start_base_pos + max_base_step_size, percent_of_inserts)
            logger.debug(f"Новая начальная позиция в базовом тексте: {start_base_pos}")

            if start_base_pos >= base_length:
                logger.debug("Прерываем цикл - начальная позиция превышает длину базового текста")
                break

            end_base_pos = min(start_base_pos + fragment_size, base_length)
            logger.debug(f"Конечная позиция в базовом тексте: {end_base_pos}")
        else:
            end_base_pos = base_length
            logger.debug("Используем полную длину базового текста")

        # Вычисляем позиции для второго текста
        if count_o >= ins_count_other:
            count_o = 0
            start_other_pos = 0

        if other_length > fragment_size:
            if max_other_step_size > 0:
                start_other_pos = random.randint(start_other_pos, start_other_pos + max_other_step_size)
            if start_other_pos >= other_length:
                start_other_pos = random.randint(0, max(0, other_length - fragment_size))
            end_other_pos = min(start_other_pos + fragment_size, other_length)
        else:
            end_other_pos = other_length

        logger.debug(
            f"До корректировки границ: начальная позиция базового текста={start_base_pos}, конечная позиция базового текста={end_base_pos}, начальная позиция второго текста={start_other_pos}, конечная позиция второго текста={end_other_pos}")


        ### ОПЦИЯ ПРИВЯЗКИ К ГРАНИЦАМ ПРЕДЛОЖЕНИЯМ.
        # Корректируем позиции по границам предложений, если это указано
        if bind_borders and base_text_content and other_text_content:
            # Получаем сдвиги для позиций для первого текста
            s_lr1 = get_shifts_for_word(base_text_content.words, start_base_pos)
            e_lr1 = get_shifts_for_word(base_text_content.words, end_base_pos)
            result = get_new_fragment_positions(base_text_content, start_base_pos, end_base_pos - 1, s_lr1, e_lr1)

            start_base_pos, end_base_pos = result.start, result.end

            # Получаем сдвиги для позиций для второго текста
            s_lr2 = get_shifts_for_word(other_text_content.words, start_other_pos)
            e_lr2 = get_shifts_for_word(other_text_content.words, end_other_pos)
            result2 = get_new_fragment_positions(other_text_content, start_other_pos, end_other_pos - 1, s_lr2, e_lr2)
            start_other_pos, end_other_pos = result2.start, result2.end

            end_base_pos += 1
            end_other_pos += 1

        # Формируем фрагмент кода
        fragment = f"A{base_id}S{start_base_pos}E{end_base_pos - 1}B{other_id}S{start_other_pos}E{end_other_pos - 1}"
        logger.debug(f"Добавляем фрагмент: {fragment}")
        code += fragment

        count_b += 1
        count_o += 1
        start_base_pos = end_base_pos
        start_other_pos = end_other_pos

    logger.debug(f"Итоговый код: {code}")
    return code


def get_array_of_shifts(ins_count: int, shifts_count: int) -> list[bool]:
    """
    Создает массив логических сдвигов для случая с малым шагом между вставками.
    
    Функция генерирует массив булевых значений, где True означает необходимость сдвига на 1 позицию,
    а False - отсутствие сдвига. Количество True значений равно shifts_count.
    
    Args:
        ins_count: Общее количество вставок
        shifts_count: Желаемое количество сдвигов (должно быть меньше или равно ins_count)
        
    Returns:
        list[bool]: Массив булевых значений длины ins_count, где True означает необходимость сдвига.
                   Возвращает пустой список, если параметры некорректны.
    """
    if shifts_count > ins_count or ins_count < 1 or shifts_count < 0:
        return []
        
    result = [True] * ins_count
    k = ins_count - shifts_count
    
    while k > 0:
        rnd = random.randint(0, ins_count - 1)
        if result[rnd]:
            result[rnd] = False
            k -= 1
            
    return result


def parse_code(code: CodeGen) -> Optional[ParsedCode]:
    """Парсит код и возвращает словарь с ID текстов и интервалами."""
    if not re.match(r"^(A\d+S\d+E\d+B\d+S\d+E\d+)+$", code):
        return None

    fragments = re.findall(r"([AB])(\d+)S(\d+)E(\d+)", code)
    if not fragments:
        return None

    # Проверяем что все A и B чередуются
    for i in range(0, len(fragments), 2):
        if i + 1 >= len(fragments) or fragments[i][0] != 'A' or fragments[i+1][0] != 'B':
            return None

    # Проверяем совпадение ID
    base_id = fragments[0][1]
    other_id = fragments[1][1]

    for i in range(0, len(fragments), 2):
        # Проверяем base id
        if fragments[i][1] != base_id:
            return None
        # Проверяем other id
        if fragments[i+1][1] != other_id:
            return None

        # Проверяем длины фрагментов и что конец > начала
        start_base = int(fragments[i][2])
        end_base = int(fragments[i][3])
        start_other = int(fragments[i+1][2])
        end_other = int(fragments[i+1][3])

        # Проверяем что конец > начала
        if end_base < start_base or end_other < start_other:
            return None

        # При привязке к границам длины могут отличаться
        base_len = end_base - start_base + 1
        other_len = end_other - start_other + 1
        if base_len <= 0 or other_len <= 0:
            return None

    result: ParsedCode = {
        "id1": int(base_id),
        "id2": int(other_id),
        "intervals": {"A": [], "B": []}
    }

    for i in range(0, len(fragments), 2):
        result["intervals"]["A"].append(CodeInterval(
            S=int(fragments[i][2]),
            E=int(fragments[i][3])
        ))
        result["intervals"]["B"].append(CodeInterval(
            S=int(fragments[i+1][2]),
            E=int(fragments[i+1][3])
        ))

    return result


def generate_text_by_code(code: CodeGen, base_words: List[TextWord], other_words: List[TextWord]):
    """
    Генерирует текст, используя код и последовательности слов
    """
    parsed = parse_code(code)
    if not parsed:
        return None
        
    result = []
    base_pos = 0
    prev_paragraph = base_words[0].paragraph_index if base_words else 0
    prev_sentence = base_words[0].sentence_index if base_words else 0
    
    # Для вставляемого текста тоже отслеживаем предыдущие индексы
    other_prev_paragraph = other_words[0].paragraph_index if other_words else 0
    other_prev_sentence = other_words[0].sentence_index if other_words else 0
    
    # Обрабатываем каждый интервал
    for i in range(len(parsed["intervals"]["A"])):
        # Добавляем фрагмент базового текста
        start = parsed["intervals"]["A"][i]["S"]
        # Текущая реализация
        for word in base_words[base_pos:start]:
            # Существующая логика для базового текста
            start_paragraph = word.paragraph_index > prev_paragraph
            start_sentence = word.sentence_index > prev_sentence
            
            if start_paragraph:
                prev_paragraph = word.paragraph_index
                result.append({'word': '|', 'start_paragraph': True, 'highlight': False})
            elif start_sentence:
                prev_sentence = word.sentence_index  
                result.append({'word': '|', 'start_paragraph': False, 'highlight': False})
                
            result.append({'word': word.word, 'start_paragraph': False, 'highlight': False})

            
        # Добавляем фрагмент вставляемого текста  
        other_start = parsed["intervals"]["B"][i]["S"]
        other_end = parsed["intervals"]["B"][i]["E"] + 1
        
        for word in other_words[other_start:other_end]:
            # Добавляем проверку разделителей для вставляемого текста
            start_paragraph = word.paragraph_index > other_prev_paragraph  
            start_sentence = word.sentence_index > other_prev_sentence

            if start_paragraph:
                other_prev_paragraph = word.paragraph_index
                result.append({'word': '|', 'start_paragraph': True, 'highlight': True})
            elif start_sentence:
                other_prev_sentence = word.sentence_index
                result.append({'word': '|', 'start_paragraph': False, 'highlight': True})
                
            result.append({'word': word.word, 'start_paragraph': False, 'highlight': True})
            
            
        base_pos = parsed["intervals"]["A"][i]["E"] + 1

    # Добавляем оставшуюся часть базового текста
    for word in base_words[base_pos:]:
        start_paragraph = word.paragraph_index > prev_paragraph
        start_sentence = word.sentence_index > prev_sentence
        
        if start_paragraph:
            prev_paragraph = word.paragraph_index
            result.append({
                'word': '|',
                'start_paragraph': True,
                'highlight': False
            })
        elif start_sentence:
            prev_sentence = word.sentence_index
            result.append({
                'word': '|',
                'start_paragraph': False, 
                'highlight': False
            })
            
        result.append({
            'word': word.word,
            'start_paragraph': False,
            'highlight': False
        })

    return result


def rint_ext(start: int, end: int, percent_of_inserts: float) -> int:
    """Генерирует случайное целое число с вероятностным смещением."""
    res = random.randint(start, end)
    i = 0.0
    while i <= percent_of_inserts:
        res = random.randint(start, res)
        i += random.uniform(0, 0.1)
    return end - res + start


def get_random_texts(
    base_list_id: int, 
    other_list_id: int, 
    base_list_items: List[TblText], 
    other_list_items: List[TblText]
) -> tuple[TblText, TblText]:
    """Возвращает случайную пару текстов из указанных списков."""
    # Выбираем случайный текст из базового списка
    base_text_item = random.choice(base_list_items)
    
    if base_list_id == other_list_id:
        # Если списки одинаковые, исключаем выбранный текст
        available_texts = [t for t in other_list_items if t != base_text_item]
        other_text_item = random.choice(available_texts)
    else:
        other_text_item = random.choice(other_list_items)
        
    return base_text_item, other_text_item


def get_length_text(text: TblText) -> Optional[int]:
    """Возвращает длину текста в словах."""
    if not text:
        return None
    
    # Получаем содержимое текста
    words = text.get_content()
    return len(words) if words else None


def check_params(
    base_text_length: int, 
    other_text_length: int, 
    percent_of_inserts: float, 
    fragment_size: int
) -> tuple[bool, str]:
    """Проверяет корректность параметров генерации текста."""
    # Проверяем корректность процента вставок
    if not (0.01 <= percent_of_inserts <= 0.95):
        return False, "Укажите долю вставок в диапазоне 0.01 - 0.95"

    # Проверяем минимальный размер фрагмента
    if fragment_size < 5:
        return False, "Минимальный размер заменяемого фрагмента 5"

    # Проверяем что фрагмент не больше текста для вставки
    if fragment_size > other_text_length:
        return False, f"Размер фрагмента не должен превышать размер вставляемого текста ({other_text_length})"

    # Проверяем что фрагмент не больше 95% базового текста
    max_size = round(base_text_length * 0.95)
    if fragment_size > max_size:
        return False, f"Максимальная доля вставок 0.95, размер фрагмента не должен превышать {max_size}"

    # Проверяем соотношение размера фрагмента и процента вставок только для малых фрагментов 
    if fragment_size < base_text_length * 0.5:  # Для больших фрагментов не проверяем
        if base_text_length * percent_of_inserts < fragment_size:
            perc = round(fragment_size / base_text_length, 2)
            return False, f"Указанная доля вставок меньше фактической. Укажите >= {perc + 0.01}"

    return True, ""
