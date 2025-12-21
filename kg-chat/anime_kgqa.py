import re
import torch
import pickle
import random
import ollama
from transformers import BertTokenizer
from py2neo import Graph

import ner_model as zwk  # 你已有的 ner_model.py


# ===============================
# 1. 加载模型 & 资源
# ===============================


def load_resources():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # NER 相关
    with open("tmp_data/tag2idx.npy", "rb") as f:
        tag2idx = pickle.load(f)
    idx2tag = list(tag2idx)

    rule = zwk.rule_find()
    tfidf_r = zwk.tfidf_alignment()

    model_name = "model/chinese-roberta-wwm-ext"
    tokenizer = BertTokenizer.from_pretrained(model_name)

    ner_model = zwk.Bert_Model(
        model_name=model_name, hidden_size=128, tag_num=len(tag2idx), bi=True
    )
    ner_model.load_state_dict(
        torch.load("model/best_roberta_rnn_model_ent_aug.pt", map_location=device)
    )
    ner_model.to(device)
    ner_model.eval()

    # Neo4j
    graph = Graph("http://localhost:7474", user="neo4j", password="your_password")

    return ner_model, tokenizer, rule, tfidf_r, idx2tag, device, graph


# ===============================
# 2. 意图识别（动漫版）
# ===============================


def Intent_Recognition(query, llm_name="qwen:32b"):
    prompt = f"""
你需要判断用户在动漫角色知识图谱中的查询意图。

【查询类别】
- 查询角色声优
- 查询角色所属作品
- 查询角色关系

【示例】
输入：路飞的声优是谁？
输出：["查询角色声优"] # 询问角色的配音演员

输入：鸣人是哪个作品里的？
输出：["查询角色所属作品"] # 查询角色来源作品

输入：佐助和鸣人是什么关系？
输出：["查询角色关系"] # 查询角色之间的关系

【要求】
- 输出必须来自上述查询类别
- 不超过 2 个
- 输出后用 # 简要解释

问题输入："{query}"
"""

    resp = ollama.generate(model=llm_name, prompt=prompt)["response"]
    return resp


# ===============================
# 3. KG 查询 + Prompt 构造
# ===============================


def build_prompt(intent_result, query, entities, graph):
    prompt = "<指令>你是一个动漫角色知识问答助手，必须完全基于提示回答。</指令>"
    prompt += "<指令>如果提示中没有答案，必须回答“根据已知信息无法回答该问题”。</指令>"

    used = False

    # ---------- 查询声优 ----------
    if "声优" in intent_result and "角色" in entities:
        role = entities["角色"]
        cypher = f"""
        MATCH (a:角色 {{名称:'{role}'}})-[:配音]->(b:声优)
        RETURN b.名称
        """
        res = graph.run(cypher).data()
        prompt += "<提示>"
        prompt += f"用户查询角色 {role} 的声优，知识图谱信息如下："
        if res:
            prompt += "、".join([list(r.values())[0] for r in res])
        else:
            prompt += "图谱中无相关信息。"
        prompt += "</提示>"
        used = True

    # ---------- 查询作品 ----------
    if "作品" in intent_result and "角色" in entities:
        role = entities["角色"]
        cypher = f"""
        MATCH (a:角色 {{名称:'{role}'}})-[:登场于]->(b:作品)
        RETURN b.名称
        """
        res = graph.run(cypher).data()
        prompt += "<提示>"
        prompt += f"用户查询角色 {role} 所属作品，知识图谱信息如下："
        if res:
            prompt += "、".join([list(r.values())[0] for r in res])
        else:
            prompt += "图谱中无相关信息。"
        prompt += "</提示>"
        used = True

    # ---------- 查询角色关系 ----------
    if "关系" in intent_result and "角色" in entities:
        role = entities["角色"]
        cypher = f"""
        MATCH (a:角色 {{名称:'{role}'}})-[r]->(b:角色)
        RETURN type(r) AS rel, b.名称 AS target
        """
        res = graph.run(cypher).data()
        prompt += "<提示>"
        prompt += f"用户查询角色 {role} 的角色关系，知识图谱信息如下："
        if res:
            rels = [f"{r['rel']} → {r['target']}" for r in res]
            prompt += "；".join(rels)
        else:
            prompt += "图谱中无相关信息。"
        prompt += "</提示>"
        used = True

    if not used:
        prompt += "<提示>知识库中没有可用信息。</提示>"

    prompt += f"<用户问题>{query}</用户问题>"
    return prompt


# ===============================
# 4. 主流程
# ===============================


def main():
    ner_model, tokenizer, rule, tfidf_r, idx2tag, device, graph = load_resources()
    llm_name = "qwen:32b"

    print("🎌 动漫角色知识问答系统已启动（输入 exit 退出）")

    while True:
        query = input("\n用户：")
        if query.lower() in ["exit", "quit"]:
            break

        # ① 实体识别
        entities = zwk.get_ner_result(
            ner_model, tokenizer, query, rule, tfidf_r, device, idx2tag
        )
        print(f"[NER] {entities}")

        # ② 意图识别
        intent = Intent_Recognition(query, llm_name)
        print(f"[Intent] {intent}")

        # ③ 构造 Prompt + 查 KG
        prompt = build_prompt(intent, query, entities, graph)

        # ④ LLM 输出答案
        answer = ollama.chat(
            model=llm_name, messages=[{"role": "user", "content": prompt}]
        )["message"]["content"]

        print(f"\n助手：{answer}")


if __name__ == "__main__":
    main()
