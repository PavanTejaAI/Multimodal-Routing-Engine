import requests
import time
import math
from backend.core.database import Neo4jConnector

class OSMLoader:
    def __init__(self, pbf_path=None, bbox="17.2,78.2,17.8,79.2"):
        self.db = Neo4jConnector()
        self.bbox = bbox
        self.overpass_url = "http://overpass-api.de/api/interpreter"
        self.speed_map = {
            "motorway": 100.0,
            "trunk": 80.0,
            "primary": 60.0,
            "secondary": 50.0,
            "tertiary": 40.0,
            "unclassified": 30.0,
            "residential": 30.0,
            "living_street": 20.0,
            "service": 15.0,
            "pedestrian": 5.0
        }

    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def load_network(self):
        query = f"""
        [out:json][timeout:600];
        (
          way["highway"]({self.bbox});
        );
        out body;
        >;
        out skel qt;
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(self.overpass_url, data={"data": query}, timeout=600)
                response.raise_for_status()
                data = response.json()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Overpass API failed after {max_retries} attempts: {e}")
                    return
                print(f"Overpass attempt {attempt+1} failed, retrying in 10s...")
                time.sleep(10)

        nodes = {str(n["id"]): n for n in data["elements"] if n["type"] == "node"}
        ways = [w for w in data["elements"] if w["type"] == "way"]

        node_batch = []
        for nid, n in nodes.items():
            node_batch.append({
                "id": nid,
                "lat": n["lat"],
                "lon": n["lon"]
            })
        
        node_query = """
        UNWIND $batch AS data
        MERGE (n:RoadNode {id: data.id})
        SET n.location = point({latitude: data.lat, longitude: data.lon}),
            n.lat = data.lat,
            n.lon = data.lon
        """
        batch_size = 5000
        for i in range(0, len(node_batch), batch_size):
            self.db.write(node_query, {"batch": node_batch[i:i+batch_size]})

        edge_batch = []
        for w in ways:
            highway = w.get("tags", {}).get("highway", "unclassified")
            speed = self.speed_map.get(highway, 30.0)
            
            w_nodes = w["nodes"]
            for i in range(len(w_nodes) - 1):
                u_id = str(w_nodes[i])
                v_id = str(w_nodes[i+1])
                if u_id in nodes and v_id in nodes:
                    u = nodes[u_id]
                    v = nodes[v_id]
                    
                    distance = self._haversine(u["lat"], u["lon"], v["lat"], v["lon"])
                    cost = (distance / 1000.0) / speed * 3600.0 if speed > 0 else distance
                    
                    edge_batch.append({
                        "u": u_id,
                        "v": v_id,
                        "distance": distance,
                        "speed_limit": speed,
                        "cost": cost
                    })

        edge_query = """
        UNWIND $batch AS data
        MATCH (u:RoadNode {id: data.u})
        MATCH (v:RoadNode {id: data.v})
        MERGE (u)-[r:ROAD_SEGMENT {distance: data.distance}]->(v)
        SET r.speed_limit = data.speed_limit,
            r.cost = data.cost
        MERGE (v)-[r2:ROAD_SEGMENT {distance: data.distance}]->(u)
        SET r2.speed_limit = data.speed_limit,
            r2.cost = data.cost
        """
        
        batch_size = 5000
        for i in range(0, len(edge_batch), batch_size):
            self.db.write(edge_query, {"batch": edge_batch[i:i+batch_size]})
        
        print(f"OSM ingestion complete: {len(node_batch)} nodes, {len(edge_batch)} segments.")
