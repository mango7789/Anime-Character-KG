'''
import os
import ahocorasick
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
'''

# ===============================
# 1. 规则实体匹配（Aho-Corasick）
# ===============================

'''
class RuleNER:
    """
    只负责识别【可指称实体节点】
    """

    def __init__(self, ent_dir="data/ent_aug"):
        # ✅ 只保留 entity_types
        self.entity_types = [
            "Work",
            "Character",
            "Person",
            "Organization",
            "Group",
            "Location",
        ]

        self.type2idx = {t: i for i, t in enumerate(self.entity_types)}
        self.automata = [ahocorasick.Automaton() for _ in self.entity_types]

        for ent_type in self.entity_types:
            path = os.path.join(ent_dir, f"{ent_type}.txt")
            if not os.path.exists(path):
                continue

            with open(path, encoding="utf-8") as f:
                for line in f:
                    ent = line.strip()
                    if ent:
                        self.automata[self.type2idx[ent_type]].add_word(ent, ent)

        for a in self.automata:
            a.make_automaton()
        

    def find(self, text):

        results = []
        used = set()

        for idx, automaton in enumerate(self.automata):
            etype = self.entity_types[idx]
            for end, word in automaton.iter(text):
                start = end - len(word) + 1
                if any(i in used for i in range(start, end + 1)):
                    continue
                results.append((start, end, etype, word))
                for i in range(start, end + 1):
                    used.add(i)

        return results
'''
'''
class RuleNER:
    """
    只负责识别【可指称实体节点】
    """

    def __init__(self, ent_dir="data/ent_aug", min_len=2):
        self.entity_types = [
            "Work",
            "Character",
            "Person",
            "Organization",
            "Group",
            "Location",
        ]

        self.type2idx = {t: i for i, t in enumerate(self.entity_types)}
        self.automata = [ahocorasick.Automaton() for _ in self.entity_types]

        for ent_type in self.entity_types:
            path = os.path.join(ent_dir, f"{ent_type}.txt")
            if not os.path.exists(path):
                continue

            idx = self.type2idx[ent_type]

            with open(path, encoding="utf-8") as f:
                for line in f:
                    ent = line.strip()
                    if not ent:
                        continue

                    # 1️⃣ 完整实体
                    self.automata[idx].add_word(ent, (ent, ent))

                    # 2️⃣ 点分割名
                    if "·" in ent:
                        key = ent.split("·")[-1]
                        if len(key) >= min_len:
                            self.automata[idx].add_word(key, (key, ent))

                    # 3️⃣ 中文姓名尾部
                    if ent_type in ("Character", "Person") and len(ent) >= 3:
                        key = ent[-2:]
                        if len(key) >= min_len:
                            self.automata[idx].add_word(key, (key, ent))


        for a in self.automata:
            a.make_automaton()


    def find(self, text):
        """
        返回：
        [(start, end, entity_type, canonical_entity), ...]
        """
        results = []
        used = set()

        for idx, automaton in enumerate(self.automata):
            etype = self.entity_types[idx]
            for end, (alias, canonical) in automaton.iter(text):
                start = end - len(alias) + 1

                if any(i in used for i in range(start, end + 1)):
                    continue

                results.append((start, end, etype, canonical))
                for i in range(start, end + 1):
                    used.add(i)

        return results


# ===============================
# 2. TF-IDF 实体规范化
# ===============================


class TFIDFAligner:
    """
    用于：
    - 处理别名
    - 模糊匹配
    """

    def __init__(self, ent_dir="data/ent_aug"):
        self.type2ents = {}
        self.type2vecs = {}
        self.type2tfidf = {}

        for file in os.listdir(ent_dir):
            if not file.endswith(".txt"):
                continue

            ent_type = file.replace(".txt", "")
            path = os.path.join(ent_dir, file)

            with open(path, encoding="utf-8") as f:
                ents = [l.strip() for l in f if l.strip()]

            if not ents:
                continue

            tfidf = TfidfVectorizer(analyzer="char")
            vecs = tfidf.fit_transform(ents).toarray()

            self.type2ents[ent_type] = ents
            self.type2vecs[ent_type] = vecs
            self.type2tfidf[ent_type] = tfidf

    def align(self, ner_results, threshold=0.5):
        """
        输出格式：
        {
            "Work": ["咒术回战"],
            "Character": ["五条悟"]
        }
        """
        result = {}

        for _, _, ent_type, word in ner_results:
            if ent_type not in self.type2tfidf:
                continue

            qv = self.type2tfidf[ent_type].transform([word])
            sims = cosine_similarity(qv, self.type2vecs[ent_type])[0]
            idx = sims.argmax()

            if sims[idx] >= threshold:
                result.setdefault(ent_type, []).append(self.type2ents[ent_type][idx])

        return result


# ===============================
# 3. 对外统一接口
# ===============================


def get_ner_result(model, tokenizer, text, rule_ner, tfidf_aligner, device, idx2tag):
    """
    ⚠️ model / tokenizer / device / idx2tag 保留
    只是为了接口兼容 anime_kgqa.py
    """

    ner_raw = rule_ner.find(text)
    entities = tfidf_aligner.align(ner_raw)

    return entities
'''
import os
import ahocorasick
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ===============================
# 1. 规则实体匹配（Aho-Corasick）
# ===============================

class RuleNER:
    """
    只负责识别【可指称实体节点】
    """

    def __init__(self, ent_dir="data/ent_aug", min_len=2):
        self.entity_types = [
            "Work",
            "Character",
            "Person",
            "Organization",
            "Group",
            "Location",
        ]

        self.type2idx = {t: i for i, t in enumerate(self.entity_types)}
        self.automata = [ahocorasick.Automaton() for _ in self.entity_types]

        for ent_type in self.entity_types:
            path = os.path.join(ent_dir, f"{ent_type}.txt")
            if not os.path.exists(path):
                continue

            idx = self.type2idx[ent_type]

            with open(path, encoding="utf-8") as f:
                for line in f:
                    ent = line.strip()
                    if not ent:
                        continue

                    # 1️⃣ 完整实体
                    self.automata[idx].add_word(ent, (ent, ent))

                    # 2️⃣ 点分割名：蒙奇·D·路飞 → 路飞
                    if "·" in ent:
                        key = ent.split("·")[-1]
                        if len(key) >= min_len:
                            self.automata[idx].add_word(key, (key, ent))

                    # 3️⃣ 中文姓名尾部：漩涡鸣人 → 鸣人
                    if ent_type in ("Character", "Person") and len(ent) >= 3:
                        key = ent[-2:]
                        if len(key) >= min_len:
                            self.automata[idx].add_word(key, (key, ent))

        for a in self.automata:
            a.make_automaton()

    def find(self, text):
        """
        返回：
        [(start, end, entity_type, canonical_entity), ...]
        """
        results = []
        used = set()

        for idx, automaton in enumerate(self.automata):
            etype = self.entity_types[idx]
            for end, (alias, canonical) in automaton.iter(text):
                start = end - len(alias) + 1

                if any(i in used for i in range(start, end + 1)):
                    continue

                results.append((start, end, etype, canonical))
                for i in range(start, end + 1):
                    used.add(i)

        return results
# ===============================
# 2. TF-IDF 实体规范化 / 兜底
# ===============================

class TFIDFAligner:
    """
    用于：
    - 别名对齐
    - 模糊匹配
    - 全量兜底搜索
    """

    def __init__(self, ent_dir="data/ent_aug"):
        self.type2ents = {}
        self.type2vecs = {}
        self.type2tfidf = {}

        for file in os.listdir(ent_dir):
            if not file.endswith(".txt"):
                continue

            ent_type = file.replace(".txt", "")
            path = os.path.join(ent_dir, file)

            with open(path, encoding="utf-8") as f:
                ents = [l.strip() for l in f if l.strip()]

            if not ents:
                continue

            tfidf = TfidfVectorizer(analyzer="char")
            vecs = tfidf.fit_transform(ents).toarray()

            self.type2ents[ent_type] = ents
            self.type2vecs[ent_type] = vecs
            self.type2tfidf[ent_type] = tfidf

    def align(self, ner_results, threshold=0.5):
        """
        对规则 NER 的结果做规范化
        """
        result = {}

        for _, _, ent_type, word in ner_results:
            if ent_type not in self.type2tfidf:
                continue

            qv = self.type2tfidf[ent_type].transform([word])
            sims = cosine_similarity(qv, self.type2vecs[ent_type])[0]
            idx = sims.argmax()

            if sims[idx] >= threshold:
                result.setdefault(ent_type, []).append(
                    self.type2ents[ent_type][idx]
                )

        return result

    def search_best(self, query, ent_type="Character", threshold=0.3):
        """
        🔥 当 NER 完全失败时的兜底：
        在指定实体类型全集中找最相似实体
        """
        if ent_type not in self.type2tfidf:
            return None

        tfidf = self.type2tfidf[ent_type]
        ents = self.type2ents[ent_type]
        vecs = self.type2vecs[ent_type]

        qv = tfidf.transform([query])
        sims = cosine_similarity(qv, vecs)[0]

        idx = sims.argmax()
        score = sims[idx]

        if score >= threshold:
            return ents[idx]

        return None
# ===============================
# 3. 对外统一接口（关键）
# ===============================

def get_ner_result(model, tokenizer, text, rule_ner, tfidf_aligner, device, idx2tag):
    """
    优先规则 NER
    规则 NER 失败 → TF-IDF 全量兜底
    """

    # ① 规则 NER
    ner_raw = rule_ner.find(text)

    if ner_raw:
        return tfidf_aligner.align(ner_raw)

    # ② 兜底：Character 实体全集模糊搜索
    fallback = tfidf_aligner.search_best(
        query=text,
        ent_type="Character",
        threshold=0.1,
    )

    if fallback:
        return {"Character": [fallback]}

    return {}
