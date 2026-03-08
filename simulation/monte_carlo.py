"""ProcessPoolExecutor-based Monte Carlo orchestration."""

import os
import logging
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable

from models.params import RocketParams
from models.api_models import SimResult, UncertaintyConfig
from simulation.parameter_sampler import SimulationInput, generate_samples
from simulation.single_run import run_single_simulation
from simulation.rocket_factory import compute_n2_densities
from config import MAX_WORKERS, TRAJECTORY_STORE_LIMIT

logger = logging.getLogger(__name__)


def _run_one(args: tuple) -> SimResult | None:
    """Wrapper for ProcessPoolExecutor - unpacks args and runs simulation."""
    params_dict, sample_dict, climatology_file, weather, n2_densities = args
    try:
        params = RocketParams(**params_dict)
        return run_single_simulation(
            params=params,
            climatology_file=climatology_file,
            weather=weather,
            store_trajectory=sample_dict["store_trajectory"],
            wind_speed_delta=sample_dict["wind_speed_delta"],
            wind_direction_delta=sample_dict["wind_direction_delta"],
            temperature_delta=sample_dict["temperature_delta"],
            pressure_delta=sample_dict["pressure_delta"],
            dry_mass_delta=sample_dict["dry_mass_delta"],
            thrust_scale_factor=sample_dict["thrust_scale_factor"],
            drogue_cds_scale=sample_dict["drogue_cds_scale"],
            main_cds_scale=sample_dict["main_cds_scale"],
            inclination_delta=sample_dict["inclination_delta"],
            heading_delta=sample_dict["heading_delta"],
            n2_densities=n2_densities,
        )
    except Exception as e:
        logger.error(f"Simulation failed: {e}\n{traceback.format_exc()}")
        return None


def run_monte_carlo(
    params: RocketParams,
    num_simulations: int,
    uncertainty: UncertaintyConfig,
    climatology_file: str,
    weather: dict | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
    seed: int | None = None,
) -> list[SimResult | None]:
    """Run N simulations in parallel using ProcessPoolExecutor.

    Args:
        progress_callback: Called with (completed, total) after each simulation.
    """
    # Pre-compute N2 densities in main process (pyfluids not subprocess-safe)
    try:
        n2_densities = compute_n2_densities(
            params.n2_pressure, params.ambient_temp, params.fuel_temp
        )
    except Exception as e:
        logger.warning(f"pyfluids N2 density computation failed ({e}), using fallback")
        n2_densities = (295.0, 295.0)

    samples = generate_samples(
        num_simulations, uncertainty,
        trajectory_limit=TRAJECTORY_STORE_LIMIT,
        seed=seed,
    )

    # Serialize params to dict for pickling across processes
    params_dict = params.model_dump()

    # Prepare args for each worker
    args_list = [
        (
            params_dict,
            {
                "store_trajectory": s.store_trajectory,
                "wind_speed_delta": s.wind_speed_delta,
                "wind_direction_delta": s.wind_direction_delta,
                "temperature_delta": s.temperature_delta,
                "pressure_delta": s.pressure_delta,
                "dry_mass_delta": s.dry_mass_delta,
                "thrust_scale_factor": s.thrust_scale_factor,
                "drogue_cds_scale": s.drogue_cds_scale,
                "main_cds_scale": s.main_cds_scale,
                "inclination_delta": s.inclination_delta,
                "heading_delta": s.heading_delta,
            },
            climatology_file,
            weather,
            n2_densities,
        )
        for s in samples
    ]

    max_workers = min(os.cpu_count() or 4, MAX_WORKERS)
    results: list[SimResult | None] = [None] * num_simulations
    completed = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(_run_one, args): i
            for i, args in enumerate(args_list)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.error(f"Simulation {idx} raised: {e}\n{traceback.format_exc()}")
                results[idx] = None

            completed += 1
            if progress_callback:
                progress_callback(completed, num_simulations)

    return results
