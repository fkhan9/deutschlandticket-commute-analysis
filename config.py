"""
Central configuration for the J&J Deutschlandticket commute analysis project.
Holds constants and API key loading so the rest of the code doesn't repeat this.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env (contains GOOGLE_API_KEY)
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found — check your .env file")

# Workplace address - the fixed destination for all commute calculations
WORKPLACE_ADDRESS = "Robert-Koch-Straße 1, 22851 Norderstedt, Germany"

# Study area radius in meters - defines how far out from the workplace
# we look for residential buildings and synthetic employees
STUDY_RADIUS_M = 26000  # 25km

# Number of synthetic employees to generate
N_EMPLOYEES = 300

# Projected coordinate system for Germany (UTM zone 32N) - used for accurate
# distance/buffer calculations in meters, since raw lat/lon degrees aren't
# equal-distance and would distort real-world measurements
CRS_PROJECTED = "EPSG:25832"
CRS_GEOGRAPHIC = "EPSG:4326"  # standard lat/lon (WGS84), used for API calls and display

# File paths for cached data - avoids repeated API/OSM calls on every run
DATA_DIR = "data"
#BUILDINGS_CACHE = f"{DATA_DIR}/buildings.geojson"
#STOPS_CACHE = f"{DATA_DIR}/hvv_stops.geojson"


EMPLOYEES_CACHE = f"{DATA_DIR}/synthetic_employees.csv"

COMMUTE_RESULTS_CACHE = f"{DATA_DIR}/commute_results.csv"
UNIQUE_STOPS_CACHE = f"{DATA_DIR}/unique_stops_baseline.csv"
EMPLOYEE_STOP_MAPPING_CACHE = f"{DATA_DIR}/employee_stop_mapping_baseline.csv"
COMMUTE_TIMES_CACHE = f"{DATA_DIR}/commute_times_baseline.csv"

WEIGHTED_EMPLOYEES_CACHE = f"{DATA_DIR}/employees_weighted.csv"
UNIQUE_STOPS_WEIGHTED_CACHE = f"{DATA_DIR}/unique_stops_weighted.csv"
EMPLOYEE_STOP_MAPPING_WEIGHTED_CACHE = f"{DATA_DIR}/employee_stop_mapping_weighted.csv"
COMMUTE_TIMES_WEIGHTED_CACHE = f"{DATA_DIR}/commute_times_weighted.csv"

PLACES_WITH_POPULATION_CACHE = f"{DATA_DIR}/places_with_population.csv"