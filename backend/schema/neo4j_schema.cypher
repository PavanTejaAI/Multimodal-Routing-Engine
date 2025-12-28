CREATE CONSTRAINT road_node_id IF NOT EXISTS FOR (n:RoadNode) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT station_id IF NOT EXISTS FOR (n:Station) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT trip_id IF NOT EXISTS FOR (n:Trip) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT trip_event_id IF NOT EXISTS FOR (n:TripEvent) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT ev_point_id IF NOT EXISTS FOR (n:EVPoint) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT bike_hub_id IF NOT EXISTS FOR (n:BikeHub) REQUIRE n.id IS UNIQUE;

CREATE INDEX road_node_loc IF NOT EXISTS FOR (n:RoadNode) ON (n.location);
CREATE INDEX station_loc IF NOT EXISTS FOR (n:Station) ON (n.location);
CREATE INDEX ev_loc IF NOT EXISTS FOR (n:EVPoint) ON (n.location);
CREATE INDEX bike_loc IF NOT EXISTS FOR (n:BikeHub) ON (n.location);
CREATE INDEX trip_event_time IF NOT EXISTS FOR (n:TripEvent) ON (n.time);
