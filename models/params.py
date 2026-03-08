import numpy as np
from pydantic import BaseModel, Field


class RocketParams(BaseModel):
    """All nominal rocket parameters, ported from rocketpy-2026/inputs/params.py."""

    # General
    rocket_length: float = 5.085  # m
    rocket_radius: float = 0.1225  # m
    center_gravity: float = 2.98  # m from top
    dry_total_mass: float = 93.8  # kg

    # Inertia
    inertia_xx: float = 0.711
    inertia_yy: float = 1631.815
    inertia_zz: float = 1631.786
    inertia_xy: float = -0.059
    inertia_xz: float = -0.117
    inertia_yz: float = -0.01

    # Nosecone
    nose_length: float = 0.8  # m

    # Fins
    fin_beta: float = 63.0  # degrees
    fin_span: float = 0.18  # m
    rootchord: float = 0.28  # m
    tipchord: float = 0.14  # m
    amount: int = 4
    fin_position: float = 4.797  # m
    cant_angle: float = 0.0  # degrees

    # Rail buttons (distance from bottom)
    button_1: float = 1.915  # m
    button_2: float = 0.3  # m

    # Tanks - ambient
    ambient_temp: float = 20.0  # C

    # Oxidizer tank
    ox_length: float = 1.079  # m
    ox_inner_radius: float = 0.0645  # m
    ox_outer_radius: float = 0.115  # m
    ox_pressure: float = 30.0  # bar
    ox_volume: float = 27.0  # liters
    ox_temp: float = -20.0  # C
    ox_position: float = 1.415  # m from bottom
    ox_density: float = 998.0  # kg/m3

    # Fuel tank
    fuel_length: float = 1.171  # m
    fuel_eff_radius: float = 0.06  # m
    fuel_pressure: float = 35.0  # bar
    fuel_volume: float = 11.7  # liters (13 * 0.9)
    fuel_temp: float = 20.0  # C (= ambient_temp)
    fuel_position: float = 1.415  # m from bottom
    fuel_density: float = 818.0  # kg/m3

    # Fuel composition (90% ethanol / 10% water by mass)
    ethanol_perc: float = 90.0
    water_perc: float = 10.0

    # N2 tank
    n2_length: float = 0.55  # m
    n2_radius: float = 0.104  # m
    n2_volume: float = 12.0  # liters
    n2_position: float = 2.94  # m from bottom
    n2_pressure: float = 280.0  # bar
    n2_mass: float = 3.6  # kg

    # Burn
    massflowrate: float = 4.3  # kg/s
    OF_ratio: float = 3.0

    # Drogue chute
    drogue_cd: float = 1.5
    drogue_area: float = 1.4775  # m2
    drogue_total_lag: float = 0.5  # s
    drogue_sampling_rate: float = 105.0  # Hz

    # Main chute
    main_cd: float = 2.2
    main_area: float = 13.858  # m2
    main_cds: float = 30.4876
    main_total_lag: float = 5.0  # s
    main_trigger: float = 600.0  # m altitude
    main_sampling_rate: float = 105.0  # Hz

    # Launch site
    latitude: float = 63.786667
    longitude: float = 9.363056
    max_expected_height: float = 12000.0  # m
    elevation: float = 20.0  # m ASL

    # Rail
    rail_length: float = 12.0  # m
    inclination: float = 82.0  # degrees
    heading: float = 225.0  # degrees

    # Files
    thrust_curve_file: str = "inputs/Estimated_thrust_curve_24.2.2026.csv"
    atmosphere_file: str = "inputs/tarva_26_6_2024.nc"
    drag_off_file: str = "inputs/drag.offH.csv"
    drag_on_file: str = "inputs/drag.on.csv"

    @property
    def ox_eff_radius(self) -> float:
        return float(np.sqrt(self.ox_inner_radius**2 + self.ox_outer_radius**2))

    @property
    def drogue_cds(self) -> float:
        return self.drogue_cd * self.drogue_area

    @property
    def ox_mass(self) -> float:
        return self.ox_density * self.ox_volume * 0.001

    @property
    def fuel_mass(self) -> float:
        return self.fuel_density * self.fuel_volume * 0.001
