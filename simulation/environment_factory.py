"""Build RocketPy Environment from weather data.

Ported from launch-server/weather.py with MC perturbation support.
"""

import numpy as np
import xarray as xr
import requests
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo
from rocketpy import Environment

from config import LAUNCH_LAT, LAUNCH_LON, LAUNCH_ELEVATION

g = 9.80665
USER_AGENT = "PropulseMC/1.0 propulse@ntnu.no"

_ds_cache: dict[str, xr.Dataset] = {}


def _get_dataset(path: str) -> xr.Dataset:
    ds = _ds_cache.get(path)
    if ds is None:
        with xr.open_dataset(path) as tmp:
            ds = tmp.load()
        _ds_cache[path] = ds
    return ds


def fetch_weather(lat: float, lon: float, timeout: int = 10) -> dict:
    """Fetch current weather from MET API (locationforecast)."""
    url = (
        f"https://api.met.no/weatherapi/locationforecast/2.0/compact"
        f"?lat={lat}&lon={lon}"
    )
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    r.raise_for_status()
    timeseries = r.json()["properties"]["timeseries"]

    ts_dt = lambda item: datetime.fromisoformat(item["time"].replace("Z", "+00:00"))
    timeseries.sort(key=ts_dt)
    now_utc = datetime.now(ZoneInfo("UTC"))

    current = max(
        (ts for ts in timeseries if ts_dt(ts) <= now_utc),
        key=ts_dt,
        default=timeseries[0],
    )

    d = current["data"]["instant"]["details"]
    return {
        "temperature": d["air_temperature"],
        "pressure": d["air_pressure_at_sea_level"],
        "wind_speed": d["wind_speed"],
        "wind_from_direction": d["wind_from_direction"],
        "humidity": d.get("relative_humidity", 50.0),
    }


def build_environment(
    climatology_file: str,
    lat: float = LAUNCH_LAT,
    lon: float = LAUNCH_LON,
    elevation: float = LAUNCH_ELEVATION,
    weather: dict | None = None,
    wind_speed_delta: float = 0.0,
    wind_direction_delta: float = 0.0,
    temperature_delta: float = 0.0,
    pressure_delta: float = 0.0,
) -> Environment:
    """Build a RocketPy Environment using ECMWF climatology + MET obs.

    For MC runs, deltas are added to the base weather values.
    """
    if weather is None:
        weather = fetch_weather(lat, lon)

    ds = _get_dataset(climatology_file)

    launch_time = datetime.now(ZoneInfo("Europe/Oslo"))
    ts_utc = launch_time.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    ts = np.datetime64(ts_utc)

    clim = ds.sel(time=ts, latitude=lat, longitude=lon, method="nearest")
    height = (clim["z"].values.astype(np.float32) / g).astype(np.float32)
    pressure_pa = (clim["level"].values.astype(np.float32) * 100.0).astype(np.float32)
    T_profile_base = clim["t"].values.astype(np.float32)

    pressure_profile = [(float(h), float(p)) for h, p in zip(height, pressure_pa)]

    # Apply temperature perturbation
    T_obs = weather["temperature"] + temperature_delta  # C
    T_obs_K = T_obs + 273.15
    T_surf_clim = float(np.interp(0.0, height, T_profile_base))
    delta_T = T_obs_K - T_surf_clim
    temp_arr = (T_profile_base + delta_T).astype(np.float32)
    temperature_profile = [(float(h), float(Ti)) for h, Ti in zip(height, temp_arr)]

    # Apply pressure perturbation (uniform shift)
    if pressure_delta != 0.0:
        pressure_profile = [(h, p + pressure_delta) for h, p in pressure_profile]

    # Wind from reanalysis profiles with MC perturbation
    u_base = clim["u"].values.astype(np.float32)
    v_base = clim["v"].values.astype(np.float32)

    # Apply direction perturbation via rotation matrix
    if wind_direction_delta != 0.0:
        theta = np.deg2rad(wind_direction_delta)
        cos_t, sin_t = np.cos(theta), np.sin(theta)
        u_rot = cos_t * u_base - sin_t * v_base
        v_rot = sin_t * u_base + cos_t * v_base
        u_base, v_base = u_rot, v_rot

    # Apply speed perturbation as multiplicative scaling
    if wind_speed_delta != 0.0:
        base_surface_speed = np.sqrt(
            float(np.interp(0.0, height, u_base)) ** 2
            + float(np.interp(0.0, height, v_base)) ** 2
        )
        if base_surface_speed > 0.1:
            scale = (base_surface_speed + wind_speed_delta) / base_surface_speed
            scale = max(scale, 0.0)  # prevent negative scaling
            u_base = u_base * scale
            v_base = v_base * scale

    wind_u_profile = [(float(h), float(u)) for h, u in zip(height, u_base)]
    wind_v_profile = [(float(h), float(v)) for h, v in zip(height, v_base)]

    env = Environment(
        max_expected_height=12000,
        latitude=lat,
        longitude=lon,
        elevation=elevation,
    )
    env.set_date(launch_time, timezone="Europe/Oslo")
    env.set_atmospheric_model(
        type="custom_atmosphere",
        pressure=pressure_profile,
        temperature=temperature_profile,
        wind_u=wind_u_profile,
        wind_v=wind_v_profile,
    )

    return env


def build_environment_from_file(
    atmosphere_file: str,
    lat: float = LAUNCH_LAT,
    lon: float = LAUNCH_LON,
    elevation: float = LAUNCH_ELEVATION,
) -> Environment:
    """Build environment directly from .nc reanalysis file (for single-run verification)."""
    env = Environment(
        date=(2024, 6, 26, 13),
        latitude=lat,
        longitude=lon,
        max_expected_height=12000,
        elevation=elevation,
    )
    env.set_atmospheric_model(
        type="Reanalysis",
        file=atmosphere_file,
        dictionary="ECMWF",
    )
    return env
