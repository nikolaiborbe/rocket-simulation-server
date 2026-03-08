"""Sample MC perturbation parameters from uncertainty distributions."""

import numpy as np
from dataclasses import dataclass
from models.api_models import UncertaintyConfig


@dataclass
class SimulationInput:
    """One set of perturbed parameters for a single MC run."""
    index: int
    wind_speed_delta: float
    wind_direction_delta: float
    temperature_delta: float
    pressure_delta: float
    dry_mass_delta: float
    thrust_scale_factor: float
    drogue_cds_scale: float
    main_cds_scale: float
    inclination_delta: float
    heading_delta: float
    store_trajectory: bool


def generate_samples(
    n: int,
    uncertainty: UncertaintyConfig,
    trajectory_limit: int = 50,
    seed: int | None = None,
) -> list[SimulationInput]:
    """Generate N sets of perturbed simulation inputs."""
    rng = np.random.default_rng(seed)

    samples = []
    for i in range(n):
        samples.append(SimulationInput(
            index=i,
            wind_speed_delta=float(rng.normal(0, uncertainty.wind_speed_sigma)),
            wind_direction_delta=float(rng.normal(0, uncertainty.wind_direction_sigma)),
            temperature_delta=float(rng.normal(0, uncertainty.temperature_sigma)),
            pressure_delta=float(rng.normal(0, uncertainty.pressure_sigma)),
            dry_mass_delta=float(rng.normal(0, uncertainty.dry_mass_sigma)),
            thrust_scale_factor=float(rng.normal(1.0, uncertainty.thrust_scale_sigma)),
            drogue_cds_scale=float(rng.normal(1.0, uncertainty.drogue_cds_scale_sigma)),
            main_cds_scale=float(rng.normal(1.0, uncertainty.main_cds_scale_sigma)),
            inclination_delta=float(rng.normal(0, uncertainty.inclination_sigma)),
            heading_delta=float(rng.normal(0, uncertainty.heading_sigma)),
            store_trajectory=(i < trajectory_limit),
        ))

    return samples
