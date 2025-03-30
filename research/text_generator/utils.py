import logging
import random
import re
from typing import Optional, List

from research.text_generator.dataclasses import *
from text_app.models.tbl_text import TblText

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

random.seed(42)

def adjust_to_sentence_borders(text: TextContent, start: int, end: int) -> tuple[int, int]:
    """
    Корректирует позиции start и end, чтобы они попадали на границы предложений.
    
    Args:
        text: Объект TextContent с текстом и его разметкой
        start: Начальная позиция
        end: Конечная позиция
        
    Returns:
        tuple[int, int]: Кортеж с новыми позициями (new_start, new_end)
    """
    # Получаем список слов и их индексы предложений
    words = text.words
    sentence_indices = [word.sentence_index for word in words]
    
    # Находим индекс предложения для начальной и конечной позиции
    start_sentence = sentence_indices[start] if start < len(sentence_indices) else sentence_indices[-1]
    end_sentence = sentence_indices[end] if end < len(sentence_indices) else sentence_indices[-1]
    
    # Корректируем начальную позицию
    new_start = start
    for i in range(start, -1, -1):
        if i == 0 or sentence_indices[i] != start_sentence:
            new_start = i if i == 0 else i + 1
            break
            
    # Корректируем конечную позицию
    new_end = end
    for i in range(end, len(words)):
        if i == len(words) - 1 or sentence_indices[i + 1] != end_sentence:
            new_end = i
            break
            
    return new_start, new_end


def generate_text_code(
    base_text: TextContent,
    other_text: TextContent,
    fragment_size: int,
    percent_of_inserts: float,
    bind_borders: bool = False
) -> str:
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
    watermark = ""
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
            start_base_pos, end_base_pos = adjust_to_sentence_borders(base_text_content, start_base_pos,
                                                                      end_base_pos - 1)
            start_other_pos, end_other_pos = adjust_to_sentence_borders(other_text_content, start_other_pos,
                                                                        end_other_pos - 1)
            end_base_pos += 1
            end_other_pos += 1
            logger.debug(
                f"После корректировки границ: начальная позиция базового текста={start_base_pos}, конечная позиция базового текста={end_base_pos}, начальная позиция второго текста={start_other_pos}, конечная позиция второго текста={end_other_pos}")

        # Формируем фрагмент кода
        fragment = f"A{base_id}S{start_base_pos}E{end_base_pos - 1}B{other_id}S{start_other_pos}E{end_other_pos - 1}"
        logger.debug(f"Добавляем фрагмент: {fragment}")
        watermark += fragment

        count_b += 1
        count_o += 1
        start_base_pos = end_base_pos
        start_other_pos = end_other_pos

    logger.debug(f"Итоговый код: {watermark}")
    return watermark


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


def parse_code(code: str) -> Optional[ParsedCode]:
    """
    Парсит код и возвращает словарь с ID текстов и интервалами.
    """
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


def generate_text_by_code(code, base_words, other_words):
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
    """
    Генерирует случайное целое число из интервала с вероятностным смещением к концу интервала.
    
    Функция использует процент вставок для определения степени смещения: чем больше процент,  
    тем чаще будут генерироваться числа ближе к концу интервала. Это обеспечивает более
    равномерное распределение вставок по тексту.
    
    Args:
        start: Начало интервала (включительно)
        end: Конец интервала (включительно)
        percent_of_inserts: Доля вставок (0.0-1.0), влияет на степень смещения к концу интервала
        
    Returns:
        int: Случайное число из интервала [start, end] с вероятностным смещением
    """
    res = random.randint(start, end)
    i = 0.0
    while i <= percent_of_inserts:
        res = random.randint(start, res)
        i += random.uniform(0, 0.1)
    return end - res + start


def get_random_texts(base_list_id: int, other_list_id: int, base_list_items: List, other_list_items: List):
    """
    Возвращает случайных текстов из указанных списков.
    Если списки одинаковые, гарантирует что тексты разные.
    """

    # Выбираем случайный текст из базового списка
    base_text_item = random.choice(base_list_items)
    
    if base_list_id == other_list_id:
        # Если списки одинаковые, исключаем выбранный текст
        available_texts = [t for t in other_list_items if t != base_text_item]
        other_text_item = random.choice(available_texts)
    else:
        other_text_item = random.choice(other_list_items)
        
    return base_text_item, other_text_item


def get_length_text(text: TblText) -> int | None:
    """
    Возвращает длину текста в словах.
    """
    if not text:
        return None
    
    # Получаем содержимое текста
    words = text.get_content()
    return len(words) if words else None


def check_params(base_text_length: int, other_text_length: int, percent_of_inserts: float, fragment_size: int) -> tuple[bool, str]:
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


def validate_form(params: dict) -> tuple[bool, str]:
    """
    Проверяет корректность параметров формы генерации текста.
    
    Args:
        params: Словарь с параметрами формы
        
    Returns:
        tuple[bool, str]: (успех проверки, сообщение об ошибке)
    """
    # Проверяем указан ли список базовых текстов
    if not params.get('base_text_list'):
        return False, "Необходимо выбрать группу основных текстов"

    # Проверяем указан ли список вставляемых текстов    
    if not params.get('other_text_list'):
        return False, "Необходимо выбрать группу вставляемых текстов"

    # Если не случайные тексты, проверяем указаны ли они
    if not params.get('random_texts'):
        if not params.get('base_text'):
            return False, "Необходимо выбрать основной текст"
        if not params.get('other_text'): 
            return False, "Необходимо выбрать вставляемый текст"

    # Проверяем число кодов
    if not params.get('code_count') or int(params.get('code_count', 0)) < 1:
        return False, "Число кодов должно быть >= 1"

    # Проверяем процент вставок
    percent = params.get('percent_of_inserts')
    if not percent or not (0.01 <= float(percent) <= 0.95):
        return False, "Укажите долю вставок в диапазоне 0.01 - 0.95"

    # Проверяем размер фрагмента
    fragment_size = params.get('fragment_size') 
    if not fragment_size or int(fragment_size) < 5:
        return False, "Минимальный размер заменяемого фрагмента 5"

    return True, ""