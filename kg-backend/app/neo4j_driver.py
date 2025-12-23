import os, json
from tqdm.auto import tqdm
from dotenv import load_dotenv
from neo4j import GraphDatabase
from .constants import ATTRIBUTE_RELATIONS

load_dotenv()
# NEO4J_URI = os.getenv("NEO4J_URI")
# NEO4J_USER = os.getenv("NEO4J_USER")
# NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_URI = "bolt://localhost:7688"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "anime123"


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

    def _insert_triple_tx(self, tx, triple: dict):
        """
        在同一个 transaction 中插入单条三元组
        """
        head = triple["head"]
        tail = triple["tail"]
        relation = triple["relation"]
        head_label = triple["head_type"]
        tail_label = triple["tail_type"]

        # 先保证 head 节点存在
        tx.run(
            f"MERGE (h:{head_label} {{name: $head}})",
            head=head,
        )

        # ===== 情况 1：tail 是属性 =====
        if tail_label in ATTRIBUTE_RELATIONS:
            tx.run(
                f"""
                MATCH (h:{head_label} {{name: $head}})
                SET h.{tail_label} = $value
                """,
                head=head,
                value=tail,
            )
            return

        # ===== 情况 2：tail 是实体 =====
        relation_safe = f"`{relation}`"
        tx.run(
            f"""
            MATCH (h:{head_label} {{name: $head}})
            MERGE (t:{tail_label} {{name: $tail}})
            MERGE (h)-[r:{relation_safe}]->(t)
            """,
            head=head,
            tail=tail,
        )

    def insert_triples(self, triples: list[dict]):
        """
        批量插入三元组（单事务）
        """

        def _tx_func(tx):
            for triple in tqdm(triples):
                self._insert_triple_tx(tx, triple)

        with self.driver.session() as session:
            session.execute_write(_tx_func)


if __name__ == "__main__":
    driver = Neo4jDriver()

    anime_path = "/home/zhengxiang/Anime-Character-KG/data/triples_anime.json"
    role_path = "/home/zhengxiang/Anime-Character-KG/data/triples_role.json"

    with open(anime_path, "r", encoding="utf-8") as f:
        anime_data = json.load(f)

    anime_triplets = []
    for triples in anime_data.values():
        anime_triplets.extend(triples)

    with open(role_path, "r", encoding="utf-8") as f:
        role_data = json.load(f)

    role_triplets = []
    for triples in role_data.values():
        role_triplets.extend(triples)

    driver.insert_triples(anime_triplets)
    driver.insert_triples(role_triplets)

    # # 清空数据库
    # with driver.driver.session() as session:
    #     session.run("MATCH (n) DETACH DELETE n")
