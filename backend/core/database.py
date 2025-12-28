from neo4j import GraphDatabase
import os
import time

class Neo4jConnector:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        
        max_retries = 12
        self.driver = None
        
        for attempt in range(max_retries):
            try:
                self.driver = GraphDatabase.driver(uri, auth=(user, password))
                self.driver.verify_connectivity()
                print(f"Successfully connected to Neo4j at {uri}")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Failed to connect to Neo4j after {max_retries} attempts.")
                    raise e
                print(f"Neo4j connection attempt {attempt+1}/{max_retries} failed. Retrying in 10s...")
                time.sleep(10)

    def query(self, cypher, parameters=None):
        with self.driver.session() as session:
            result = session.run(cypher, parameters)
            return [dict(record) for record in result]

    def write(self, cypher, parameters=None):
        with self.driver.session() as session:
            result = session.run(cypher, parameters)
            return result.consume()

    def close(self):
        if self.driver:
            self.driver.close()
