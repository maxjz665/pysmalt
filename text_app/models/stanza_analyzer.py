import os
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
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
        'PRON': 3,
        'PUNCT': 20,
        'SCONJ': 11,
        'SYM': 20,
        'VERB': 4,
        'X': 20
    }

    def __init__(self):
        #базовая станза
        self.nlp_base = stanza.Pipeline(lang='ru', processors='tokenize, lemma, pos, depparse')
        #дообученная станза (feats не полные)
        self.nlp_tr = stanza.Pipeline(lang='ru', processors='tokenize, pos',
                                       tokenize_model_path=os.getcwd() + "/text_app/stanza_models/99,99tok.pt",
                                       pos_model_path=os.getcwd() + "/text_app/stanza_models/94,48dualpos.pt")
        self.text_doc = None

    def analyze_text(self, text, base_mode=False):
        if base_mode:
            self.text_doc = self.nlp_base(text)
        else:
            self.text_doc = self.nlp_tr(text)
        return self.text_doc

    def search_word(self, s_word):
        for sentence in self.text_doc.sentences:
            for word in sentence.words:
                if word.text == s_word:
                    return word
        return None


    def analyze_word(self, word, base_mode=False):
        if self.text_doc:
            res = self.search_word(word)
            if res:
                return res
        if base_mode:
            doc = self.nlp_base(word)
        else:
            doc = self.nlp_tr(word)
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


    def get_sentence_with_punct(self, text):
        local_dir = os.getcwd() + "/text_app/sbert_model"
        tokenizer = AutoTokenizer.from_pretrained("kontur-ai/sbert_punc_case_ru", cache_dir=local_dir)
        model = AutoModelForTokenClassification.from_pretrained("kontur-ai/sbert_punc_case_ru", cache_dir=local_dir)
        classifier = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="first")

        def process_token(token, label):
            if "UPPER" in label:
                token = token.capitalize()
            if "TOTAL" in label:
                token = token.upper()

            punct_map = {
                "PERIOD": ".",
                "COMMA": ",",
                "QUESTION": "?",
                "TIRE": " —",
                "DVOETOCHIE": ":",
                "VOSKL": "!",
                "PERIODCOMMA": ";",
                "DEFIS": "-",
                "MNOGOTOCHIE": "...",
                "QUESTIONVOSKL": "?!",
            }

            for suffix, punct in punct_map.items():
                if suffix in label:
                    return token + punct
            return token

        preds = classifier(text)
        output = ""
        for item in preds:
            output += " " + process_token(item['word'].strip(), item['entity_group'])
        return output

    def get_member_of_sentence(self, pos, deprel):
        if deprel == 'obj':
            #print(pos)
            if pos == "ADV":
                return 'adverbial'
            else:
                return 'object'
        elif deprel in ['nsubj', 'csubj', 'nsubj:pass', 'nsubj:outer', 'csubj:pass']:
            return 'subject'  # Подлежащее
        elif deprel in ['root', 'cop', 'aux', 'aux:pass', 'xcomp']:
            return 'predicate'  # Сказуемое
        elif deprel in ['iobj', 'ccomp', 'obl', 'obl:agent', 'obl:tmod', 'nmod', 'appos']:
            return 'object'  # Дополнение
        elif deprel in ['advmod', 'obl:tmod', 'advcl']:
            return 'adverbial'  # Обстоятельство
        elif deprel in ['det', 'nummod', 'acl', 'amod']:
            return 'attribute'  # Определение
        else:
            return 'other'

    def get_syntax_roles(self, tokens):
        """
        Определяет только subject и predicate.
        """

        roles = {}

        subject_deprels = {"nsubj", "nsubj:pass", "csubj", "csubj:pass", "expl"}

        id_to_token = {tok.id: tok for tok in tokens}

        # 1. Подлежащее
        for tok in tokens:
            if tok.deprel in subject_deprels:
                roles[tok.id] = "subject"

        # 2. Сказуемое
        root = next((tok for tok in tokens if tok.head == 0), None)
        if root:
            if root.upos in {"VERB", "AUX"}:
                roles[root.id] = "predicate"
            else:
                # Ищем глагол-связку (copula)
                copulas = [tok for tok in tokens if tok.deprel == "cop" and tok.head == root.id]
                if copulas:
                    for cop in copulas:
                        roles[cop.id] = "predicate"
                    roles[root.id] = "predicate"  # можно обе части как предикат
                else:
                    # root без явного глагола — все равно играющее роль сказуемого
                    roles[root.id] = "predicate"

        # Результат
        result = []
        for tok in tokens:
            result.append({
                "text": tok.text,
                "upos": tok.upos,
                "deprel": tok.deprel,
                "role": roles.get(tok.id, "other")
            })

        return result

    '''def get_syntax_roles(self, tokens):
        """
        Принимает список токенов с полями:
            id, head, deprel, form/text, upos
        Возвращает список слов с пометками ролей: subject, predicate, object, adverbial, attribute
        """

        roles = {}

        # Карта соответствия dependency -> синтаксическая роль
        dep_to_role = {
            "nsubj": "subject",
            "nsubj:pass": "subject",
            "root": "predicate",
            "obj": "object",
            "iobj": "object",
            "obl": "adverbial",
            "advmod": "adverbial",
            "amod": "attribute",
            "nmod": "attribute",
            "acl": "attribute",
            "det": "attribute",
            "case": "attribute",
            "xcomp": "object",
            "ccomp": "object",
        }

        id_to_token = {tok.id: tok for tok in tokens}
        print(id_to_token)
        children = {tok.id: [] for tok in tokens}
        for tok in tokens:
            if tok.head != 0:
                children[tok.head].append(tok.id)

        def annotate_recursive(token_id, inherited_role=None):
            token = id_to_token[token_id]
            role = dep_to_role.get(token.deprel, inherited_role)
            roles[token_id] = role or "other"

            for child_id in children.get(token_id, []):
                child = id_to_token[child_id]
                if child.deprel == "case":
                    # Предлог получает роль от головы
                    roles[child_id] = role
                else:
                    annotate_recursive(child_id, role)

        # Найдём корень
        root = next(tok for tok in tokens if tok.head == 0)
        annotate_recursive(root.id, "predicate")

        # Собираем результат
        result = []
        for tok in tokens:
            result.append({
                "text": tok.text if hasattr(tok, "text") else tok.form,
                "upos": tok.upos,
                "deprel": tok.deprel,
                "role": roles.get(tok.id, "other")
            })

        return result'''


    def get_roles_of_sentence(self,sentence):
        annotated_words = []
        print(sentence)
        for i in range(0, len(sentence)):
            if sentence[i].deprel == "root":
                annotated_words.append({
                    'text': sentence[i].text,
                    'deprel': sentence[i].deprel,
                    'role': "predicate"
                })
            else:
                annotated_words.append({
                    'text': sentence[i].text,
                    'deprel': sentence[i].deprel,
                    'role': "other"
                })
        return annotated_words


    def analyze_sentence(self, sentence):
        doc = self.nlp_base(sentence)
        annotated_words = []
        res = []
        for sent in doc.sentences:
            #res = self.get_roles_of_sentence(sent.words)
            res += self.get_syntax_roles(sent.words)
            print(res)
            for word in sent.words:
                if word.upos == 'PUNCT':
                    continue
                annotated_words.append({
                    'text': word.text,
                    'deprel': word.deprel,
                    'role': self.get_member_of_sentence(word.upos, word.deprel)
                })
        return res
        #return annotated_words

    def get_feats_description(self, word):
        feats = self.parse_attrs(word)
        res_data = []
        #print(word.upos)
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
