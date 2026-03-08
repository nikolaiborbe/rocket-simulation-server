from pydantic import BaseModel, Field
from typing import Optional


class UncertaintyConfig(BaseModel):
    wind_speed_sigma: float = 2.0  # m/s
    wind_direction_sigma: float = 15.0  # degrees
    temperature_sigma: float = 2.0  # K
    pressure_sigma: float = 500.0  # Pa
    dry_mass_sigma: float = 1.0  # kg
    thrust_scale_sigma: float = 0.03  # 3%
    drogue_cds_scale_sigma: float = 0.10  # 10%
    main_cds_scale_sigma: float = 0.10  # 10%
    inclination_sigma: float = 1.0  # degrees
    heading_sigma: float = 2.0  # degrees


class RocketConfigOverride(BaseModel):
    """Optional overrides for rocket parameters (only include fields to change)."""
    # General
    dry_total_mass: Optional[float] = None
    rocket_radius: Optional[float] = None
    rocket_length: Optional[float] = None
    center_gravity: Optional[float] = None
    nose_length: Optional[float] = None
    # Fins
    fin_span: Optional[float] = None
    rootchord: Optional[float] = None
    tipchord: Optional[float] = None
    cant_angle: Optional[float] = None
    # Propellant
    ox_volume: Optional[float] = None
    ox_density: Optional[float] = None
    fuel_volume: Optional[float] = None
    fuel_density: Optional[float] = None
    OF_ratio: Optional[float] = None
    massflowrate: Optional[float] = None
    # Recovery
    drogue_cd: Optional[float] = None
    drogue_area: Optional[float] = None
    main_cd: Optional[float] = None
    main_area: Optional[float] = None
    main_trigger: Optional[float] = None
    # Launch
    rail_length: Optional[float] = None
    inclination: Optional[float] = None
    heading: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None


class MonteCarloRequest(BaseModel):
    num_simulations: int = Field(default=500, ge=10, le=5000)
    uncertainty: UncertaintyConfig = Field(default_factory=UncertaintyConfig)
    rocket_params: Optional[RocketConfigOverride] = None


class SimResult(BaseModel):
    impact_x: float
    impact_y: float
    apogee_altitude: float
    apogee_x: float
    apogee_y: float
    max_velocity: float
    apogee_time: float
    impact_time: float
    impact_velocity: float
    trajectory: Optional[list[list[float]]] = None  # [[x,y,z], ...] at 1Hz


class EllipseData(BaseModel):
    center_x: float
    center_y: float
    semi_major: float
    semi_minor: float
    angle_deg: float  # rotation angle of ellipse


class MonteCarloStatus(BaseModel):
    run_id: str
    status: str  # "running", "completed", "failed"
    completed: int
    total: int
    failed: int = 0


class MonteCarloResult(BaseModel):
    run_id: str
    num_simulations: int
    num_successful: int

    # Landing statistics
    mean_impact_x: float
    mean_impact_y: float
    std_impact_x: float
    std_impact_y: float
    landing_points: list[list[float]]  # [[x,y], ...]

    # Confidence ellipses (1σ, 2σ, 3σ)
    ellipses: list[EllipseData]

    # Apogee statistics
    mean_apogee: float
    std_apogee: float
    mean_max_velocity: float
    std_max_velocity: float
    mean_impact_velocity: float
    std_impact_velocity: float

    # Trajectory subset
    trajectories: list[list[list[float]]]  # [[[x,y,z], ...], ...]

    # Launch site for coordinate conversion
    launch_lat: float
    launch_lon: float

    # Weather used for simulation
    weather_temperature: Optional[float] = None
    weather_pressure: Optional[float] = None
    weather_wind_speed: Optional[float] = None
    weather_wind_direction: Optional[float] = None
    weather_humidity: Optional[float] = None
