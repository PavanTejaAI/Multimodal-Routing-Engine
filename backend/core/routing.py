from backend.core.database import Neo4jConnector

class MultimodalRouter:
    def __init__(self):
        self.db = Neo4jConnector()

    def find_path(self, start_lat, start_lon, end_lat, end_lon, mode='transit'):
        snap_query = """
        MATCH (s:RoadNode) 
        WITH s, point.distance(s.location, point({latitude: $start_lat, longitude: $start_lon})) AS d 
        ORDER BY d LIMIT 1
        MATCH (e:RoadNode) 
        WITH s, e, point.distance(e.location, point({latitude: $end_lat, longitude: $end_lon})) AS d 
        ORDER BY d LIMIT 1
        RETURN s.id as start_node, e.id as end_node, 
               point.distance(s.location, point({latitude: $start_lat, longitude: $start_lon})) as start_dist,
               point.distance(e.location, point({latitude: $end_lat, longitude: $end_lon})) as end_dist
        """
        params = {
            "start_lat": start_lat, "start_lon": start_lon,
            "end_lat": end_lat, "end_lon": end_lon
        }
        snap_res = self.db.query(snap_query, params)
        if not snap_res:
            return {"segments": [], "totalCost": -1, "totalDistance": 0}
        
        node = snap_res[0]

        rel_types = []
        if mode == 'transit':
            rel_types = ['ROAD_SEGMENT', 'WALK_TO', 'HAS_EVENT', 'AT_STATION']
        elif mode == 'walk':
            rel_types = ['ROAD_SEGMENT', 'WALK_TO']
        else:
            rel_types = ['ROAD_SEGMENT']

        query = """
        MATCH (s:RoadNode {id: $start_id})
        MATCH (e:RoadNode {id: $end_id})
        CALL gds.shortestPath.astar.stream('multimodal', {
            sourceNode: s,
            targetNode: e,
            latitudeProperty: 'lat',
            longitudeProperty: 'lon',
            relationshipWeightProperty: 'cost',
            relationshipTypes: $rels
        })
        YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
        RETURN [nodeId IN nodeIds | gds.util.asNode(nodeId)] AS nodes, totalCost
        """
        try:
            results = self.db.query(query, {
                "start_id": node['start_node'], 
                "end_id": node['end_node'],
                "rels": rel_types
            })
        except Exception as e:
            if "GraphNotFoundException" in str(e):
                project_query = """
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
                self.db.write(project_query)
                results = self.db.query(query, {
                    "start_id": node['start_node'], 
                    "end_id": node['end_node'],
                    "rels": rel_types
                })
            else:
                raise e
        
        if not results:
            return {"segments": [], "totalCost": -1, "totalDistance": 0}

        res = results[0]
        nodes = res.get('nodes', [])
        total_cost = res.get('totalCost', 0)
        
        if total_cost == float('inf') or total_cost != total_cost:
             return {"segments": [], "totalCost": -1, "totalDistance": 0}

        segments = []
        current_segment = {"mode": "WALK", "coords": []}
        
        for i, node_data in enumerate(nodes):
            current_segment["coords"].append([node_data['lat'], node_data['lon']])
            
            if i < len(nodes) - 1:
                next_node = nodes[i+1]
                is_trip_curr = 'time' in node_data
                is_trip_next = 'time' in next_node
                
                if is_trip_curr and is_trip_next:
                    if current_segment["mode"] != "TRANSIT":
                        segments.append(current_segment)
                        current_segment = {"mode": "TRANSIT", "coords": [[node_data['lat'], node_data['lon']]]}
                elif is_trip_curr or is_trip_next: 
                     if current_segment["mode"] != "TRANSIT":
                        segments.append(current_segment)
                        current_segment = {"mode": "TRANSIT", "coords": [[node_data['lat'], node_data['lon']]]}
                else:
                    if current_segment["mode"] != "WALK":
                        segments.append(current_segment)
                        current_segment = {"mode": "WALK", "coords": [[node_data['lat'], node_data['lon']]]}

        segments.append(current_segment)
        
        total_distance = 0.0
        from math import radians, sin, cos, sqrt, atan2
        
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371000
            phi1, phi2 = radians(lat1), radians(lat2)
            dphi = radians(lat2 - lat1)
            dlambda = radians(lon2 - lon1)
            a = sin(dphi / 2)**2 + cos(phi1) * cos(phi2) * sin(dlambda / 2)**2
            return 2 * R * atan2(sqrt(a), sqrt(1 - a))

        for i in range(len(nodes) - 1):
            total_distance += haversine(
                nodes[i]['lat'], nodes[i]['lon'],
                nodes[i+1]['lat'], nodes[i+1]['lon']
            )
            
        return {"segments": segments, "totalCost": total_cost, "totalDistance": total_distance}
    
    def get_all_stations(self):
        query = """
        MATCH (s:Station)
        RETURN s.name as name, s.lat as lat, s.lon as lon
        """
        return self.db.query(query)

    def get_ev_routes(self, lat, lon):
        query = """
        MATCH (n:EVPoint)
        WHERE point.distance(n.location, point({latitude: $lat, longitude: $lon})) < 5000
        RETURN n.location, n.charger_type, n.sockets
        """
        return self.db.query(query, {"lat": lat, "lon": lon})

    def get_all_evs(self):
        query = """
        MATCH (n:EVPoint)
        RETURN n.lat as lat, n.lon as lon, n.charger_type as type
        """
        return self.db.query(query)

    def get_graph_bounds(self):
        query = """
        MATCH (n:RoadNode)
        RETURN min(n.lat) as min_lat, max(n.lat) as max_lat, 
               min(n.lon) as min_lon, max(n.lon) as max_lon
        """
        res = self.db.query(query)
        if res:
            return res[0]
        return None
