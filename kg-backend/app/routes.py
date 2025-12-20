from flask import Blueprint, jsonify, request
from .neo4j_driver import Neo4jDriver
from .constants import DEFAULT_GRAPH

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
    return jsonify(DEFAULT_GRAPH)


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
