"""
Reusable helper functions for the commute analysis pipeline.
Keeps the notebook clean by moving logic here.
"""

import requests
import os
import json
import time
import random
from config import GOOGLE_API_KEY
import geopandas as gpd
from geopy.distance import geodesic
from config import CRS_PROJECTED, CRS_GEOGRAPHIC
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime, timedelta
import pytz


def geocode_address(address: str) -> tuple[float, float, str]:
    """
    Converts a street address into latitude/longitude using Google's
    Geocoding API. Returns (lat, lon, formatted_address).
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_API_KEY}
    response = requests.get(url, params=params)
    data = response.json()

    if data["status"] == "OK":
        location = data["results"][0]["geometry"]["location"]
        formatted_address = data["results"][0]["formatted_address"]
        return location["lat"], location["lng"], formatted_address
    else:
        raise RuntimeError(f"Geocoding failed: {data['status']} - {data.get('error_message', '')}")
    



def generate_random_points(lat: float, lon: float, radius_m: float, n_points: int):
    """
    Generates random search points scattered within a circular study area
    around the office. These are NOT final employee homes yet - they're
    candidate search locations, each of which we'll later query for nearby
    real residential buildings to snap employees onto.
    Uses a projected CRS (metric) so the random scatter is distributed
    correctly in real-world meters, not distorted lat/lon degrees.
    """
    # Convert office point to the projected (metric) CRS
    office_point = gpd.GeoDataFrame(
        geometry=[Point(lon, lat)], crs=CRS_GEOGRAPHIC
    ).to_crs(CRS_PROJECTED)

    office_x = office_point.geometry.x.iloc[0]
    office_y = office_point.geometry.y.iloc[0]

    # Generate random points within a circle using polar coordinates,
    # so points are evenly distributed across the circular area (not
    # clustered near the center, which a naive x/y random approach would cause)
    angles = np.random.uniform(0, 2 * np.pi, n_points)
    radii = radius_m * np.sqrt(np.random.uniform(0, 1, n_points))

    xs = office_x + radii * np.cos(angles)
    ys = office_y + radii * np.sin(angles)

    points = [Point(x, y) for x, y in zip(xs, ys)]

    # Build GeoDataFrame in the projected CRS, then convert back to lat/lon
    # since that's what we need for Overpass queries and Google APIs
    points_gdf = gpd.GeoDataFrame(geometry=points, crs=CRS_PROJECTED).to_crs(CRS_GEOGRAPHIC)
    points_gdf["employee_id"] = range(1, n_points + 1)

    return points_gdf




def get_nearby_buildings(lat: float, lon: float, radius_m: float = 400):
    """
    Queries a small radius (300-500m) around a single search point for
    real residential building nodes/ways. Small queries are fast and
    reliable on Overpass's public server, unlike one large area-wide query.
    Returns a list of (lat, lon) tuples for buildings found near this point.
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    (
      node["building"~"residential|house|apartments|detached|terrace"](around:{radius_m},{lat},{lon});
      way["building"~"residential|house|apartments|detached|terrace"](around:{radius_m},{lat},{lon});
    );
    out center;
    """
    headers = {"User-Agent": "jnj-assessment-notebook"}

    try:
        response = requests.get(overpass_url, params={"data": query}, headers=headers, timeout=30)
        if response.status_code != 200:
            return []
        data = response.json()
    except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError):
        return []

    buildings = []
    for el in data.get("elements", []):
        if el["type"] == "node":
            buildings.append((el["lat"], el["lon"]))
        elif el["type"] == "way" and "center" in el:
            buildings.append((el["center"]["lat"], el["center"]["lon"]))

    return buildings

def find_building_with_retry(lat, lon, radii=[400, 800, 1500, 3000]):
    """
    Tries to find a nearby residential building, progressively widening
    the search radius if none is found at smaller radii. Only falls back
    to the raw search point if even 3km turns up nothing (should be rare).
    """
    for radius in radii:
        buildings = get_nearby_buildings(lat, lon, radius_m=radius)
        if buildings:
            return random.choice(buildings), radius
    return (lat, lon), None


def get_nearest_transit_stop(lat: float, lon: float, api_key: str, radius_m: int = 2000):
    """
    Uses Google Places API (New) to find the nearest public transit stop
    to a given coordinate. Returns the stop's name, coordinates, and the
    straight-line walking distance in meters. Returns None if no stop is
    found within the search radius.
    """
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.location"
    }
    body = {
        "includedTypes": ["train_station", "subway_station", "bus_station", "transit_station"],
        "maxResultCount": 1,
        "rankPreference": "DISTANCE",
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": radius_m
            }
        }
    }

    response = requests.post(url, headers=headers, json=body)
    data = response.json()

    places = data.get("places", [])
    if not places:
        return None

    stop = places[0]
    stop_name = stop.get("displayName", {}).get("text")
    stop_lat = stop["location"]["latitude"]
    stop_lon = stop["location"]["longitude"]

    distance_m = geodesic((lat, lon), (stop_lat, stop_lon)).meters

    return {
        "stop_name": stop_name,
        "stop_lat": stop_lat,
        "stop_lon": stop_lon,
        "distance_m": round(distance_m, 1)
    }




def get_next_weekday_8am(timezone_str="Europe/Berlin"):
    """
    Calculates the Unix timestamp for the next upcoming weekday (Mon-Fri) at
    8:00 AM local time, so all commute calculations reflect a realistic
    morning commute scenario rather than whatever time the code runs.
    """
    tz = pytz.timezone(timezone_str)
    now = datetime.now(tz)

    target = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)

    # If it lands on a weekend, roll forward to Monday
    while target.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        target += timedelta(days=1)

    return int(target.timestamp())


def get_transit_commute_time(origin_lat: float, origin_lon: float,
                               dest_lat: float, dest_lon: float, api_key: str,
                               departure_time: int):
    """
    Uses Google Directions API (transit mode) to calculate a real door-to-door
    public transport commute time between an employee's home and the workplace,
    for a specific departure time (as a Unix timestamp) - this ensures we get
    realistic weekday commute-hour transit schedules rather than routes based
    on whatever moment the code happens to run.
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_lat},{origin_lon}",
        "destination": f"{dest_lat},{dest_lon}",
        "mode": "transit",
        "departure_time": departure_time,
        "key": api_key
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data["status"] != "OK" or not data.get("routes"):
        return None

    route = data["routes"][0]
    leg = route["legs"][0]

    duration_min = leg["duration"]["value"] / 60

    transit_steps = [s for s in leg["steps"] if s["travel_mode"] == "TRANSIT"]
    num_transfers = max(0, len(transit_steps) - 1)

    walking_steps = [s for s in leg["steps"] if s["travel_mode"] == "WALKING"]
    total_walk_time_min = sum(s["duration"]["value"] for s in walking_steps) / 60

    return {
        "duration_min": round(duration_min, 1),
        "num_transfers": num_transfers,
        "walk_time_min": round(total_walk_time_min, 1),
        "num_transit_steps": len(transit_steps)
    }



def get_population_wikidata(place_name: str):
    """
    Queries Wikidata's SPARQL endpoint for a place's population.
    No API key or account needed - fully open access. Used to weight
    synthetic employee sampling toward real population centers.
    """
    url = "https://query.wikidata.org/sparql"
    query = f"""
    SELECT ?population WHERE {{
      ?place rdfs:label "{place_name}"@en.
      ?place wdt:P1082 ?population.
    }}
    LIMIT 1
    """
    headers = {"Accept": "application/sparql-results+json", "User-Agent": "jnj-assessment-notebook"}
    response = requests.get(url, params={"query": query}, headers=headers)

    try:
        data = response.json()
        results = data["results"]["bindings"]
        if results:
            return int(results[0]["population"]["value"])
    except Exception:
        pass
    return 0

import pandas as pd

def build_population_weighted_surface(places_df, cache_path="data/places_with_population.csv"):
    """
    Attaches population data to each place once, using Wikidata, and caches
    the result. This is the expensive one-time step - after this, sampling
    any number of employees from it is instant and needs no new API calls.
    """
    if os.path.exists(cache_path):
        return pd.read_csv(cache_path)

    populations = []
    for i, row in places_df.iterrows():
        pop = get_population_wikidata(row["name"])
        populations.append(pop)
        time.sleep(0.3)  # light courtesy delay for Wikidata's shared endpoint

    places_df = places_df.copy()
    places_df["population"] = populations

    # Small villages that returned 0 (either genuinely tiny or not found in
    # Wikidata) get a small floor value, so they can still be sampled rarely
    # rather than being fully excluded from the model
    places_df["population"] = places_df["population"].replace(0, 50)

    places_df.to_csv(cache_path, index=False)
    return places_df




def sample_employees_by_population(places_df, n_employees, spread_km=2, seed=None):
    """
    Draws n_employees synthetic locations, weighted by real population using
    a square-root scaling. Square-root weighting was chosen after comparing
    linear (too dominated by Hamburg, ~70% of the sample), log (too flat,
    barely distinguishing Hamburg from small towns), and sqrt (balanced -
    Hamburg gets meaningfully more weight without swallowing the sample).
    """
    if seed is not None:
        np.random.seed(seed)

    weights = np.sqrt(places_df["final_population"])
    probs = weights / weights.sum()

    chosen_indices = np.random.choice(places_df.index, size=n_employees, replace=True, p=probs)
    chosen_places = places_df.loc[chosen_indices].reset_index(drop=True)

    lat_scatter = np.random.normal(0, spread_km / 111, n_employees)
    lon_scatter = np.random.normal(
        0, spread_km / (111 * np.cos(np.radians(chosen_places["lat"].mean()))), n_employees
    )

    return pd.DataFrame({
        "employee_id": range(1, n_employees + 1),
        "search_lat": chosen_places["lat"].values + lat_scatter,
        "search_lon": chosen_places["lon"].values + lon_scatter
    })


def commute_bucket(minutes):
    """
    Groups a commute time in minutes into the bands requested by the
    assessment brief: 30, 45, 60, and over 60 minutes.
    """
    if pd.isna(minutes):
        return "No transit route found"
    elif minutes <= 30:
        return "≤30 min"
    elif minutes <= 45:
        return "31-45 min"
    elif minutes <= 60:
        return "46-60 min"
    else:
        return ">60 min"


def calculate_adoption_score(row):
    """
    Calculates a 0-100 Deutschlandticket adoption potential score based on
    commute characteristics. Higher score = more likely to adopt. Uses a
    simple, transparent weighted formula (not a black-box model) so the
    logic is fully explainable: commute time (0-50 pts), walking distance
    to the nearest stop (0-25 pts), and number of transfers (0-25 pts).
    """
    if pd.isna(row["commute_time_min"]):
        return 0  # no viable transit route - lowest possible adoption potential

    time_score = max(0, min(50, 50 - (row["commute_time_min"] - 30) * (50 / 90)))
    walk_score = max(0, min(25, 25 - (row["distance_to_stop_m"] - 200) * (25 / 1300)))
    transfer_score = max(0, 25 - row["num_transfers"] * 8)

    return round(time_score + walk_score + transfer_score, 1)


def adoption_tier(score):
    """
    Groups a numeric adoption score into High (65+), Medium (35-64),
    or Low (under 35) tiers for easy interpretation.
    """
    if score >= 65:
        return "High"
    elif score >= 35:
        return "Medium"
    else:
        return "Low"


def find_nearest_place_name(lat, lon, places_df):
    """
    Finds the name of the real place closest to a given coordinate.
    Used to label geographic clusters with real place names instead
    of arbitrary cluster numbers.
    """
    distances = places_df.apply(
        lambda row: geodesic((lat, lon), (row["lat"], row["lon"])).meters, axis=1
    )
    nearest_idx = distances.idxmin()
    return places_df.loc[nearest_idx, "name"]

def search_wikidata_candidates(place_name, limit=5, max_retries=3):
    """
    Searches Wikidata's entity search API for candidate QIDs. Includes
    retry logic since Wikidata's shared endpoint can occasionally return
    non-JSON responses (rate limiting, transient errors) instead of a
    clean HTTP error.
    """
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": place_name,
        "language": "en",
        "type": "item",
        "limit": limit,
        "format": "json"
    }
    headers = {"User-Agent": "jnj-assessment-notebook"}

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            return data.get("search", [])
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.JSONDecodeError,
                json.JSONDecodeError):
            print(f"    Retry {attempt + 1}/{max_retries} for search: {place_name}")
            time.sleep(2)

    return []  # give up gracefully, don't crash the whole loop


def get_qid_coordinates_and_population(qid, max_retries=3):
    """
    Given a Wikidata QID, retrieves coordinates, population, and type
    labels. Includes the same retry/error handling as the search function.
    """
    if not qid:
        return (None, None), None, []

    url = "https://query.wikidata.org/sparql"
    query = f"""
    SELECT ?coord ?population ?typeLabel WHERE {{
      OPTIONAL {{ wd:{qid} wdt:P625 ?coord. }}
      OPTIONAL {{ wd:{qid} wdt:P1082 ?population. }}
      OPTIONAL {{
        wd:{qid} wdt:P31 ?type.
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
      }}
    }}
    """
    headers = {"Accept": "application/sparql-results+json", "User-Agent": "jnj-assessment-notebook"}

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params={"query": query}, headers=headers, timeout=10)
            data = response.json()
            results = data["results"]["bindings"]

            if not results:
                return (None, None), None, []

            coord_str = results[0].get("coord", {}).get("value")
            lat, lon = None, None
            if coord_str:
                coords = coord_str.replace("Point(", "").replace(")", "").split()
                lon, lat = float(coords[0]), float(coords[1])

            population = None
            for r in results:
                if "population" in r:
                    population = int(r["population"]["value"])
                    break

            types = [r["typeLabel"]["value"] for r in results if "typeLabel" in r]

            return (lat, lon), population, types

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.JSONDecodeError,
                json.JSONDecodeError):
            print(f"    Retry {attempt + 1}/{max_retries} for QID: {qid}")
            time.sleep(2)

    return (None, None), None, []  # give up gracefully


def find_best_matching_qid(place_name, known_lat, known_lon, max_distance_km=15):
    """
    Finds the Wikidata entity that best matches a place name. Filters
    candidates to only those describing an actual settlement (city, town,
    village, municipality) BEFORE comparing distance - otherwise nearby
    but incorrect entity types (boroughs, railway stations, etc.) can
    incorrectly win just for being geographically closest.
    """
    candidates = search_wikidata_candidates(place_name)

    valid_settlement_keywords = ["city", "town", "municipality", "village", "market town"]
    invalid_keywords = ["railway station", "train station", "district of", "borough of", "neighbourhood", "neighborhood"]

    best_match = None
    best_distance = float("inf")

    for candidate in candidates:
        qid = candidate.get("id")
        description = candidate.get("description", "").lower()

        # Skip candidates whose description clearly indicates a non-settlement
        # or a sub-unit (borough/district) rather than the actual town/city
        if any(bad in description for bad in invalid_keywords):
            continue

        (cand_lat, cand_lon), population, types = get_qid_coordinates_and_population(qid)

        if cand_lat is None or cand_lon is None:
            continue

        # Require at least one positive settlement signal, either in the
        # search description or in the SPARQL-retrieved type labels
        combined_text = (description + " " + " ".join(types)).lower()
        is_settlement = any(keyword in combined_text for keyword in valid_settlement_keywords)

        if not is_settlement:
            continue

        distance_km = geodesic((known_lat, known_lon), (cand_lat, cand_lon)).km

        if distance_km < best_distance:
            best_distance = distance_km
            best_match = {
                "qid": qid,
                "description": candidate.get("description", ""),
                "population": population,
                "types": types,
                "distance_km": round(distance_km, 2)
            }

        time.sleep(0.2)

    if best_match and best_match["distance_km"] <= max_distance_km:
        return best_match

    return None
