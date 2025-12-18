from flask import Blueprint, jsonify, request
from .neo4j_driver import Neo4jDriver

bp = Blueprint("api", __name__, url_prefix="/api")

# Neo4j 配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "anime123"

driver = Neo4jDriver(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)


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
