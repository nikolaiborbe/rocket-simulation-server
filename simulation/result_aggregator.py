"""Aggregate Monte Carlo results into statistics and confidence ellipses."""

import numpy as np
from models.api_models import SimResult, MonteCarloResult, EllipseData

# Chi-squared values for 2D confidence ellipses
CHI2_1SIGMA = 2.2789  # ~39.3% for 2D
CHI2_2SIGMA = 6.1801  # ~86.5% for 2D
CHI2_3SIGMA = 11.8290  # ~98.9% for 2D


def _compute_ellipse(
    mean: np.ndarray,
    cov: np.ndarray,
    chi2_val: float,
) -> EllipseData:
    """Compute confidence ellipse from mean and covariance matrix."""
    eigenvalues, eigenvectors = np.linalg.eigh(cov)

    # Sort by largest eigenvalue
    order = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    # Semi-axes scaled by chi-squared value
    semi_major = float(np.sqrt(chi2_val * eigenvalues[0]))
    semi_minor = float(np.sqrt(chi2_val * eigenvalues[1]))

    # Angle of major axis
    angle = float(np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0])))

    return EllipseData(
        center_x=float(mean[0]),
        center_y=float(mean[1]),
        semi_major=semi_major,
        semi_minor=semi_minor,
        angle_deg=angle,
    )


def aggregate_results(
    results: list[SimResult | None],
    run_id: str,
    launch_lat: float = 63.786667,
    launch_lon: float = 9.363056,
    weather: dict | None = None,
) -> MonteCarloResult:
    """Compute statistics and ellipses from MC simulation results."""
    successful = [r for r in results if r is not None]

    if not successful:
        raise ValueError("No successful simulations to aggregate")

    # Landing points
    landing_points = np.array([[r.impact_x, r.impact_y] for r in successful])
    mean_landing = landing_points.mean(axis=0)
    cov_landing = np.cov(landing_points.T)

    # Handle degenerate case (single point)
    if cov_landing.ndim == 0:
        cov_landing = np.array([[float(cov_landing), 0], [0, float(cov_landing)]])

    # Confidence ellipses
    ellipses = [
        _compute_ellipse(mean_landing, cov_landing, CHI2_1SIGMA),
        _compute_ellipse(mean_landing, cov_landing, CHI2_2SIGMA),
        _compute_ellipse(mean_landing, cov_landing, CHI2_3SIGMA),
    ]

    # Apogee stats
    apogees = np.array([r.apogee_altitude for r in successful])
    max_velocities = np.array([r.max_velocity for r in successful])
    impact_velocities = np.array([r.impact_velocity for r in successful])

    # Collect trajectories from runs that stored them
    trajectories = [r.trajectory for r in successful if r.trajectory is not None]

    return MonteCarloResult(
        run_id=run_id,
        num_simulations=len(results),
        num_successful=len(successful),
        mean_impact_x=float(mean_landing[0]),
        mean_impact_y=float(mean_landing[1]),
        std_impact_x=float(np.std(landing_points[:, 0])),
        std_impact_y=float(np.std(landing_points[:, 1])),
        landing_points=landing_points.tolist(),
        ellipses=ellipses,
        mean_apogee=float(apogees.mean()),
        std_apogee=float(apogees.std()),
        mean_max_velocity=float(max_velocities.mean()),
        std_max_velocity=float(max_velocities.std()),
        mean_impact_velocity=float(impact_velocities.mean()),
        std_impact_velocity=float(impact_velocities.std()),
        trajectories=trajectories,
        launch_lat=launch_lat,
        launch_lon=launch_lon,
        weather_temperature=weather.get("temperature") if weather else None,
        weather_pressure=weather.get("pressure") if weather else None,
        weather_wind_speed=weather.get("wind_speed") if weather else None,
        weather_wind_direction=weather.get("wind_from_direction") if weather else None,
        weather_humidity=weather.get("humidity") if weather else None,
    )
