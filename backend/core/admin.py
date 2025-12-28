from backend.core.database import Neo4jConnector

class AdminManager:
    def __init__(self):
        self.db = Neo4jConnector()

    def add_ev_point(self, data):
        query = """
        MERGE (ev:EVPoint {id: $id})
        SET ev.location = point({latitude: $lat, longitude: $lon}),
            ev.charger_type = $charger_type,
            ev.sockets = $sockets,
            ev.provider = $provider
        """
        self.db.write(query, data)

    def add_bike_hub(self, data):
        query = """
        MERGE (bh:BikeHub {id: $id})
        SET bh.location = point({latitude: $lat, longitude: $lon}),
            bh.capacity = $capacity,
            bh.has_ebikes = $has_ebikes
        """
        self.db.write(query, data)
