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
            LIMIT $top_n
            """,
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
        return jsonify({"error": "entityA 和 entityB 必须提供"}), 400

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

        # Memgraph 不支持 shortestPath(), 改用固定长度路径匹配
        result = session.run(
            """
            MATCH p = (a)-[r*..5]-(b)
            WHERE id(a) = $idA AND id(b) = $idB
            UNWIND nodes(p) AS n
            UNWIND relationships(p) AS rel
            RETURN collect(DISTINCT n) AS path_nodes, collect(DISTINCT rel) AS path_rels
            """,
            idA=idA,
            idB=idB,
        )

        record = result.single()
        path_nodes = record["path_nodes"] if record else []
        path_rels = record["path_rels"] if record else []

        node_ids = set()
        for n in path_nodes:
            nid = n.id
            if nid in node_ids:
                continue
            node_ids.add(nid)
            props = {k: v for k, v in n.items() if k != "name"}
            nodes.append(
                {
                    "id": nid,
                    "name": n.get("name"),
                    "group": next(iter(n.labels), "default"),
                    "properties": props,
                }
            )

        for r in path_rels:
            rel_type = r.type
            source_id = r.start_node.id
            target_id = r.end_node.id
            rel_props = dict(r.items())
            if rel_type in ATTRIBUTE_RELATIONS:
                for node in nodes:
                    if node["id"] == source_id:
                        node["properties"][rel_type] = rel_props.get("value", target_id)
            else:
                links.append(
                    {
                        "source": source_id,
                        "target": target_id,
                        "type": rel_type,
                        "properties": rel_props,
                    }
                )

    return jsonify(
        {
            "path": {"nodes": nodes, "links": links},
            "subgraph": {"nodes": nodes, "links": links},
            "focusNodeIds": [str(idA), str(idB)],
        }
    )


@bp.route("/qa", methods=["POST"])
def qa_route():
    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "Missing 'query'"}), 400

    answer = f"模拟回答: {query}"
    evidence = []
    subgraph = {
        "nodes": [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}],
        "links": [{"source": "1", "target": "2", "type": "friend"}],
    }
    focusNodeIds = ["1"]

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
        return jsonify({"error": "Missing 'name' parameter"}), 400

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
