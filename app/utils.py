import openrouteservice
import requests
import geopy.distance
from datetime import datetime
from config import OPENROUTESERVICE_API_KEY, WEATHERAPI_KEY, TOMTOM_API_KEY

client = openrouteservice.Client(key=OPENROUTESERVICE_API_KEY)

# --- Weather Functions ---
def get_weather_condition(lat, lon):
    try:
        url = "http://api.weatherapi.com/v1/current.json"
        params = {"key": WEATHERAPI_KEY, "q": f"{lat},{lon}"}
        response = requests.get(url, params=params)
        data = response.json()
        return data['current']['condition']['text']
    except Exception as e:
        return "Unknown"

def get_weather_penalty(condition):
    condition = condition.lower()
    if 'rain' in condition:
        return 10
    elif 'thunder' in condition:
        return 20
    elif 'fog' in condition or 'mist' in condition:
        return 5
    elif 'snow' in condition:
        return 15
    else:
        return 0

# --- Rush Hour Logic ---
def get_rush_hour_penalty(departure_time):
    try:
        dt = datetime.strptime(departure_time, "%H:%M")
        hour = dt.hour
        if 8 <= hour <= 10 or 17 <= hour <= 20:
            return 5  # Rush hour penalty
        return 0
    except:
        return 0

# --- TomTom Traffic ---
def get_traffic_penalty(lat, lon):
    try:
        url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
        params = {
            "point": f"{lat},{lon}",
            "unit": "KMPH",
            "key": TOMTOM_API_KEY
        }
        resp = requests.get(url, params=params).json()
        current_speed = resp["flowSegmentData"]["currentSpeed"]
        free_flow_speed = resp["flowSegmentData"]["freeFlowSpeed"]
        speed_diff = max(0, free_flow_speed - current_speed)
        return round(speed_diff * 0.5)  # 0.5 min penalty per km/h slowdown
    except Exception:
        return 0

# --- Main Routing Function ---
def get_routes_from_openrouteservice(source, destination, departure_time=None):
    try:
        # Coordinates
        source_coords = client.pelias_search(source)["features"][0]["geometry"]["coordinates"]
        dest_coords = client.pelias_search(destination)["features"][0]["geometry"]["coordinates"]
        coords = [source_coords, dest_coords]

        # Distance estimate
        dist_km = geopy.distance.distance(
            (source_coords[1], source_coords[0]),
            (dest_coords[1], dest_coords[0])
        ).km

        # Routing logic
        if dist_km < 100:
            routes = client.directions(
                coordinates=coords,
                profile='driving-car',
                format='json',
                alternative_routes={"share_factor": 0.6, "target_count": 3},
                instructions=True
            )
        else:
            routes = client.directions(
                coordinates=coords,
                profile='driving-car',
                format='json',
                instructions=True
            )

        # Build route info
        route_info_list = []
        for route in routes["routes"]:
            summary = route["summary"]
            distance_km = round(summary["distance"] / 1000, 2)
            duration_min = round(summary["duration"] / 60, 2)

            # External penalties
            lat, lon = dest_coords[1], dest_coords[0]
            weather = get_weather_condition(lat, lon)
            weather_penalty = get_weather_penalty(weather)
            rush_hour_penalty = get_rush_hour_penalty(departure_time)
            traffic_penalty = get_traffic_penalty(lat, lon)

            final_score = duration_min + weather_penalty + rush_hour_penalty + traffic_penalty

            route_info = {
                "distance_km": distance_km,
                "duration_min": duration_min,
                "weather": weather,
                "weather_penalty_min": weather_penalty,
                "rush_hour_penalty_min": rush_hour_penalty,
                "traffic_penalty_min": traffic_penalty,
                "final_score_min": final_score,
                "segments": route["segments"],
                "geometry": route["geometry"]
            }

            route_info_list.append(route_info)

        route_info_list.sort(key=lambda x: x["final_score_min"])  # Best route first
        return route_info_list

    except Exception as e:
        return {"error": str(e)}
