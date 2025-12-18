from neo4j import GraphDatabase


class Neo4jDriver:
    def __init__(self, uri, user, password):
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
