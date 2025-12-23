import logging

logger = logging.getLogger(__name__)

from flask import Blueprint, jsonify, request
from .neo4j_driver import Neo4jDriver
from .constants import ATTRIBUTE_RELATIONS, RELATION_RELATIONS

bp = Blueprint("api", __name__, url_prefix="/api")

driver = Neo4jDriver()

# ============ 引入 kg-chat 里的 NER ============
import json
import re
from openai import OpenAI
from .ner_model import RuleNER, TFIDFAligner, get_ner_result

# 规则 NER + TFIDF 对齐（全局单例，避免每次请求都加载）
RULE_NER = RuleNER(ent_dir="app/ent_aug")
TFIDF_ALIGNER = TFIDFAligner(ent_dir="app/ent_aug")

# ============ LLM 客户端（OpenAI 兼容）============
LLM_CLIENT = OpenAI(
    api_key="sk-tahcowcdmrkhavgytieftbuiwyejajagthkkesunkygznxvo",
    base_url="https://api.siliconflow.cn/v1",
)
LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"


def _call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    # 如果没配置 key，就不给 LLM，后面会走模板回答
    if not LLM_CLIENT.api_key:
        return ""
    resp = LLM_CLIENT.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


def _safe_json_loads(s: str) -> dict:
    """
    允许 LLM 输出前后带一些无关文字，尽量从中抠出 JSON
    """
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        pass

    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def _intent_recognition(query: str) -> dict:
    system_prompt = "你是一个【动漫知识图谱查询解析器】。"
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
用户输入：
"{query}"
"""
    raw = _call_llm(system_prompt, user_prompt, temperature=0.0)
    return _safe_json_loads(raw)


@bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "pong"})


@bp.route("/character/<name>", methods=["GET"])
def get_character(name):
    char = driver.get_character(name)
    if char:
        return jsonify(char)
    else:
        return jsonify({"error": "Character not found"}), 404


@bp.route("/characters", methods=["GET"])
def search_characters():
    keyword = request.args.get("keyword", "")
    limit = int(request.args.get("limit", 10))
    results = driver.search_characters(keyword, limit)
    return jsonify(results)


@bp.route("/graph/init", methods=["POST"])
def init_graph():
    data = request.get_json() or {}
    view_mode = data.get("viewMode", "focus")

    if view_mode == "full":
        append_cypher = ""
    else:
        append_cypher = "LIMIT $top_n"
    nodes = []
    links = []
    TOP_N = 1000

    with driver.driver.session() as session:
        result = session.run(
            """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) AS degree
            WITH n, degree, labels(n)[0] AS label
            RETURN id(n) AS id, n.name AS name, label AS label, properties(n) AS props
            ORDER BY degree DESC
            """
            + append_cypher,
            top_n=TOP_N,
        )

        node_ids = set()
        label_seen = set()
        for record in result:
            nid = record["id"]
            label = record["label"]
            if nid not in node_ids or label not in label_seen:
                node_ids.add(nid)
                label_seen.add(label)

                # 过滤掉 name，保留其它属性（包括 ATTRIBUTE_RELATIONS）
                props = {k: v for k, v in record["props"].items() if k != "name"}
                nodes.append(
                    {
                        "id": nid,
                        "name": record["name"],
                        "group": label,
                        "properties": props,
                    }
                )

        if node_ids:
            result = session.run(
                """
                MATCH (a)-[r]->(b)
                WHERE id(a) IN $ids AND id(b) IN $ids
                RETURN id(a) AS source, id(b) AS target, type(r) AS type, properties(r) AS props
                """,
                ids=list(node_ids),
            )
            for record in result:
                rel_type = record["type"]
                source_id = record["source"]
                target_id = record["target"]
                rel_props = record["props"]

                if rel_type in ATTRIBUTE_RELATIONS:
                    for node in nodes:
                        if node["id"] == source_id:
                            node["properties"][rel_type] = rel_props.get(
                                "value", target_id
                            )
                    continue
                else:
                    links.append(
                        {
                            "source": source_id,
                            "target": target_id,
                            "type": rel_type,
                            "properties": rel_props,
                        }
                    )

    return jsonify({"nodes": nodes, "links": links})


@bp.route("/query-path", methods=["POST"])
def query_path():
    data = request.get_json()
    entityA = data.get("entityA")
    entityB = data.get("entityB")

    if not entityA or not entityB:
        return jsonify({"error": "实体 A 和实体 B 必须提供"}), 400

    if entityA == entityB:
        return jsonify({"error": "实体 A 和实体 B 不能相同"}), 400

    nodes = []
    links = []

    with driver.driver.session() as session:
        # 找出起点和终点节点
        result = session.run(
            "MATCH (a {name: $entityA}), (b {name: $entityB}) RETURN id(a) AS idA, id(b) AS idB",
            entityA=entityA,
            entityB=entityB,
        )
        record = result.single()
        if not record:
            return jsonify({"error": "找不到对应节点"}), 404

        idA, idB = record["idA"], record["idB"]

        # 获取最短路径
        result_shortest = session.run(
            """
            MATCH p = allShortestPaths((a)-[*..5]-(b))
            WHERE id(a) = $idA AND id(b) = $idB
            RETURN nodes(p) AS shortest_nodes, relationships(p) AS shortest_rels, length(p) AS shortest_length
            """,
            idA=idA,
            idB=idB,
        )

        record_shortest = result_shortest.single()
        shortest_nodes_seq = (
            record_shortest["shortest_nodes"] if record_shortest else []
        )
        shortest_rels_seq = record_shortest["shortest_rels"] if record_shortest else []
        shortest_length = record_shortest["shortest_length"] if record_shortest else 0

        # 把所有最短路径的节点和关系加入图，同时标记 is_shortest
        node_map = {}
        link_map = {}

        for n in shortest_nodes_seq:
            nid = n.id
            if nid not in node_map:
                props = {k: v for k, v in n.items() if k != "name"}
                node_map[nid] = {
                    "id": nid,
                    "name": n.get("name"),
                    "group": next(iter(n.labels), "default"),
                    "properties": props,
                }

        for r in shortest_rels_seq:
            rid = r.id
            rel_type = r.type
            source_id = r.start_node.id
            target_id = r.end_node.id
            rel_props = dict(r.items())
            if rel_type in ATTRIBUTE_RELATIONS:
                if source_id in node_map:
                    node_map[source_id]["properties"][rel_type] = rel_props.get(
                        "value", target_id
                    )
            else:
                link_map[rid] = {
                    "source": source_id,
                    "target": target_id,
                    "type": rel_type,
                    "properties": rel_props,
                    "is_shortest": True,
                }

        nodes = list(node_map.values())
        links = list(link_map.values())

    return jsonify(
        {
            "path": {"nodes": nodes, "links": links},
            "subgraph": {"nodes": nodes, "links": links},
            "shortest": {
                "length": shortest_length,
                "node_ids": [n.id for n in shortest_nodes_seq],
                "node_names": [n.get("name") for n in shortest_nodes_seq],
                "rel_ids": [r.id for r in shortest_rels_seq],
            },
            "focusNodeIds": [str(idA), str(idB)],
        }
    )


@bp.route("/qa", methods=["POST"])
def qa_route():
    # current_app.logger.info("qa_route 被调用")

    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "Missing 'query'"}), 400

    logger.info(f"QA请求: {query}")

    # answer = f"模拟回答: {query}"
    # evidence = []
    # subgraph = {
    #     "nodes": [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}],
    #     "links": [{"source": "1", "target": "2", "type": "friend"}],
    # }
    # focusNodeIds = ["1", "2"]

    # ========= ① NER：从自然语言里抽实体 =========
    # zwk.get_ner_result 接口需要 model/tokenizer/device/idx2tag，但在规则NER实现里是兼容占位
    entities_by_type = get_ner_result(
        model=None,
        tokenizer=None,
        text=query,
        rule_ner=RULE_NER,
        tfidf_aligner=TFIDF_ALIGNER,
        device=None,
        idx2tag=None,
    )
    # entities_by_type 形如 {"Work":[...], "Character":[...]}
    # 我们优先取 Character，其次 Work 等
    focus_entities = []
    for t in ["Character", "Work", "Person", "Organization", "Group", "Location"]:
        focus_entities.extend(entities_by_type.get(t, []))

    # ========= ② 意图识别：LLM 输出 domain/relation/multi_entity =========
    intent = _intent_recognition(query)
    domain = intent.get("domain") or ""
    relation = intent.get("relation") or ""
    multi_entity = bool(intent.get("multi_entity"))

    # ========= ③ 构造 Cypher：用 schema 关系去查图谱 =========
    evidence = []
    nodes = []
    links = []
    focusNodeIds = []

    # 没抽到实体时直接返回
    if not focus_entities:
        return jsonify(
            {
                "answer": "根据已知信息无法回答该问题。",
                "evidence": [],
                "subgraph": {"nodes": [], "links": []},
                "focusNodeIds": [],
            }
        )

    # 选实体：多实体取前2个，单实体取第1个
    ent_a = focus_entities[0]
    ent_b = focus_entities[1] if (multi_entity and len(focus_entities) >= 2) else None

    # 对关系做个兜底：如果 LLM 没给 relation，就尝试从 query 中猜一个
    # （你也可以删除这段，仅依赖 LLM）
    if not relation:
        # 简单启发式：包含“声优” -> VoiceBy
        if "声优" in query:
            relation = "VoiceBy"

    # 如果还是没有 relation：直接查“与该实体相关的边”做证据，再让 LLM 根据证据回答
    fallback_relation_free = False
    if not relation:
        fallback_relation_free = True

    with driver.driver.session() as session:
        # 先把 focus 实体对应的节点拿到（用于 focusNodeIds）
        # 优先按 domain label 找，如果 domain 为空就不限定 label
        if domain:
            rec = session.run(
                f"""
                MATCH (n:{domain} {{name:$name}})
                RETURN id(n) AS id, labels(n)[0] AS label, n.name AS name, properties(n) AS props
                """,
                name=ent_a,
            ).single()
        else:
            rec = session.run(
                """
                MATCH (n {name:$name})
                RETURN id(n) AS id, labels(n)[0] AS label, n.name AS name, properties(n) AS props
                """,
                name=ent_a,
            ).single()

        if rec:
            focusNodeIds.append(str(rec["id"]))

        if ent_b:
            if domain:
                rec2 = session.run(
                    f"""
                    MATCH (n:{domain} {{name:$name}})
                    RETURN id(n) AS id, labels(n)[0] AS label, n.name AS name, properties(n) AS props
                    """,
                    name=ent_b,
                ).single()
            else:
                rec2 = session.run(
                    """
                    MATCH (n {name:$name})
                    RETURN id(n) AS id, labels(n)[0] AS label, n.name AS name, properties(n) AS props
                    """,
                    name=ent_b,
                ).single()
            if rec2:
                focusNodeIds.append(str(rec2["id"]))

        # ---------- 主查询 ----------
        if fallback_relation_free:
            # 不指定关系：拉取实体的一圈邻居做证据
            result = session.run(
                """
                MATCH (a {name:$name})-[r]-(b)
                RETURN a, b, r
                LIMIT 50
                """,
                name=ent_a,
            )
        else:
            if ent_b:
                # 双实体关系查询：限定 type(r)=relation
                result = session.run(
                    """
                    MATCH (a {name:$a})-[r]-(b {name:$b})
                    WHERE type(r) = $rel
                    RETURN a, b, r
                    LIMIT 50
                    """,
                    a=ent_a,
                    b=ent_b,
                    rel=relation,
                )
            else:
                # 单实体：查询 a -[relation]-> x
                result = session.run(
                    """
                    MATCH (a {name:$a})-[r]->(b)
                    WHERE type(r) = $rel
                    RETURN a, b, r
                    LIMIT 50
                    """,
                    a=ent_a,
                    rel=relation,
                )

        # ---------- 组装 evidence + subgraph ----------
        node_ids = {}

        def _add_node(n):
            nid = n.id
            if nid in node_ids:
                return
            label = next(iter(n.labels), "default")
            props = dict(n.items())
            name = props.get("name")
            props = {k: v for k, v in props.items() if k != "name"}
            node_obj = {"id": nid, "name": name, "group": label, "properties": props}
            node_ids[nid] = node_obj
            nodes.append(node_obj)

        for record in result:
            a_node = record["a"]
            b_node = record["b"]
            rel = record["r"]

            _add_node(a_node)
            _add_node(b_node)

            rel_type = rel.type
            rel_props = dict(rel.items())
            src = rel.start_node.id
            tgt = rel.end_node.id

            # 属性边：写回 source 节点 properties
            if rel_type in ATTRIBUTE_RELATIONS:
                if src in node_ids:
                    node_ids[src]["properties"][rel_type] = rel_props.get(
                        "value", b_node.get("name")
                    )
                # evidence 也记一条
                val = rel_props.get("value") or b_node.get("name")
                evidence.append(f"{a_node.get('name')} 的 {rel_type} 是 {val}")
            else:
                links.append(
                    {
                        "source": src,
                        "target": tgt,
                        "type": rel_type,
                        "properties": rel_props,
                    }
                )
                evidence.append(
                    f"{a_node.get('name')} -[{rel_type}]-> {b_node.get('name')}"
                )

    # ========= ④ LLM 根据证据生成答案（严格基于 evidence）=========
    # 如果没配置 key，就用模板回答
    if evidence and LLM_CLIENT.api_key:
        system_prompt = "你是一个动漫/人物知识图谱问答助手，必须严格基于给定证据回答。"
        user_prompt = (
            "证据如下（只可使用这些证据）：\n"
            + "\n".join(f"- {e}" for e in evidence[:30])
            + f"\n\n用户问题：{query}\n"
            + "如果证据不足以回答，输出：根据已知信息无法回答该问题。"
        )
        answer = (
            _call_llm(system_prompt, user_prompt, temperature=0.3)
            or "根据已知信息无法回答该问题。"
        )
    else:
        # 模板：有证据就直接返回第一条/汇总，否则无法回答
        answer = evidence[0] if evidence else "根据已知信息无法回答该问题。"

    logger.info(f"返回结果: answer长度={len(answer)}, evidence数量={len(evidence)}")

    return jsonify(
        {
            "answer": answer,
            "evidence": evidence,
            "subgraph": {"nodes": nodes, "links": links},
            "focusNodeIds": focusNodeIds,
        }
    )


@bp.route("/recommend", methods=["POST"])
def recommend_route():
    data = request.get_json()
    name = data.get("name")
    limit = data.get("limit", 5)

    if not name:
        return jsonify({"error": "缺少实体"}), 400

    query = """
        MATCH (c:Character {name:$name})-[:FRIEND_OF]->(f)-[:FRIEND_OF]->(rec)
        WHERE NOT (c)-[:FRIEND_OF]->(rec) AND c <> rec
        RETURN rec.name AS name, COUNT(*) AS score
        ORDER BY score DESC
        LIMIT $limit
    """

    result = driver.run(query, name=name, limit=limit)
    items = [{"name": r["name"], "score": r["score"]} for r in result]

    subgraph = {
        "nodes": [{"id": name, "name": name}]
        + [{"id": r["name"], "name": r["name"]} for r in result],
        "links": [
            {"source": name, "target": r["name"], "type": "recommend"} for r in result
        ],
    }
    focusNodeIds = [name]

    return jsonify({"items": items, "subgraph": subgraph, "focusNodeIds": focusNodeIds})
