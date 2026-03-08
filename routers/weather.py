"""MET API weather proxy."""

from fastapi import APIRouter
from simulation.environment_factory import fetch_weather
from config import LAUNCH_LAT, LAUNCH_LON

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/current")
def get_current_weather():
    """Fetch current weather at launch site from MET API."""
    return fetch_weather(LAUNCH_LAT, LAUNCH_LON)
