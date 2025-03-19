import random
import re
import nltk

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

    # Корректируем start
    start_char = word_positions[start] if start < len(word_positions) else word_positions[-1]
    new_start = start
    for i, pos in enumerate(sentence_starts):
        if pos > start_char:
            new_start = next((idx for idx, w_pos in enumerate(word_positions) if w_pos >= sentence_starts[i-1]), start)
            break

    # Корректируем end
    end_char = word_positions[end] if end < len(word_positions) else word_positions[-1]
    new_end = end
    for i, pos in enumerate(sentence_starts):
        if pos > end_char:
            new_end = next((idx for idx, w_pos in enumerate(word_positions) if w_pos >= sentence_starts[i-1]), end) - 1
            break

    return new_start, new_end

def generate_text_code(base_id, other_id, base_length, other_length, fragment_size, percent_of_inserts, bind_borders=False, base_text=None, other_text=None):
    """
    Генерирует код для вставки текста.
    """
    # Вычисляем количество вставок
    ins_count_base = round(base_length * percent_of_inserts / fragment_size)
    while ins_count_base * fragment_size > base_length:
        ins_count_base -= 1

    max_base_step_size = (
        (base_length - (ins_count_base * fragment_size)) // ins_count_base
        if ins_count_base else 0
    )

    ins_count_other = min(ins_count_base, other_text_length // fragment_size)
    max_other_step_size = (
        (other_length - (ins_count_other * fragment_size)) // ins_count_other
        if ins_count_other else 0
    )

    start_base_pos = 0
    start_other_pos = 0
    watermark = ""
    count_b = 0
    count_o = 0

    while count_b < ins_count_base:
        if base_length > fragment_size:
            start_base_pos = random.randint(start_base_pos, start_base_pos + max_base_step_size)
            if start_base_pos >= base_length:
                break
            end_base_pos = start_base_pos + fragment_size
            if end_base_pos > base_length:
                end_base_pos = base_length
        else:
            end_base_pos = base_length

        if count_o >= ins_count_other:
            count_o = 0
            start_other_pos = 0

        if other_length > fragment_size:
            start_other_pos = random.randint(start_other_pos, start_other_pos + max_other_step_size)
            if start_other_pos >= other_length:
                start_other_pos = random.randint(0, other_length - fragment_size)
            end_other_pos = start_other_pos + fragment_size
            if end_other_pos > other_length:
                end_other_pos = other_length
        else:
            end_other_pos = other_length

        # Привязка к границам предложений
        if bind_borders and base_text and other_text:
            start_base_pos, end_base_pos = adjust_to_sentence_borders(base_text, start_base_pos, end_base_pos - 1)
            start_other_pos, end_other_pos = adjust_to_sentence_borders(other_text, start_other_pos, end_other_pos - 1)
            end_base_pos += 1
            end_other_pos += 1

        watermark += (
            f"A{base_id}S{start_base_pos}E{end_base_pos-1}"
            f"B{other_id}S{start_other_pos}E{end_other_pos-1}"
        )
        count_b += 1
        count_o += 1
        start_base_pos = end_base_pos
        start_other_pos = end_other_pos

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
        result["intervals"]["B"].append({"S": int(fragments[i+1][2]), "E": int(fragments[i+1][3])})
    return result

def generate_text_by_code(code, base_text, other_text):
    """
    Генерирует текст на основе кода.
    """
    parsed = parse_code(code)
    if not parsed:
        return "Неверный код"

    base_words = base_text.split()
    other_words = other_text.split()
    result = []
    base_pos = 0

    for i in range(len(parsed["intervals"]["A"])):
        # Добавляем фрагмент основного текста
        start = parsed["intervals"]["A"][i]["S"]
        result.extend(base_words[base_pos:start])
        # Добавляем фрагмент вставляемого текста
        other_start = parsed["intervals"]["B"][i]["S"]
        other_end = parsed["intervals"]["B"][i]["E"] + 1
        result.extend(other_words[other_start:other_end])
        base_pos = parsed["intervals"]["A"][i]["E"] + 1

    # Добавляем остаток основного текста
    result.extend(base_words[base_pos:])
    return " ".join(result)