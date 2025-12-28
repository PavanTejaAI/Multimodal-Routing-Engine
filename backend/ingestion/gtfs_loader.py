import pandas as pd
import os
from backend.core.database import Neo4jConnector

class GTFSLoader:
    def __init__(self, gtfs_dir):
        self.db = Neo4jConnector()
        self.gtfs_dir = gtfs_dir

    def load_gtfs(self):
        stops = pd.read_csv(os.path.join(self.gtfs_dir, "stops.txt"))
        stop_batch = []
        for _, row in stops.iterrows():
            stop_batch.append({
                "id": str(row["stop_id"]),
                "name": row["stop_name"],
                "lat": float(row["stop_lat"]),
                "lon": float(row["stop_lon"])
            })
        
        stop_query = """
        UNWIND $batch AS data
        MERGE (s:Station {id: data.id})
        SET s.name = data.name,
            s.location = point({latitude: data.lat, longitude: data.lon}),
            s.lat = data.lat,
            s.lon = data.lon
        """
        self.db.write(stop_query, {"batch": stop_batch})

        stop_times = pd.read_csv(os.path.join(self.gtfs_dir, "stop_times.txt"))
        
        def time_to_sec(t_str):
            h, m, s = map(int, t_str.split(':'))
            return h * 3600 + m * 60 + s

        event_query = """
        UNWIND $batch AS data
        MATCH (s:Station {id: data.stop_id})
        MERGE (e:TripEvent {id: data.event_id})
        SET e.arrival_time = data.arr,
            e.departure_time = data.dep,
            e.trip_id = data.trip_id,
            e.lat = s.lat,
            e.lon = s.lon,
            e.location = s.location,
            e.time = data.arr
        MERGE (s)-[r:HAS_EVENT]->(e)
        SET r.cost = 0.0
        MERGE (e)-[r2:AT_STATION]->(s)
        SET r2.cost = 0.0
        """
        
        batch_size = 5000
        for i in range(0, len(stop_times), batch_size):
            batch = []
            chunk = stop_times.iloc[i:i+batch_size]
            for _, row in chunk.iterrows():
                batch.append({
                    "stop_id": str(row["stop_id"]),
                    "event_id": f"{row['trip_id']}_{row['stop_sequence']}",
                    "trip_id": str(row["trip_id"]),
                    "arr": time_to_sec(row["arrival_time"]),
                    "dep": time_to_sec(row["departure_time"])
                })
            self.db.write(event_query, {"batch": batch})
        
        transfer_query = """
        MATCH (s:Station)
        MATCH (n:RoadNode)
        WHERE point.distance(s.location, n.location) < 500
        MERGE (s)-[r:WALK_TO]->(n)
        SET r.distance = point.distance(s.location, n.location),
            r.cost = point.distance(s.location, n.location) / 1.4
        MERGE (n)-[r2:WALK_TO]->(s)
        SET r2.distance = point.distance(s.location, n.location),
            r2.cost = point.distance(s.location, n.location) / 1.4
        """
        self.db.write(transfer_query)
        
        fallback_query = """
        MATCH (s:Station)
        WHERE NOT (s)-[:WALK_TO]-()
        CALL {
            WITH s
            MATCH (n:RoadNode)
            WITH n, point.distance(s.location, n.location) AS dist
            ORDER BY dist ASC
            LIMIT 1
            RETURN n, dist
        }
        MERGE (s)-[r:WALK_TO]->(n)
        SET r.distance = dist,
            r.cost = dist / 1.4
        MERGE (n)-[r2:WALK_TO]->(s)
        SET r2.distance = dist,
            r2.cost = dist / 1.4
        """
        self.db.write(fallback_query)
        
        print("GTFS loading and connectivity established.")
