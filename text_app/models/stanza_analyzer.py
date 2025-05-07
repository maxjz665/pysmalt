import os

import stanza


class StanzaAnalyzer:
    stanza_pos_mapping = {
        'ADJ': 1,
        'ADP': 10,
        'ADV': 7,
        'AUX': 4,
        'CCONJ': 11,
        'INTJ': 13,
        'NOUN': 0,
        'NUM': 9,
        'PART': 9,
        'PROPN': 3,
        'PUNCT': 20,
        'SCONJ': 11,
        'SYM': 20,
        'VERB': 4,
        'X': 20
    }

    def __init__(self, mode=0):
        if mode == 0:
            self.nlp = stanza.Pipeline(lang='ru', processors='tokenize, lemma, pos, depparse')
        if mode == 1:
            self.nlp = stanza.Pipeline(lang='ru', processors='tokenize, pos',
                                       tokenize_model_path=os.getcwd() + "/text_app/stanza_models/99,983.pt",
                                       pos_model_path=os.getcwd() + "/text_app/stanza_models/79,18wfext.pt")
        self.text_doc = None

    def analyze_text(self, text):
        self.text_doc = self.nlp(text)
        return self.text_doc

    def search_word(self, s_word):
        for sentence in self.text_doc.sentences:
            for word in sentence.words:
                if word.text == s_word:
                    return word
        return None

    def analyze_word(self, word):
        if self.text_doc:
            res = self.search_word(word)
            if res:
                return res
        doc = self.nlp(word)
        return doc.sentences[0].words[0]

    def parse_attrs(self, word):
        if not word.feats or word.feats == "":
            return None
        spl_feats = word.feats.split("|")
        data = {}
        for feat in spl_feats:
            spl_feat = feat.split("=")
            feat_name = spl_feat[0]
            feat_val = spl_feat[1]
            data[feat_name] = feat_val
        return data

    def get_feats_description(self, word):
        feats = self.parse_attrs(word)
        res_data = []
        print(word.upos)
        if word.upos == "SCONJ":
            res_data.append({
                "name": "По синтаксической функции",
                "value": "Подчинительный"
            })
        if word.upos == "CCONJ":
            res_data.append({
                "name": "По синтаксической функции",
                "value": "Сочинительный"
            })
        if not feats:
            return res_data
        for key in feats.keys():
            if key == 'Animacy':
                if feats[key] == 'Anim':
                    res_data.append({
                        "name": "Разряд по значению(А)",
                        "value": "Одушевленное"
                    })
                elif feats[key] == 'Inan':
                    res_data.append({
                        "name": "Разряд по значению(А)",
                        "value": "Неодушевленное"
                    })

            elif key == 'Aspect':
                if feats[key] == 'Imp':
                    res_data.append({
                        "name": "Категория вида",
                        "value": "Несовершенный"
                    })
                elif feats[key] == 'Perf':
                    res_data.append({
                        "name": "Категория вида",
                        "value": "Совершенный"
                    })

            elif key == 'Case':
                case_map = {
                    'Nom': "Именительный",
                    'Gen': "Родительный",
                    'Dat': "Дательный",
                    'Acc': "Винительный",
                    'Ins': "Творительный",
                    'Loc': "Предложный",
                    'Voc': "Звательный"
                }
                if feats[key] in case_map:
                    res_data.append({
                        "name": "Категория падежа",
                        "value": case_map[feats[key]]
                    })

            elif key == 'Degree':
                if feats[key] == 'Pos':
                    res_data.append({
                        "name": "Степень сравнения",
                        "value": "Положительная"
                    })
                elif feats[key] == 'Comp':
                    res_data.append({
                        "name": "Степень сравнения",
                        "value": "Сравнительная"
                    })
                elif feats[key] == 'Sup':
                    res_data.append({
                        "name": "Степень сравнения",
                        "value": "Превосходная"
                    })

            elif key == 'Foreign':
                if feats[key] == 'Yes':
                    res_data.append({
                        "name": "Иностранное слово",
                        "value": "Да"
                    })
            elif key == 'Abbr':
                if feats[key] == 'Yes':
                    res_data.append({
                        "name": "Сокращенное слово",
                        "value": "Да"
                    })
            elif key == 'Gender':
                if feats[key] == 'Masc':
                    res_data.append({
                        "name": "Категория рода",
                        "value": "Мужской"
                    })
                elif feats[key] == 'Fem':
                    res_data.append({
                        "name": "Категория рода",
                        "value": "Женский"
                    })
                elif feats[key] == 'Neut':
                    res_data.append({
                        "name": "Категория рода",
                        "value": "Средний"
                    })

            elif key == 'Mood':
                if feats[key] == 'Ind':
                    res_data.append({
                        "name": "Категория наклонения",
                        "value": "Изъявительное"
                    })
                elif feats[key] == 'Imp':
                    res_data.append({
                        "name": "Категория наклонения",
                        "value": "Повелительное"
                    })

            elif key == 'NumType':
                if feats[key] == 'Card':
                    res_data.append({
                        "name": "Разряды по значению",
                        "value": "Количественное"
                    })
                elif feats[key] == 'Ord':
                    res_data.append({
                        "name": "Разряды по значению",
                        "value": "Порядковое"
                    })
                elif feats[key] == 'Mult':
                    res_data.append({
                        "name": "Разряды по значению",
                        "value": "Множительное"
                    })
                elif feats[key] == 'Frac':
                    res_data.append({
                        "name": "Разряды по значению",
                        "value": "Дробное"
                    })

            elif key == 'Number':
                if feats[key] == 'Sing':
                    res_data.append({
                        "name": "Категория числа",
                        "value": "Единственное"
                    })
                elif feats[key] == 'Plur':
                    res_data.append({
                        "name": "Категория числа",
                        "value": "Множественное"
                    })

            elif key == 'Person':
                if feats[key] == '1':
                    res_data.append({
                        "name": "Категория лица",
                        "value": "I"
                    })
                elif feats[key] == '2':
                    res_data.append({
                        "name": "Категория лица",
                        "value": "II"
                    })
                elif feats[key] == '3':
                    res_data.append({
                        "name": "Категория лица",
                        "value": "III"
                    })

            elif key == 'Polarity':
                if feats[key] == 'Neg':
                    res_data.append({
                        "name": "Полярность",
                        "value": "Отрицательная"
                    })

            elif key == 'Reflex':
                if feats[key] == 'Yes':
                    res_data.append({
                        "name": "Возвратность",
                        "value": "Возвратный"
                    })

            elif key == 'Tense':
                if feats[key] == 'Past':
                    res_data.append({
                        "name": "Категория времени",
                        "value": "Прошедшее"
                    })
                elif feats[key] == 'Pres':
                    res_data.append({
                        "name": "Категория времени",
                        "value": "Настоящее"
                    })
                elif feats[key] == 'Fut':
                    res_data.append({
                        "name": "Категория времени",
                        "value": "Будущее"
                    })

            elif key == 'Typo':
                if feats[key] == 'Yes':
                    res_data.append({
                        "name": "Опечатка",
                        "value": "Да"
                    })

            elif key == 'Variant':
                if feats[key] == 'Short':
                    res_data.append({
                        "name": "Вариант написания",
                        "value": "Краткая форма"
                    })

            elif key == 'VerbForm':
                if feats[key] == 'Fin':
                    res_data.append({
                        "name": "Форма глагола",
                        "value": "Личная"
                    })
                elif feats[key] == 'Inf':
                    res_data.append({
                        "name": "Форма глагола",
                        "value": "Инфинитив"
                    })
                elif feats[key] == 'Part':
                    res_data.append({
                        "name": "Форма глагола",
                        "value": "Причастие"
                    })
                elif feats[key] == 'Conv':
                    res_data.append({
                        "name": "Форма глагола",
                        "value": "Причастие страдательное"
                    })
                elif feats[key] == 'Ger':
                    res_data.append({
                        "name": "Форма глагола",
                        "value": "Деепричастие"
                    })

            elif key == 'Voice':
                if feats[key] == 'Act':
                    res_data.append({
                        "name": "Категория залога",
                        "value": "Действительный"
                    })
                elif feats[key] == 'Pass':
                    res_data.append({
                        "name": "Категория залога",
                        "value": "Страдательный"
                    })
            elif key == 'PronType':
                if feats[key] == 'Prs':
                    res_data.append({
                        "name": "Разряд по значению",
                        "value": "Личное"
                    })
                elif feats[key] == 'Rcp':
                    res_data.append({
                        "name": "Разряд по значению",
                        "value": "Возвратное"
                    })
                elif feats[key] == 'Int':
                    res_data.append({
                        "name": "Разряд по значению",
                        "value": "Вопросительное"
                    })
                elif feats[key] == 'Rel':
                    res_data.append({
                        "name": "Разряд по значению",
                        "value": "Относительное"
                    })
                elif feats[key] == 'Dem':
                    res_data.append({
                        "name": "Разряд по значению",
                        "value": "Указательное"
                    })
                elif feats[key] == 'Tot':
                    res_data.append({
                        "name": "Разряд по значению",
                        "value": "Тотальное"
                    })
                elif feats[key] == 'Neg':
                    res_data.append({
                        "name": "Разряд по значению",
                        "value": "Отрицательное"
                    })
                elif feats[key] == 'Ind':
                    res_data.append({
                        "name": "Разряд по значению",
                        "value": "Неопределённое"
                    })
            elif key == 'Subcat':
                if feats[key] == 'Intr':
                    res_data.append({
                        "name": "По отношению к объекту действия",
                        "value": "Непереходный"
                    })
                elif feats[key] == 'Tran':
                    res_data.append({
                        "name": "По отношению к объекту действия",
                        "value": "Переходный"
                    })
        return res_data

    def get_pos_id(self, word):
        pos = word.upos
        if pos in self.stanza_pos_mapping:
            if pos == "VERB":
                attrs = self.parse_attrs(word)
                if attrs and 'VerbForm' in attrs:
                    if attrs['VerbForm'] == "Part":  # причастие
                        return 5
                    if attrs['VerbForm'] == "Conv" or attrs['VerbForm'] == "Ger":  # деепричастие
                        return 6
            return self.stanza_pos_mapping[pos]
        else:
            return -1
