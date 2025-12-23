import re
import torch
import pickle
import random
from openai import OpenAI
from transformers import BertTokenizer
from py2neo import Graph

import ner_model as zwk

client = OpenAI(
    api_key="sk-tahcowcdmrkhavgytieftbuiwyejajagthkkesunkygznxvo",
    base_url="https://api.siliconflow.cn/v1",
)


def call_llm(system_prompt, user_prompt, temperature=0.3):
    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-7B-Instruct",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


# ===============================
# 1. 加载模型 & 资源
# ===============================


def load_resources():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ===== NER（规则 + TFIDF）=====
    rule_ner = zwk.RuleNER(ent_dir="data/ent_aug")
    tfidf_aligner = zwk.TFIDFAligner(ent_dir="data/ent_aug")

    # ===== Neo4j =====
    graph = Graph("http://localhost:7474", user="neo4j", password="anime123")

    # ⚠️ 这些返回 None 只是为了兼容旧接口
    ner_model = None
    tokenizer = None
    idx2tag = None

    return ner_model, tokenizer, rule_ner, tfidf_aligner, idx2tag, device, graph


# ===============================
# 2. 意图识别（动漫版）
# ===============================


def Intent_Recognition(query):
    system_prompt = f"""
你是一个【动漫知识图谱查询解析器】。"""
    user_prompt = f"""

你的任务是：
- 从用户问题中识别：
  1. 查询主体的实体类型（domain）
  2. 用户想查询的关系（relation，必须来自给定 schema）
  3. 是否为多实体关系查询（multi_entity）

--------------------
【可用关系 schema】

【Work 相关关系】
- OriginalAuthor
- ChiefDirector
- SeriesComposition
- CharacterDesigner
- Music
- ProductionCompany
- Publisher
- PublicationPeriod
- FirstAiringDate
- WorkCategory

【Character 属性关系】
- AppearsIn
- VoiceBy
- Alias
- BirthDate
- Gender
- Height
- Weight
- EyeColor
- HairColor
- LivingStatus
- MemberOf
- Origin
- ActiveArea
- CharacterTag

【Character 人物关系】
- HasParent
- HasFather
- HasMother
- HasAdoptiveFather
- HasAdoptiveMother
- HasAdoptiveParent
- HasGrandfather
- HasGrandmother
- HasOlderBrother
- HasYoungerBrother
- HasOlderSister
- HasYoungerSister
- HasUncle
- HasAunt
- HasCousin
- HasRelative
- HasChildhoodFriend
- HasFriend
- HasBestFriend
- HasCompanion
- HasMaster
- HasServant
- HasPeer
- HasMentor
- HasStudent
- HasSuperior
- HasSubordinate
- HasColleague
- HasEnemy
- HasRival
- HasLover
- HasSpouse
- IsPossessedBy
- IsHostOf

--------------------
【输出格式（严格 JSON，不要多余文字）】

{{
  "domain": "Character | Work | Person | Organization",
  "relation": "<关系名>",
  "multi_entity": true | false
}}

--------------------
【示例】

输入：路飞的声优是谁？
输出：
{{
  "domain": "Character",
  "relation": "VoiceBy",
  "multi_entity": false
}}

输入：路飞和索隆是什么关系？
输出：
{{
  "domain": "Character",
  "relation": "HasCompanion",
  "multi_entity": true
}}

输入：咒术回战的原作者是谁？
输出：
{{
  "domain": "Work",
  "relation": "OriginalAuthor",
  "multi_entity": false
}}

--------------------
用户输入：
"{query}"
"""

    return call_llm(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0)


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
        roles = entities["角色"]

        # ========= 情况 1：双角色关系（核心升级） =========
        if isinstance(roles, list) and len(roles) >= 2:
            a, b = roles[0], roles[1]
            cypher = f"""
            MATCH (x:角色 {{名称:'{a}'}})-[r]-(y:角色 {{名称:'{b}'}})
            RETURN type(r) AS rel
            """
            res = graph.run(cypher).data()

            prompt += "<提示>"
            prompt += f"用户查询角色 {a} 和 {b} 的关系，知识图谱信息如下："
            if res:
                prompt += "、".join([r["rel"] for r in res])
            else:
                prompt += "图谱中未找到两者之间的关系。"
            prompt += "</提示>"
            used = True

        # ========= 情况 2：单角色关系（原逻辑兜底） =========
        else:
            role = roles[0] if isinstance(roles, list) else roles
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
        answer = call_llm(
            system_prompt="你是一个动漫角色知识问答助手，必须严格基于给定提示回答。",
            user_prompt=prompt,
            temperature=0.3,
        )

        print(f"\n助手：{answer}")


if __name__ == "__main__":
    main()
