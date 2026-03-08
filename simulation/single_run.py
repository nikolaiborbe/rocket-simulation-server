"""Run a single RocketPy flight simulation.

This must be a top-level function so it's picklable for ProcessPoolExecutor.
"""

import gc
import io
import contextlib
import matplotlib
matplotlib.use("Agg")

import numpy as np
from rocketpy import Flight

from models.params import RocketParams
from models.api_models import SimResult
from simulation.rocket_factory import build_rocket
from simulation.environment_factory import build_environment, build_environment_from_file
from config import INPUTS_DIR


def run_single_simulation(
    params: RocketParams,
    climatology_file: str | None = None,
    weather: dict | None = None,
    store_trajectory: bool = False,
    # MC perturbation parameters
    wind_speed_delta: float = 0.0,
    wind_direction_delta: float = 0.0,
    temperature_delta: float = 0.0,
    pressure_delta: float = 0.0,
    dry_mass_delta: float = 0.0,
    thrust_scale_factor: float = 1.0,
    drogue_cds_scale: float = 1.0,
    main_cds_scale: float = 1.0,
    inclination_delta: float = 0.0,
    heading_delta: float = 0.0,
    use_reanalysis: bool = False,
    n2_densities: tuple[float, float] | None = None,
) -> SimResult:
    """Run one flight simulation and return results.

    Top-level function for pickling compatibility with ProcessPoolExecutor.
    """
    # Suppress stdout from RocketPy
    with contextlib.redirect_stdout(io.StringIO()):
        # Build rocket with MC perturbations
        rocket = build_rocket(
            params,
            thrust_scale_factor=thrust_scale_factor,
            drogue_cds_scale=drogue_cds_scale,
            main_cds_scale=main_cds_scale,
            dry_mass_delta=dry_mass_delta,
            n2_densities=n2_densities,
        )

        # Build environment
        if use_reanalysis:
            atmo_file = str(INPUTS_DIR / "tarva_26_6_2024.nc")
            env = build_environment_from_file(
                atmo_file,
                lat=params.latitude,
                lon=params.longitude,
                elevation=params.elevation,
            )
        else:
            clim_file = climatology_file or str(INPUTS_DIR / "tarva_26_6_2024.nc")
            env = build_environment(
                clim_file,
                lat=params.latitude,
                lon=params.longitude,
                elevation=params.elevation,
                weather=weather,
                wind_speed_delta=wind_speed_delta,
                wind_direction_delta=wind_direction_delta,
                temperature_delta=temperature_delta,
                pressure_delta=pressure_delta,
            )

        # Run flight
        flight = Flight(
            rocket=rocket,
            environment=env,
            rail_length=params.rail_length,
            inclination=params.inclination + inclination_delta,
            heading=params.heading + heading_delta,
            max_time_step=0.1,
            max_time=1500,
        )

    # Extract results
    trajectory = None
    if store_trajectory:
        t_arr = np.arange(0, flight.t_final, 1.0, dtype=np.float32)
        coords = np.column_stack([
            flight.x(t_arr),
            flight.y(t_arr),
            flight.z(t_arr),
        ]).astype(np.float32)
        trajectory = coords.tolist()
        del t_arr, coords

    result = SimResult(
        impact_x=float(flight.x_impact),
        impact_y=float(flight.y_impact),
        apogee_altitude=float(flight.apogee - params.elevation),
        apogee_x=float(flight.apogee_x),
        apogee_y=float(flight.apogee_y),
        max_velocity=float(flight.max_speed),
        apogee_time=float(flight.apogee_time),
        impact_time=float(flight.t_final),
        impact_velocity=float(flight.impact_velocity),
        trajectory=trajectory,
    )

    # Cleanup
    del flight, rocket, env
    gc.collect()

    return result
