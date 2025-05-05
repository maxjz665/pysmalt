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
        'X': 20  # неизвестная категория
        ### деепричастия и т д добавить
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

    def get_pos_id(self, word):
        pos = word.upos
        if pos in self.stanza_pos_mapping:
            if pos == "VERB":
                attrs = self.parse_attrs(word)
                if attrs and 'VerbForm' in attrs:
                    if attrs['VerbForm'] == "Part":  # причастие
                        return 5
                    if attrs['VerbForm'] == "Conv":  # деепричастие
                        return 6
            return self.stanza_pos_mapping[pos]
        else:
            return -1
