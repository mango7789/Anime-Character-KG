from flask import Blueprint, jsonify, request
from .neo4j_driver import Neo4jDriver
from .constants import ATTRIBUTE_RELATIONS, RELATION_RELATIONS

bp = Blueprint("api", __name__, url_prefix="/api")

driver = Neo4jDriver()


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

    # TODO: ner 识别
    # TODO: 构造 cypher 查询
    # TODO: 输入 LLM 生成回复

    answer = f"模拟回答: {query}"
    evidence = []
    subgraph = {
        "nodes": [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}],
        "links": [{"source": "1", "target": "2", "type": "friend"}],
    }
    focusNodeIds = ["1", "2"]

    return jsonify(
        {
            "answer": answer,
            "evidence": evidence,
            "subgraph": subgraph,
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
