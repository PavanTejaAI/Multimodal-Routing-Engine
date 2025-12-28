import requests
from google.transit import gtfs_realtime_pb2
from backend.core.database import Neo4jConnector

class RealtimeFeeder:
    def __init__(self, feed_url):
        self.feed_url = feed_url
        self.db = Neo4jConnector()

    def update_delays(self):
        response = requests.get(self.feed_url)
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                self._apply_update(entity.trip_update)

    def _apply_update(self, update):
        query = """
        UNWIND $updates AS upd
        MATCH (e:TripEvent) 
        WHERE e.id STARTS WITH upd.trip_id + '_' + upd.stop_id
        SET e.delay = upd.delay,
            e.actual_time = datetime(e.time) + duration({seconds: upd.delay})
        """
        batch = []
        for stop_time_update in update.stop_time_update:
            batch.append({
                "trip_id": update.trip.trip_id,
                "stop_id": stop_time_update.stop_id,
                "delay": stop_time_update.arrival.delay
            })
        self.db.write(query, {"updates": batch})
