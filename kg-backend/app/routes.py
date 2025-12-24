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

def _intent_recognition(query: str, entities: dict) -> dict:
    system_prompt = """你是一个【动漫知识图谱查询解析器】。你的任务是从用户问题中识别：
1. query_mode: 这次查询要走哪种执行模式（查询属性/查询实体/探索关系）
2. query_predicate: 用哪个属性/关系作为查询谓词
3. source_entity_type: 查询从哪类实体节点出发
4. result_value_type: 查询最终返回的值类型（属性/实体/关系）

每个字段均为枚举型：
1. query_mode: get_property | get_entity | find_relation
2. query_predicate: 必须来自给定 schema
3. source_entity_type: Character | Work | Person | Organization
4. result_value_type: Property | Character | Work | Person | Organization | Relationship
除query_mode字段为单值外，其余字段允许多值（用|分隔）

严格按 JSON 格式输出（不要多余文字）：
{
  "query_mode": "...",
  "query_predicate": "...",
  "source_entity_type": "...",
  "result_value_type": "..."
}

---
【可用属性 schema】
【Character 属性关系】
- Alias
- BirthDate
- Gender
- Height
- Weight
- EyeColor
- HairColor
- LivingStatus
- Origin
- ActiveArea
- CharacterTag

---
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

【Character 相关关系】
- AppearsIn
- VoiceBy
- MemberOf
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
"""
    user_prompt = f"用户输入：\n\"{query}\"\n\n实体识别：\n\"{entities}\""
    raw = _call_llm(system_prompt, user_prompt, temperature=0.0)
    return _safe_json_loads(raw)

def build_cypher_plan(
    query_mode: str,
    query_predicate: str,
    source_entity_type: str,
    result_value_type: str,
    entities_by_type: dict,
):
    """
    返回：
      - plans: List[{"cypher": str, "params": dict, "plan_name": str}]
      - anchor: {"name": str, "type": str}
      - secondary: Optional[{"name": str, "type": str}]

    设计原则：
      1) 所有兜底/模板/回退都在这里做
      2) intent 不参与“选实体”之外的任何逻辑（但 mode 会决定是否需要 second）
    """

    ALLOWED_TYPES = {"Character", "Work", "Person", "Organization", "Group", "Location"}
    mode = (query_mode or "").strip()
    pred_raw = (query_predicate or "").strip()

    def _split_multi(s: str):
        return [x.strip() for x in (s or "").split("|") if x.strip()]

    def pick_first(t: str):
        arr = (entities_by_type or {}).get(t, [])
        return arr[0] if arr else None

    def pick_anchor():
        # ① 优先按 source_entity_type
        for t in _split_multi(source_entity_type):
            if t in ALLOWED_TYPES:
                v = pick_first(t)
                if v:
                    return v, t
        # ② 兜底按通用优先级
        for t in ["Character", "Work", "Person", "Organization", "Group", "Location"]:
            v = pick_first(t)
            if v:
                return v, t
        return None, None

    def pick_second(anchor_name: str, anchor_type: str):
        # second 只在 find_relation 强相关；其他模式尽量不引入噪声
        if mode != "find_relation":
            return None, None

        # 同类型第二个优先
        if anchor_type:
            arr = (entities_by_type or {}).get(anchor_type, [])
            if len(arr) >= 2:
                return arr[1], anchor_type

        # 否则找其它类型的第一个（避免等于 anchor）
        for t in ["Character", "Work", "Person", "Organization", "Group", "Location"]:
            arr2 = (entities_by_type or {}).get(t, [])
            if arr2 and arr2[0] != anchor_name:
                return arr2[0], t

        return None, None

    def match_anchor(anchor_type: str):
        # label 不可参数化，只能拼接；使用白名单避免注入
        if anchor_type in ALLOWED_TYPES:
            return f"(a:{anchor_type} {{name:$a}})"
        return "(a {name:$a})"

    def label_filter_clause(result_labels: list, var_name: str = "b"):
        # 过滤返回端 b 的 label，减少 get_entity 噪声
        if not result_labels:
            return ""
        return f" AND any(lbl IN labels({var_name}) WHERE lbl IN $result_labels) "

    # ---- 1) 选实体 ----
    anchor, anchor_type = pick_anchor()
    if not anchor:
        return [], None, None

    second, second_type = pick_second(anchor, anchor_type)

    # ---- 2) 解析 predicate / result labels ----
    # find_relation 必须 Unknown（或空），这里强制归一化
    if mode == "find_relation":
        pred_raw = "Unknown"

    preds = [p for p in _split_multi(pred_raw) if p.lower() != "unknown"]
    # result_value_type 里可出现 Property / Relationship，这些不是 label，过滤掉
    result_labels = [x for x in _split_multi(result_value_type) if x in ALLOWED_TYPES]

    plans = []

    # ---- 3) find_relation：两实体之间探索关系（不指定 predicate）----
    if mode == "find_relation":
        # 没 second 就无法 between，退化成邻居兜底（但这一般说明 NER 没抽到第二实体）
        if second:
            plans.append(
                {
                    "plan_name": "between_any_1hop",
                    "cypher": """
                        MATCH (a {name:$a})-[r]-(b {name:$b})
                        RETURN a, b, r
                        LIMIT 50
                    """,
                    "params": {"a": anchor, "b": second},
                }
            )
            # 一跳没有关系就查最短路径（<=5）
            plans.append(
                {
                    "plan_name": "between_shortest_path",
                    "cypher": """
                        MATCH p = allShortestPaths((a {name:$a})-[*..5]-(b {name:$b}))
                        RETURN nodes(p) AS shortest_nodes, relationships(p) AS shortest_rels, length(p) AS shortest_length
                        LIMIT 1
                    """,
                    "params": {"a": anchor, "b": second},
                }
            )

        # 最后兜底：拉一圈邻居（给 LLM 证据）
        plans.append(
            {
                "plan_name": "fallback_neighbors",
                "cypher": """
                    MATCH (a {name:$a})-[r]-(b)
                    RETURN a, b, r
                    LIMIT 50
                """,
                "params": {"a": anchor},
            }
        )

        return plans, {"name": anchor, "type": anchor_type}, (
            {"name": second, "type": second_type} if second else None
        )

    # ---- 4) get_property：查属性值（优先属性边）----
    if mode == "get_property":
        # predicate 为空时的兜底
        if not preds:
            plans.append(
                {
                    "plan_name": "fallback_neighbors",
                    "cypher": """
                        MATCH (a {name:$a})-[r]-(b)
                        RETURN a, b, r
                        LIMIT 50
                    """,
                    "params": {"a": anchor},
                }
            )
            return plans, {"name": anchor, "type": anchor_type}, None

        # plan1：只查属性边（ATTRIBUTE_RELATIONS）
        plans.append(
            {
                "plan_name": "property_edges_only",
                "cypher": f"""
                    MATCH {match_anchor(anchor_type)}-[r]-(b)
                    WHERE type(r) IN $preds AND type(r) IN $attr_rels
                    RETURN a, b, r
                    LIMIT 50
                """,
                "params": {"a": anchor, "preds": preds, "attr_rels": list(ATTRIBUTE_RELATIONS)},
            }
        )
        # plan2：放宽为通用谓词（有些“属性”可能被建成普通边）
        plans.append(
            {
                "plan_name": "property_by_predicate_fallback",
                "cypher": f"""
                    MATCH {match_anchor(anchor_type)}-[r]-(b)
                    WHERE type(r) IN $preds
                    RETURN a, b, r
                    LIMIT 50
                """,
                "params": {"a": anchor, "preds": preds},
            }
        )
        # plan3：最后兜底邻居
        plans.append(
            {
                "plan_name": "fallback_neighbors",
                "cypher": """
                    MATCH (a {name:$a})-[r]-(b)
                    RETURN a, b, r
                    LIMIT 50
                """,
                "params": {"a": anchor},
            }
        )
        return plans, {"name": anchor, "type": anchor_type}, None

    # ---- 5) get_entity：按 predicate 返回实体（可按 result_value_type 过滤）----
    if mode == "get_entity":
        # predicate 为空时：兜底邻居
        if not preds:
            plans.append(
                {
                    "plan_name": "fallback_neighbors",
                    "cypher": """
                        MATCH (a {name:$a})-[r]-(b)
                        RETURN a, b, r
                        LIMIT 50
                    """,
                    "params": {"a": anchor},
                }
            )
            return plans, {"name": anchor, "type": anchor_type}, None

        # plan1：按 predicate 查邻居，并过滤 b 的 label（如果识别到了 result_value_type）
        plans.append(
            {
                "plan_name": "entity_by_predicate_typed_b",
                "cypher": f"""
                    MATCH {match_anchor(anchor_type)}-[r]-(b)
                    WHERE type(r) IN $preds
                    {label_filter_clause(result_labels, "b")}
                    RETURN a, b, r
                    LIMIT 50
                """,
                "params": {"a": anchor, "preds": preds, "result_labels": result_labels},
            }
        )
        # plan2：不做 label 过滤（容错 result_value_type 错）
        plans.append(
            {
                "plan_name": "entity_by_predicate_no_type_filter",
                "cypher": f"""
                    MATCH {match_anchor(anchor_type)}-[r]-(b)
                    WHERE type(r) IN $preds
                    RETURN a, b, r
                    LIMIT 50
                """,
                "params": {"a": anchor, "preds": preds},
            }
        )
        # plan3：最后兜底邻居
        plans.append(
            {
                "plan_name": "fallback_neighbors",
                "cypher": """
                    MATCH (a {name:$a})-[r]-(b)
                    RETURN a, b, r
                    LIMIT 50
                """,
                "params": {"a": anchor},
            }
        )
        return plans, {"name": anchor, "type": anchor_type}, None

    # ---- 6) UNKNOWN mode：兜底邻居 ----
    plans.append(
        {
            "plan_name": "fallback_neighbors",
            "cypher": """
                MATCH (a {name:$a})-[r]-(b)
                RETURN a, b, r
                LIMIT 50
            """,
            "params": {"a": anchor},
        }
    )
    return plans, {"name": anchor, "type": anchor_type}, None


def _node_label(n):
    try:
        return next(iter(n.labels), "default")
    except Exception:
        return "default"

def _node_name(n):
    try:
        return n.get("name")
    except Exception:
        return None

def build_evidence_line(a_node, b_node, rel, attr_rels: set):
    a_name, a_label = _node_name(a_node), _node_label(a_node)
    b_name, b_label = _node_name(b_node), _node_label(b_node)
    rel_type = rel.type
    rel_props = dict(rel.items())

    # 属性边：优先用 rel_props.value，否则用 b_name 作为值
    if rel_type in attr_rels:
        val = rel_props.get("value")
        if val is None or val == "":
            val = b_name
        return f"{a_name}({a_label}) 的 {rel_type} 是 {val}"

    # 普通关系边：给出方向（按 start/end）
    src_name = _node_name(rel.start_node)
    tgt_name = _node_name(rel.end_node)
    # 方向字符串：如果 a_node 刚好是 start_node，就显示 a -> b，否则 b -> a
    if src_name == a_name and tgt_name == b_name:
        return f"{a_name}({a_label}) -[{rel_type}]-> {b_name}({b_label})"
    elif src_name == b_name and tgt_name == a_name:
        return f"{b_name}({b_label}) -[{rel_type}]-> {a_name}({a_label})"
    else:
        # 兜底：不强求方向一致
        return f"{a_name}({a_label}) -[{rel_type}]- {b_name}({b_label})"


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
    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "Missing 'query'"}), 400

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
    print(entities_by_type)

    # ========= ② 意图识别：LLM 输出 query_mode/query_predicate/source_entity_type/result_value_type =========
    intent = _intent_recognition(query, entities_by_type)
    query_mode = (intent.get("query_mode") or "").strip()
    query_predicate = (intent.get("query_predicate") or "").strip()
    source_entity_type = (intent.get("source_entity_type") or "").strip()
    result_value_type = (intent.get("result_value_type") or "").strip()
    print(intent)

    # ========= ③ 构造 Cypher：用 schema 关系去查图谱 =========
    evidence = []
    nodes = []
    links = []
    focusNodeIds = []

    plans, anchor, secondary = build_cypher_plan(
        query_mode=query_mode,
        query_predicate=query_predicate,
        source_entity_type=source_entity_type,
        result_value_type=result_value_type,
        entities_by_type=entities_by_type
    )

    if not plans or not anchor:
        return jsonify(
            {
                "answer": "根据已知信息无法回答该问题。",
                "evidence": [],
                "subgraph": {"nodes": [], "links": []},
                "focusNodeIds": [],
            }
        )

    ent_a, ent_a_type = anchor["name"], anchor["type"]
    ent_b, ent_b_type = secondary["name"] if secondary else None, secondary["type"] if secondary else None

    # 定位实体对应的节点
    with driver.driver.session() as session:
        if ent_a_type:
            rec = session.run(
                f"MATCH (n:{ent_a_type} {{name:$name}}) RETURN id(n) AS id",
                name=ent_a,
            ).single()
        else:
            rec = session.run(
                "MATCH (n {name:$name}) RETURN id(n) AS id",
                name=ent_a,
            ).single()
        if rec:
            focusNodeIds.append(str(rec["id"]))

        if ent_b and ent_b_type:
            rec2 = session.run(
                f"MATCH (n:{ent_b_type} {{name:$name}}) RETURN id(n) AS id",
                name=ent_b,
            ).single()
            if rec2:
                focusNodeIds.append(str(rec2["id"]))

    # 执行 plans：按顺序尝试，取第一个有结果的
    with driver.driver.session() as session:
        result_rows = []
        used_plan = None
        for p in plans:
            rows = list(session.run(p["cypher"], **p["params"]))
            if rows:
                result_rows = rows
                used_plan = p["plan_name"]
                break

        # 如果所有 plan 都没结果，就返回空（后面 evidence 会空）
        result = result_rows
        print("used_plan:", used_plan, "rows:", len(result_rows))

    # 组装 evidence + subgraph
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

    evidence_set = set()
    link_seen = set()
    MAX_EVIDENCE = 30
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

        # --- subgraph: 属性边写回节点；关系边进 links ---
        if rel_type in ATTRIBUTE_RELATIONS:
            a_id = a_node.id
            b_name = _node_name(b_node)
            if a_id in node_ids:
                node_ids[a_id]["properties"][rel_type] = rel_props.get("value", b_name)
        else:
            key = (src, tgt, rel_type)
            if key not in link_seen:
                link_seen.add(key)
                links.append(
                    {
                        "source": src,
                        "target": tgt,
                        "type": rel_type,
                        "properties": rel_props,
                    }
            )

        line = build_evidence_line(a_node, b_node, rel, set(ATTRIBUTE_RELATIONS))
        if line and line not in evidence_set:
            evidence_set.add(line)
            evidence.append(line)
            if len(evidence) >= MAX_EVIDENCE:
                break
    print(evidence)

    # ========= ④ LLM 根据证据生成答案（严格基于 evidence）=========
    if evidence and LLM_CLIENT.api_key:
        system_prompt = f"你是一个动漫/人物知识图谱问答助手，严格基于给定证据回答用户问题。"
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
        answer = "根据已知信息无法回答该问题。"

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
