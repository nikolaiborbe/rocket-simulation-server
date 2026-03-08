"""Build a RocketPy Rocket from RocketParams.

Ported from rocketpy-2026/ROCKETPY_P26.py lines 256-534.
Key differences from launch-server/sim.py:
  - Fuel: 90% ethanol / 10% water (not 75/25)
  - Ox density: 998 kg/m3
  - Main chute trigger: 600m (not 500m)
  - Main chute Cd_s: main_cds + drogue_cds combined
  - Flow rates as lambdas (not numpy arrays)
"""

import numpy as np
import pandas as pd
from pathlib import Path

from rocketpy import (
    LiquidMotor,
    MassFlowRateBasedTank,
    Rocket,
    CylindricalTank,
    Fluid,
)

from models.params import RocketParams
from config import INPUTS_DIR


def _resolve_path(relative_path: str) -> str:
    """Resolve a path relative to server/ directory. Returns absolute path."""
    p = Path(relative_path)
    if p.is_absolute() and p.exists():
        return str(p)
    # Try relative to server/ directory
    server_dir = Path(__file__).resolve().parent.parent
    candidate = server_dir / p
    if candidate.exists():
        return str(candidate.resolve())
    # Try relative to CWD
    if p.exists():
        return str(p.resolve())
    raise FileNotFoundError(f"Cannot find file: {relative_path}")


def compute_n2_densities(
    n2_pressure_bar: float = 280.0,
    ambient_temp_c: float = 20.0,
    fuel_temp_c: float = 20.0,
) -> tuple[float, float]:
    """Compute N2 gas densities using pyfluids. Call once in main process.

    Returns (n2i_density, n2f_density).
    """
    from pyfluids import FluidsList, Input
    from pyfluids import Fluid as PyFluid

    n2i = PyFluid(FluidsList.Nitrogen).with_state(
        Input.pressure(n2_pressure_bar * 1e5),
        Input.temperature(ambient_temp_c),
    )
    n2f = PyFluid(FluidsList.Nitrogen).with_state(
        Input.pressure(n2_pressure_bar * 1e5),
        Input.temperature(fuel_temp_c),
    )
    return (n2i.density, n2f.density)


# Pre-compute at import time (main process only, before any forks)
_N2_DENSITIES: tuple[float, float] | None = None


def _get_n2_densities(params: RocketParams) -> tuple[float, float]:
    """Get cached N2 densities, computing once on first call."""
    global _N2_DENSITIES
    if _N2_DENSITIES is None:
        try:
            _N2_DENSITIES = compute_n2_densities(
                params.n2_pressure, params.ambient_temp, params.fuel_temp
            )
        except Exception:
            # Fallback: N2 at 280 bar, 20°C ≈ 295 kg/m³
            _N2_DENSITIES = (295.0, 295.0)
    return _N2_DENSITIES


def build_rocket(
    params: RocketParams,
    thrust_scale_factor: float = 1.0,
    drogue_cds_scale: float = 1.0,
    main_cds_scale: float = 1.0,
    dry_mass_delta: float = 0.0,
    n2_densities: tuple[float, float] | None = None,
) -> Rocket:
    """Build a fully configured Rocket with LiquidMotor and parachutes.

    Args:
        n2_densities: Pre-computed (n2i_density, n2f_density) tuple.
            If None, uses cached values (avoids pyfluids in subprocesses).
    """
    # Get N2 gas densities (pre-computed, no pyfluids call needed here)
    if n2_densities is not None:
        n2i_density, n2f_density = n2_densities
    else:
        n2i_density, n2f_density = _get_n2_densities(params)

    # --- Tank geometries ---
    fuel_tank_geometry = CylindricalTank(
        params.fuel_eff_radius, params.fuel_length, spherical_caps=False
    )
    ox_tank_geometry = CylindricalTank(
        params.ox_eff_radius, params.ox_length, spherical_caps=False
    )
    n2_tank_geometry = CylindricalTank(
        params.n2_radius, params.n2_length, spherical_caps=True
    )

    # --- RocketPy Fluids (densities from params, not pyfluids) ---
    N2O = Fluid(name="N2O", density=params.ox_density)
    fuel = Fluid(name="liq_eth90", density=params.fuel_density)
    gas_N2i = Fluid(name="gas_N2_initial", density=n2i_density)
    gas_N2f = Fluid(name="gas_N2_final", density=n2f_density)

    # --- Mass flow calculations ---
    ox_mass = params.ox_mass
    prop_mass = params.fuel_mass
    n2_mass = params.n2_mass

    of = params.OF_ratio
    ox_perc = params.ox_volume / (params.ox_volume + params.fuel_volume)
    prop_perc = params.fuel_volume / (params.ox_volume + params.fuel_volume)

    mdot = params.massflowrate
    ox_mdot = mdot * (of / (of + 1))
    prop_mdot = mdot / (of + 1)

    burnout_time = min(prop_mass / prop_mdot, ox_mass / ox_mdot)
    n2_mdot = n2_mass / burnout_time

    # --- Tanks with lambda flow rates ---
    # NOTE: lambdas must have exactly 1 parameter (t) - RocketPy inspects
    # the signature to determine input dimensions. Use closures, not defaults.
    ox_gas_in_rate = ox_perc * n2_mdot / 2

    N2O_tank = MassFlowRateBasedTank(
        name="oxidizer tank",
        geometry=ox_tank_geometry,
        liquid=N2O,
        gas=gas_N2f,
        flux_time=burnout_time,
        initial_liquid_mass=ox_mass,
        initial_gas_mass=0,
        liquid_mass_flow_rate_in=0,
        liquid_mass_flow_rate_out=lambda t: ox_mdot if t < burnout_time else 0,
        gas_mass_flow_rate_in=lambda t: ox_gas_in_rate if t < burnout_time else 0,
        gas_mass_flow_rate_out=0,
    )

    fuel_gas_in_rate = prop_perc * n2_mdot / 2

    fuel_tank = MassFlowRateBasedTank(
        name="fuel tank",
        geometry=fuel_tank_geometry,
        liquid=fuel,
        gas=gas_N2f,
        flux_time=burnout_time,
        initial_liquid_mass=prop_mass,
        initial_gas_mass=0,
        liquid_mass_flow_rate_in=0,
        liquid_mass_flow_rate_out=lambda t: prop_mdot if t < burnout_time else 0,
        gas_mass_flow_rate_in=lambda t: fuel_gas_in_rate if t < burnout_time else 0,
        gas_mass_flow_rate_out=0,
    )

    n2_tank = MassFlowRateBasedTank(
        name="N2 tank",
        geometry=n2_tank_geometry,
        liquid=gas_N2i,
        gas=gas_N2i,
        flux_time=burnout_time,
        initial_liquid_mass=0,
        initial_gas_mass=n2_mass,
        liquid_mass_flow_rate_in=0,
        liquid_mass_flow_rate_out=0,
        gas_mass_flow_rate_in=0,
        gas_mass_flow_rate_out=lambda t: n2_mdot if t < burnout_time else 0,
    )

    # --- Thrust curve ---
    thrust_curve_path = _resolve_path(params.thrust_curve_file)
    thrust_df = pd.read_csv(thrust_curve_path)

    # Apply thrust scale factor for MC
    if thrust_scale_factor != 1.0:
        thrust_data = thrust_df.values.copy()
        thrust_data[:, 1] *= thrust_scale_factor
        thrust_source = thrust_data
    else:
        thrust_source = thrust_curve_path

    # --- Motor ---
    liquid_motor = LiquidMotor(
        thrust_source=thrust_source,
        center_of_dry_mass_position=0,
        dry_inertia=(0, 0, 0),
        dry_mass=0.1,
        burn_time=(0, burnout_time),
        nozzle_radius=0.068,
        nozzle_position=0,
        coordinate_system_orientation="nozzle_to_combustion_chamber",
    )

    liquid_motor.add_tank(fuel_tank, position=params.fuel_position)
    liquid_motor.add_tank(N2O_tank, position=params.ox_position)
    liquid_motor.add_tank(n2_tank, position=params.n2_position)

    # --- Rocket ---
    drymass = params.dry_total_mass + dry_mass_delta

    heimdal = Rocket(
        radius=params.rocket_radius,
        mass=drymass,
        inertia=(
            params.inertia_xx, params.inertia_yy, params.inertia_zz,
            params.inertia_xz, params.inertia_xy, params.inertia_yz,
        ),
        power_off_drag=_resolve_path(params.drag_off_file),
        power_on_drag=_resolve_path(params.drag_on_file),
        center_of_mass_without_motor=params.center_gravity,
        coordinate_system_orientation="nose_to_tail",
    )

    heimdal.add_nose(length=params.nose_length, kind="von karman", position=0)

    sweep_length = params.fin_span / np.tan(np.deg2rad(params.fin_beta))
    heimdal.add_trapezoidal_fins(
        n=params.amount,
        root_chord=params.rootchord,
        tip_chord=params.tipchord,
        span=params.fin_span,
        position=params.fin_position,
        cant_angle=params.cant_angle,
        sweep_length=sweep_length,
    )

    nozzle_pos = params.rocket_length
    heimdal.add_motor(liquid_motor, position=nozzle_pos)

    heimdal.set_rail_buttons(
        upper_button_position=params.rocket_length - params.button_1,
        lower_button_position=params.rocket_length - params.button_2,
    )

    # --- Parachutes ---
    drogue_Cd_s = params.drogue_cds * drogue_cds_scale
    main_Cd_s = params.main_cds * main_cds_scale
    main_trigger_alt = params.main_trigger

    # NOTE: trigger functions must have exactly 3 params (p, h, y).
    # RocketPy 1.11 inspects the signature: 3 params → wraps to add sensors arg,
    # 4 params → assumes (p, h, y, sensors) and passes sensors directly.
    # Using a default arg like (p, h, y, _alt=600) gives 4 params, so RocketPy
    # passes sensors as _alt, breaking the comparison. Use closures instead.
    def drogue_trigger(p, h, y):
        return y[5] < 0

    def main_trigger_fn(p, h, y):
        return y[5] < 0 and h <= main_trigger_alt

    heimdal.add_parachute(
        "Drogue",
        cd_s=drogue_Cd_s,
        trigger=drogue_trigger,
        sampling_rate=params.drogue_sampling_rate,
        lag=params.drogue_total_lag,
    )

    # Main Cd_s = main_cds + drogue_cds (combined, as in ROCKETPY_P26.py line 504)
    heimdal.add_parachute(
        "Main",
        cd_s=main_Cd_s + drogue_Cd_s,
        trigger=main_trigger_fn,
        sampling_rate=params.main_sampling_rate,
        lag=params.main_total_lag,
    )

    return heimdal
