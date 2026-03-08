"""Monte Carlo simulation endpoints + WebSocket progress."""

import uuid
import json
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from models.params import RocketParams
from models.api_models import (
    MonteCarloRequest,
    MonteCarloResult,
    MonteCarloStatus,
    SimResult,
)
from simulation.monte_carlo import run_monte_carlo
from simulation.result_aggregator import aggregate_results
from simulation.environment_factory import fetch_weather
from simulation.single_run import run_single_simulation
from storage.database import save_run, update_run, get_run, list_runs, upsert_user, get_user_by_email
from storage.file_store import save_trajectories
from config import INPUTS_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulate", tags=["simulate"])

# In-memory state for active runs
_active_runs: dict[str, dict[str, Any]] = {}


def _run_mc_background(
    run_id: str,
    params: RocketParams,
    request: MonteCarloRequest,
    weather: dict,
    climatology_file: str,
):
    """Background task that runs the full MC simulation."""
    state = _active_runs[run_id]

    def on_progress(completed: int, total: int):
        state["completed"] = completed

    try:
        results = run_monte_carlo(
            params=params,
            num_simulations=request.num_simulations,
            uncertainty=request.uncertainty,
            climatology_file=climatology_file,
            weather=weather,
            progress_callback=on_progress,
        )

        mc_result = aggregate_results(results, run_id, launch_lat=params.latitude, launch_lon=params.longitude)

        # Save trajectories to disk
        traj_file = None
        if mc_result.trajectories:
            traj_file = save_trajectories(run_id, mc_result.trajectories)

        # Store results summary in DB (without full trajectory data)
        summary = mc_result.model_dump()
        summary.pop("trajectories", None)
        update_run(run_id, "completed", results_summary=summary, trajectory_file=traj_file)

        state["status"] = "completed"
        state["result"] = mc_result
        state["failed"] = sum(1 for r in results if r is None)

    except Exception as e:
        logger.error(f"MC run {run_id} failed: {e}")
        state["status"] = "failed"
        update_run(run_id, "failed")


@router.post("/monte-carlo")
async def start_monte_carlo(
    request: MonteCarloRequest,
    background_tasks: BackgroundTasks,
    user_email: str | None = None,
):
    """Start a Monte Carlo simulation run. Returns run_id for tracking."""
    run_id = str(uuid.uuid4())
    params = RocketParams()

    # Apply optional rocket parameter overrides
    if request.rocket_params:
        overrides = request.rocket_params.model_dump(exclude_none=True)
        if overrides:
            params = params.model_copy(update=overrides)

    # Resolve user_id from email
    user_id = None
    if user_email:
        user = upsert_user(user_email)
        user_id = user.id

    # Fetch weather once for all runs
    try:
        weather = fetch_weather(params.latitude, params.longitude)
    except Exception:
        weather = {
            "temperature": 15.0,
            "pressure": 1013.25,
            "wind_speed": 5.0,
            "wind_from_direction": 180.0,
            "humidity": 50.0,
        }

    climatology_file = str(INPUTS_DIR / "tarva_26_6_2024.nc")

    # Init tracking state
    _active_runs[run_id] = {
        "status": "running",
        "completed": 0,
        "total": request.num_simulations,
        "failed": 0,
        "result": None,
    }

    # Save to DB
    save_run(run_id, request.num_simulations, request.model_dump(), user_id=user_id)

    # Launch background task
    background_tasks.add_task(
        _run_mc_background, run_id, params, request, weather, climatology_file
    )

    return {"run_id": run_id, "num_simulations": request.num_simulations}


@router.get("/{run_id}/status", response_model=MonteCarloStatus)
async def get_status(run_id: str):
    """Get progress of a running MC simulation."""
    state = _active_runs.get(run_id)
    if state:
        return MonteCarloStatus(
            run_id=run_id,
            status=state["status"],
            completed=state["completed"],
            total=state["total"],
            failed=state["failed"],
        )

    # Check DB for completed runs
    row = get_run(run_id)
    if row:
        return MonteCarloStatus(
            run_id=run_id,
            status=row.status,
            completed=row.num_simulations if row.status == "completed" else 0,
            total=row.num_simulations,
        )

    return MonteCarloStatus(
        run_id=run_id, status="not_found", completed=0, total=0
    )


@router.get("/{run_id}/results", response_model=MonteCarloResult)
async def get_results(run_id: str):
    """Get full MC results."""
    state = _active_runs.get(run_id)
    if state and state["result"]:
        return state["result"]

    # Load from DB
    row = get_run(run_id)
    if row and row.results_summary:
        summary = json.loads(row.results_summary)
        # Re-attach trajectories from file if available
        if row.trajectory_file:
            from storage.file_store import load_trajectories
            summary["trajectories"] = load_trajectories(run_id)
        else:
            summary["trajectories"] = []
        return MonteCarloResult(**summary)

    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Results not found")


@router.get("/runs/list")
async def list_simulation_runs(limit: int = 50, user_email: str | None = None):
    """List past simulation runs, optionally filtered by user email."""
    user_id = None
    if user_email:
        user = get_user_by_email(user_email)
        if user:
            user_id = user.id
    return list_runs(user_id=user_id, limit=limit)


@router.websocket("/ws/{run_id}")
async def websocket_progress(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for real-time MC progress updates."""
    await websocket.accept()
    try:
        while True:
            state = _active_runs.get(run_id)
            if state:
                await websocket.send_json({
                    "status": state["status"],
                    "completed": state["completed"],
                    "total": state["total"],
                    "failed": state["failed"],
                })
                if state["status"] in ("completed", "failed"):
                    break
            else:
                row = get_run(run_id)
                status = row.status if row else "not_found"
                await websocket.send_json({
                    "status": status,
                    "completed": 0,
                    "total": 0,
                })
                if status != "running":
                    break

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()


@router.post("/single")
async def run_single(use_reanalysis: bool = True):
    """Run a single simulation with default params (for verification)."""
    params = RocketParams()
    result = run_single_simulation(params, use_reanalysis=use_reanalysis)
    return result
