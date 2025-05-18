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
        # базовая станза
        self.nlp_base = stanza.Pipeline(lang='ru', processors='tokenize, lemma, pos, depparse')
        # дообученная станза (feats не полные)
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


    def analyze_sentence(self, sentence):
        doc = self.nlp_base(sentence)
        res = []
        for sent in doc.sentences:
            # res = self.get_roles_of_sentence(sent.words)
            tree = DependencyTree(sent)
            print(tree)
            tree.print_tree()
            res += DependencyTree.classify_annotated_words(tree)
        return res

    def get_feats_description(self, word):
        feats = self.parse_attrs(word)
        res_data = []
        # print(word.upos)
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


class DependencyNode:
    def __init__(self, id_, text, lemma, upos, deprel, head, feats):
        self.id = id_
        self.text = text
        self.lemma = lemma
        self.upos = upos
        self.deprel = deprel
        self.head = head  # id головного слова
        self.feats = feats
        self.children = []  # дочерние узлы

    def add_child(self, node):
        self.children.append(node)

    def __repr__(self):
        return f"{self.text} ({self.deprel})"


class DependencyTree:
    def __init__(self, sentence):
        self.nodes = {}
        self.roots = []

        # Создаём узлы
        for word in sentence.words:
            node = DependencyNode(
                id_=word.id,
                text=word.text,
                lemma=word.lemma,
                upos=word.upos,
                deprel=word.deprel,
                head=word.head,
                feats=self.parse_feats(word.feats)
            )
            self.nodes[word.id] = node

        # Связываем узлы
        for node in self.nodes.values():
            if node.head == 0:
                self.roots.append(node)
            else:
                head_node = self.nodes.get(node.head)
                if head_node:
                    head_node.add_child(node)

    @staticmethod
    def parse_feats(feats_str):
        if not feats_str:
            return {}
        feats_dict = {}
        for feat in feats_str.split('|'):
            if '=' in feat:
                key, value = feat.split('=')
                feats_dict[key] = value
        return feats_dict


    def get_roots(self):
        return self.roots

    def print_tree(self, node=None, level=0):
        if node is None:
            for root in self.roots:
                self.print_tree(root, level)
        else:
            print("  " * level + f"{node.text} ({node.deprel})")
            for child in node.children:
                self.print_tree(child, level + 1)

    @staticmethod
    def classify_annotated_words(tree):
        annotated_words = []
        found_subject = False
        node_roles = {}
        visited_ids = set()

        def annotate_node(node, role):
            annotated_words.append({
                'id': node.id,
                'text': node.text,
                'head': node.head,
                'deprel': node.deprel,
                'role': role
            })
            node_roles[node.id] = role
            visited_ids.add(node.id)

        def traverse(node, parent=None):
            nonlocal found_subject

            if node.id in visited_ids:
                return

            role = None

            if node.deprel in ['nsubj', 'nsubj:pass']:
                role = 'subject'
                found_subject = True
            elif node.deprel in ['conj', 'flat', 'flat:name']:
                parent_role = node_roles.get(node.head)
                if parent_role:
                    role = parent_role
                else:
                    role = 'other'
            elif node.deprel in ['root', 'conj', 'aux:pass'] and node.upos in ['VERB', 'AUX', 'ADJ']:
                role = 'predicate'
            elif node.deprel == 'root' and not found_subject and node.upos in ['NOUN', 'PRON']:
                role = 'subject'
                found_subject = True
            elif node.deprel == 'ccomp':
                role = 'predicate'  # вложенное сказуемое (придаточное)
            elif node.deprel == 'cop':
                role = 'predicate'  # глагол связка
            elif node.deprel == 'xcomp':
                verbform = node.feats.get('VerbForm') if node.feats else None

                if verbform == 'Inf':
                    # инфинитив — скорее всего часть составного сказуемого
                    parent_role = node_roles.get(node.head)
                    if parent_role in ['attribute']:
                        role = 'attribute'
                    else:
                        role = 'predicate'
                elif verbform == 'Part':
                    role = 'attribute'
                elif verbform == 'Conv':
                    # деепричастие — это обстоятельство образа действия
                    role = 'adverbial'
                else:
                    # по умолчанию — если непонятно
                    role = 'adverbial'
            elif node.deprel in ['obj', 'iobj']:
                role = 'object'
            elif node.deprel == 'obl':
                head_node = tree.nodes.get(node.head)
                case_child = next((c for c in node.children if c.deprel == 'case'), None)
                case_text = case_child.text.lower() if case_child else ""

                if case_text in ['в', 'на', 'под', 'при', 'между']:
                    role = 'adverbial'  # место
                elif case_text in ['с', 'без', 'от', 'до', 'для', 'из']:
                    role = 'adverbial'  # образ действия, причины
                elif head_node and head_node.upos == 'VERB':
                    if node.upos in ['NOUN', 'PRON']:
                        role = 'object'
                    elif node.upos == 'ADJ':
                        role = 'attribute'
                elif head_node and head_node.upos in ['NOUN', 'PRON', 'ADJ']:
                    role = 'attribute'
                else:
                    role = 'adverbial'
            elif node.deprel in ['advmod', 'advcl']:
                role = 'adverbial'
            elif node.deprel in ['amod', 'nmod', 'det', 'nummod', 'acl', 'nummod:gov', 'fixed']:
                role = 'attribute'
            elif node.deprel == 'appos':
                parent_role = node_roles.get(node.head)
                if parent_role in ['subject']:
                    role = 'subject'
                    found_subject = True
                else:
                    role = 'attribute'
            elif node.deprel == 'case':
                # case обрабатываем отдельно ниже
                role = None
            else:
                # Для всех прочих ролей - other
                role = 'other'

            if role:
                annotate_node(node, role)

            for child in node.children:
                if child.deprel == 'case':
                    if node.id in node_roles:
                        annotate_node(child, node_roles[node.id])
                    else:
                        annotate_node(child, 'other')
                elif child.deprel == 'mark':
                    # Тут можешь заменить на 'marker' если хочешь явно видеть союзы
                    #if node.id in node_roles:
                    #    annotate_node(child, node_roles[node.id])
                    #else:
                    annotate_node(child, 'other')
                else:
                    traverse(child, node)

        for root in tree.get_roots():
            traverse(root)

        # Обработка узлов, не попавших в обход
        for node in tree.nodes.values():
            if node.id not in visited_ids:
                inherited_role = node_roles.get(node.head, 'other')
                annotate_node(node, inherited_role)

        annotated_words.sort(key=lambda x: x['id'])
        return annotated_words
