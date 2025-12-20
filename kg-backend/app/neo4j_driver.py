import os, json
from dotenv import load_dotenv
from neo4j import GraphDatabase


LABEL_MAP = {
    "角色": "Character",
    "作品": "Work",
    "人物": "Person",
}

RELATION_MAP = {
    "出自作品": "APPEARS_IN",
    "声优": "VOICED_BY",
}

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


class Neo4jDriver:
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_character(self, name):
        with self.driver.session() as session:
            result = session.run(
                "MATCH (c:Character {name: $name}) "
                "RETURN c.name AS name, c.description AS description",
                name=name,
            )
            record = result.single()
            if record:
                return {"name": record["name"], "description": record["description"]}
            return None

    def search_characters(self, keyword, limit=10):
        with self.driver.session() as session:
            result = session.run(
                "MATCH (c:Character) "
                "WHERE c.name CONTAINS $keyword "
                "RETURN c.name AS name, c.description AS description "
                "LIMIT $limit",
                keyword=keyword,
                limit=limit,
            )
            return [
                {"name": r["name"], "description": r["description"]} for r in result
            ]

    def insert_triple(self, triple: dict):
        """
        插入单条三元组
        """
        with self.driver.session() as session:
            session.run(
                f"""
                MERGE (h:{LABEL_MAP[triple['head_type']]} {{name: $head}})
                MERGE (t:{LABEL_MAP[triple['tail_type']]} {{name: $tail}})
                MERGE (h)-[r:{RELATION_MAP[triple['relation']]}]->(t)
                SET r.source = $source
                """,
                head=triple["head"],
                tail=triple["tail"],
                source=triple.get("source"),
            )

    def insert_triples(self, triples: list[dict]):
        """
        批量插入三元组
        """
        with self.driver.session() as session:
            for triple in triples:
                print(triple["head_type"])
                session.run(
                    f"""
                    MERGE (h:{LABEL_MAP[triple['head_type']]} {{name: $head}})
                    MERGE (t:{LABEL_MAP[triple['tail_type']]} {{name: $tail}})
                    MERGE (h)-[r:{RELATION_MAP[triple['relation']]}]->(t)
                    SET r.source = $source
                    """,
                    head=triple["head"],
                    tail=triple["tail"],
                    source=triple.get("source"),
                )


if __name__ == "__main__":
    driver = Neo4jDriver()

    anime_path = "../../data/temp_triples_anime.json"
    role_path = "../../data/temp_triples_role.json"

    with open(anime_path, "r", encoding="utf-8") as f:
        anime_triplets = json.load(f)

    with open(role_path, "r", encoding="utf-8") as f:
        role_triplets = json.load(f)

    driver.insert_triples(anime_triplets)
    driver.insert_triples(role_triplets)
