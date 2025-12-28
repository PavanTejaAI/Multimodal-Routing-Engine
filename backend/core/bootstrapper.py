import os
import requests
import zipfile
from backend.ingestion.osm_loader import OSMLoader
from backend.ingestion.gtfs_loader import GTFSLoader
from backend.core.database import Neo4jConnector

class Bootstrapper:
    def __init__(self):
        self.db = Neo4jConnector()
        self.gtfs_url = os.getenv("HYDERABAD_GTFS_URL", "https://storage.googleapis.com/tumi-transit-data/hyderabad/hyderabad_gtfs.zip")
        self.data_dir = "/app/data"
        os.makedirs(self.data_dir, exist_ok=True)

    def run(self):
        print("Bootstrapper: Running system validation and ingestion...")
        
        is_empty = self.db.query("MATCH (n) RETURN count(n) as c")[0]["c"] == 0
        
        if is_empty:
            print("Database empty. Starting API-based ingestion...")
            
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:RoadNode) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Station) REQUIRE s.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (e:TripEvent) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (ev:EVPoint) REQUIRE ev.id IS UNIQUE",
                "CREATE INDEX IF NOT EXISTS FOR (n:RoadNode) ON (n.location)"
            ]
            for q in constraints:
                self.db.write(q)

            osm_loader = OSMLoader()
            osm_loader.load_network()
            
            gtfs_zip = os.path.join(self.data_dir, "gtfs.zip")
            gtfs_ext = os.path.join(self.data_dir, "gtfs")
            self._download_file(self.gtfs_url, gtfs_zip)
            with zipfile.ZipFile(gtfs_zip, 'r') as zip_ref:
                zip_ref.extractall(gtfs_ext)
            
            gtfs_loader = GTFSLoader(gtfs_ext)
            gtfs_loader.load_gtfs()
        else:
            print("Database already contains data, skipping ingestion.")

        print("Refreshing GDS Projection...")
        self.db.write("CALL gds.graph.drop('multimodal', false)")
        gds_query = """
        CALL gds.graph.project(
          'multimodal',
          {
            RoadNode: {properties: ['lat', 'lon']},
            Station: {properties: ['lat', 'lon']},
            TripEvent: {properties: ['lat', 'lon', 'time']}
          },
          {
            ROAD_SEGMENT: {properties: 'cost', orientation: 'UNDIRECTED'},
            WALK_TO: {properties: 'cost', orientation: 'UNDIRECTED'},
            HAS_EVENT: {properties: 'cost'},
            AT_STATION: {properties: 'cost'}
          }
        )
        """
        self.db.write(gds_query)
        print("System Ready.")

    def _download_file(self, url, dest):
        if os.path.exists(dest): return
        print(f"Downloading {url}...")
        r = requests.get(url, stream=True)
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
