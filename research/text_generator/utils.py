import random
import re
import nltk
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def adjust_to_sentence_borders(text, start, end):
    """
    Корректирует позиции start и end, чтобы они попадали на границы предложений.
    """
    sentences = nltk.sent_tokenize(text)
    words = text.split()
    word_positions = []
    current_pos = 0

    # Создаем список позиций слов
    for word in words:
        word_positions.append(current_pos)
        current_pos += len(word) + 1  # +1 для пробела

    # Находим ближайшие границы предложений
    char_pos = 0
    sentence_starts = [0]
    for sentence in sentences:
        char_pos += len(sentence) + 1  # +1 для пробела или знака препинания
        sentence_starts.append(char_pos)

    # Корректируем начальную позицию (start)
    start_char = word_positions[start] if start < len(word_positions) else word_positions[-1]
    new_start = start
    for i, pos in enumerate(sentence_starts):
        if pos > start_char:
            new_start = next((idx for idx, w_pos in enumerate(word_positions) if w_pos >= sentence_starts[i - 1]),
                             start)
            break

    # Корректируем конечную позицию (end)
    end_char = word_positions[end] if end < len(word_positions) else word_positions[-1]
    new_end = end
    for i, pos in enumerate(sentence_starts):
        if pos > end_char:
            new_end = next((idx for idx, w_pos in enumerate(word_positions) if w_pos >= sentence_starts[i - 1]),
                           end) - 1
            break

    return new_start, new_end


def generate_text_code(base_id, other_id, base_length, other_length, fragment_size, percent_of_inserts,
                       bind_borders=False, base_text=None, other_text=None):
    """
    Генерирует код для вставки текста.
    """
    logger.debug(
        f"Входные параметры: base_id={base_id}, other_id={other_id}, base_length={base_length}, other_length={other_length}")
    logger.debug(f"Тип базового текста: {type(base_text)}")
    logger.debug(f"Тип вставляемого текста: {type(other_text)}")

    # Конвертируем тексты в строки, если они являются объектами
    if hasattr(base_text, 'text'):
        logger.debug("У базового текста есть атрибут text")
        base_text_content = base_text.text.get_content()
    elif hasattr(base_text, 'get_content'):
        logger.debug("У базового текста есть метод get_content")
        base_text_content = base_text.get_content()
    else:
        logger.debug("Базовый текст в сыром виде")
        base_text_content = base_text

    # Аналогично для вставляемого текста
    if hasattr(other_text, 'text'):
        logger.debug("У вставляемого текста есть атрибут text")
        other_text_content = other_text.text.get_content()
    elif hasattr(other_text, 'get_content'):
        logger.debug("У вставляемого текста есть метод get_content")
        other_text_content = other_text.get_content()
    else:
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
            if max_base_step_size > 0:
                start_base_pos = random.randint(start_base_pos, start_base_pos + max_base_step_size)
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


def parse_code(code):
    """
    Парсит код и возвращает словарь с ID текстов и интервалами.
    """
    if not re.match(r"^(A\d+S\d+E\d+B\d+S\d+E\d+)+$", code):
        return None
    fragments = re.findall(r"([AB])(\d+)S(\d+)E(\d+)", code)
    result = {"id1": fragments[0][1], "id2": fragments[1][1], "intervals": {"A": [], "B": []}}
    for i in range(0, len(fragments), 2):
        result["intervals"]["A"].append({"S": int(fragments[i][2]), "E": int(fragments[i][3])})
        result["intervals"]["B"].append({"S": int(fragments[i + 1][2]), "E": int(fragments[i + 1][3])})
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
    
    # Обрабатываем каждый интервал
    for i in range(len(parsed["intervals"]["A"])):
        # Добавляем фрагмент базового текста
        start = parsed["intervals"]["A"][i]["S"]
        for word in base_words[base_pos:start]:
            # Проверяем изменение абзаца
            start_paragraph = word.paragraph_index > prev_paragraph
            if start_paragraph:
                prev_paragraph = word.paragraph_index
            result.append({
                'word': word.word,
                'start_paragraph': start_paragraph,
                'highlight': False
            })
            
        # Добавляем фрагмент вставляемого текста
        other_start = parsed["intervals"]["B"][i]["S"]
        other_end = parsed["intervals"]["B"][i]["E"] + 1
        
        for word in other_words[other_start:other_end]:
            # Для вставляемого текста не отслеживаем абзацы
            result.append({
                'word': word.word,
                'start_paragraph': False,
                'highlight': True
            })
            
        base_pos = parsed["intervals"]["A"][i]["E"] + 1

    # Добавляем оставшуюся часть базового текста
    for word in base_words[base_pos:]:
        # Продолжаем отслеживать абзацы только для базового текста
        start_paragraph = word.paragraph_index > prev_paragraph 
        if start_paragraph:
            prev_paragraph = word.paragraph_index
        result.append({
            'word': word.word,
            'start_paragraph': start_paragraph,
            'highlight': False
        })

    return result