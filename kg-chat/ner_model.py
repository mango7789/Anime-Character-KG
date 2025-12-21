import os
import ahocorasick
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ===============================
# 1. 规则实体匹配（Aho-Corasick）
# ===============================


class rule_find:
    def __init__(self):
        self.idx2type = ["角色", "作品", "声优"]
        self.type2idx = {t: i for i, t in enumerate(self.idx2type)}
        self.ahos = [ahocorasick.Automaton() for _ in self.idx2type]

        for t in self.idx2type:
            path = os.path.join("data", "ent_aug", f"{t}.txt")
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                for line in f:
                    ent = line.strip()
                    if len(ent) >= 1:
                        self.ahos[self.type2idx[t]].add_word(ent, ent)

        for a in self.ahos:
            a.make_automaton()

    def find(self, text):
        results = []
        used = set()

        for idx, automaton in enumerate(self.ahos):
            etype = self.idx2type[idx]
            for end, word in automaton.iter(text):
                start = end - len(word) + 1
                if any(i in used for i in range(start, end + 1)):
                    continue
                results.append((start, end, etype, word))
                for i in range(start, end + 1):
                    used.add(i)

        return results


# ===============================
# 2. TF-IDF 对齐（实体规范化）
# ===============================


class tfidf_alignment:
    def __init__(self):
        self.tag2ents = {}
        self.tag2vec = {}
        self.tag2tfidf = {}

        base = os.path.join("data", "ent_aug")
        for file in os.listdir(base):
            if not file.endswith(".txt"):
                continue
            tag = file.replace(".txt", "")
            with open(os.path.join(base, file), encoding="utf-8") as f:
                ents = [l.strip() for l in f if l.strip()]
            if not ents:
                continue
            tfidf = TfidfVectorizer(analyzer="char")
            vec = tfidf.fit_transform(ents).toarray()
            self.tag2ents[tag] = ents
            self.tag2vec[tag] = vec
            self.tag2tfidf[tag] = tfidf

    def align(self, ent_list):
        result = {}
        for _, _, tag, word in ent_list:
            if tag not in self.tag2tfidf:
                continue
            qv = self.tag2tfidf[tag].transform([word])
            sims = cosine_similarity(qv, self.tag2vec[tag])[0]
            idx = sims.argmax()
            if sims[idx] >= 0.5:
                result[tag] = self.tag2ents[tag][idx]
        return result


# ===============================
# 3. 对外统一接口（anime_kgqa.py 用的）
# ===============================


def get_ner_result(model, tokenizer, text, rule, tfidf_r, device, idx2tag):
    """
    ⚠️ 注意：
    - model / tokenizer 在这里完全没用
    - 但接口必须保留，保证和 anime_kgqa.py 对齐
    """

    rule_res = rule.find(text)
    entities = tfidf_r.align(rule_res)
    return entities
