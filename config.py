from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
STORAGE_DIR = BASE_DIR / "storage" / "data"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = STORAGE_DIR / "simulations.db"

# Launch site: Tarva
LAUNCH_LAT = 63.786667
LAUNCH_LON = 9.363056
LAUNCH_ELEVATION = 20  # m ASL

# Simulation defaults
DEFAULT_NUM_SIMULATIONS = 500
MAX_SIMULATIONS = 5000
MAX_WORKERS = 8
TRAJECTORY_STORE_LIMIT = 50  # only store trajectories for first N runs
