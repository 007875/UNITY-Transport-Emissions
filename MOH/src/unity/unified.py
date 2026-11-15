"""Unified estimator: chooses the method from the data that are actually available."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from . import params as P
from .scenario import TransportScenario, Trip
from .trajectory import summarize
from . import models as M
from .uncertainty import summarize as stats

BOUNDARY_NOTE = ("CO2e, reported as TTW (tank-to-wheel) and WTW (well-to-wheel = TTW + WTT). "
                 "Fuel-chain and non-CO2 factors are placeholder assumptions (see params.py).")


@dataclass
class UnifiedResult:
    scenario_name: str
    mode: str
    level: str
    method: str
    point_ttw_kg: float
    point_wtw_kg: float
    ttw: dict
    wtw: dict
    payload_t: float
    warnings: list = field(default_factory=list)
    boundary: str = BOUNDARY_NOTE
    kg_per_t_ttw: np.ndarray = field(default=None, repr=False)
    kg_per_t_wtw: np.ndarray = field(default=None, repr=False)

    def summary_row(self) -> dict:
        return dict(scenario=self.scenario_name, level=self.level,
                    wtw_point_kg=self.point_wtw_kg, wtw_p5=self.wtw["p5"],
                    wtw_p50=self.wtw["p50"], wtw_p95=self.wtw["p95"],
                    wtw_rel_half_width=self.wtw["rel_half_width"],
                    ttw_point_kg=self.point_ttw_kg, method=self.method)


# ---------------------------------------------------------------- levels ---
def select_level(scn: TransportScenario):
    """Pick the most detailed method supported by the data. Returns (level, warnings)."""
    scn.validate()
    warns = []
    if scn.mode == "rail":
        return "low", ["rail: only the factor-based (low-data) method exists in v2"]
    t = scn.trip
    if scn.vehicle.load_factor is None:
        warns.append("load factor unknown: default triangular distribution (0.3/0.6/0.9) used")
    if t.speed_trace_kmh is not None:
        return "high", warns
    if t.average_speed_kmh is not None and t.road_type is not None:
        return "medium", warns
    if t.average_speed_kmh is not None or t.road_type is not None:
        warns.append("average speed AND road type are both needed for the medium level; using low")
    return "low", warns


def with_information(scn: TransportScenario, level: str) -> TransportScenario:
    """Same trip, but only the information available at ``level`` (an 'information ladder')."""
    t = scn.trip
    avg = t.average_speed_kmh
    if avg is None and t.speed_trace_kmh is not None:
        avg = summarize(t.speed_trace_kmh).average_speed_kmh
    if level == "high":
        return scn
    if level == "medium":
        return scn.copy(trip=Trip(t.distance_km, avg, t.road_type or "motorway", None))
    if level == "low":
        return scn.copy(trip=Trip(t.distance_km))
    raise ValueError(f"unknown level {level!r}")


def _check_inputs(scn, level):
    t = scn.trip
    if level == "medium" and (t.average_speed_kmh is None or t.road_type is None):
        raise ValueError("medium level needs average_speed_kmh and road_type")
    if level == "high" and t.speed_trace_kmh is None:
        raise ValueError("high level needs a speed trace (1 Hz, km/h)")


METHOD_TEXT = {
    "low": "consumption(L/km) linear in payload x distance, class-level defaults",
    "medium": "low-data consumption x speed/road-type curve",
    "high": "road-load physics model on a 1 Hz speed trajectory",
}


# -------------------------------------------------------------- estimator ---
def estimate(scn: TransportScenario, level: str = "auto", n: int = 3000, seed: int = 42,
             high_backend: str = "physics") -> UnifiedResult:
    """Point estimate + Monte-Carlo uncertainty for a scenario.

    level="auto" selects the method from the available data; otherwise the level is forced
    (and its required inputs are checked).
    """
    auto_level, warns = select_level(scn)
    if level == "auto":
        level = auto_level
    elif scn.mode == "rail" and level != "low":
        raise ValueError("rail supports only level='low'")
    else:
        _check_inputs(scn, level)
    rng = np.random.default_rng(seed)

    if scn.mode == "rail":
        n_ttw, n_wtw = M.rail_per_tkm(scn, 1, None)
        s_ttw, s_wtw = M.rail_per_tkm(scn, n, rng)
        tonnes, km = scn.shipment_tonnes, scn.trip.distance_km
        return UnifiedResult(
            scn.name, "rail", "low", "factor-based intensity (kg CO2e per t-km) x t x km",
            float(n_ttw[0] * tonnes * km), float(n_wtw[0] * tonnes * km),
            stats(s_ttw * tonnes * km), stats(s_wtw * tonnes * km), float(tonnes), warns,
            kg_per_t_ttw=s_ttw * km, kg_per_t_wtw=s_wtw * km)

    fuel_fn = M.FUEL_FUNCS[level]
    dn, dr = M.nominal_draws(scn), M.random_draws(scn, n, rng)
    fuel_n, fuel_r = fuel_fn(scn, dn), fuel_fn(scn, dr)
    ttw_n, wtw_n = M.co2e_from_fuel(fuel_n, dn)
    ttw_r, wtw_r = M.co2e_from_fuel(fuel_r, dr)
    method = METHOD_TEXT[level]

    if level == "high" and high_backend == "sumo":
        from . import sumo_backend as SB
        res = SB.run_hbefa4(scn.trip.speed_trace_kmh, scn.vehicle.vehicle_class)
        km_scale = scn.trip.distance_km / res["trace_distance_km"]
        sumo_ttw = res["co2_kg"] * km_scale
        sumo_fuel_l = res["fuel_kg"] * km_scale / 0.832            # approx. diesel density kg/L
        ratio = ttw_r / ttw_n[0]
        point_ttw = sumo_ttw
        point_wtw = sumo_ttw + sumo_fuel_l * P.DIESEL_WTT_KG_CO2E_PER_L
        ttw_r, wtw_r = sumo_ttw * ratio, (sumo_ttw + sumo_fuel_l * P.DIESEL_WTT_KG_CO2E_PER_L) * (wtw_r / wtw_n[0])
        ttw_n, wtw_n = np.array([point_ttw]), np.array([point_wtw])
        method = "HBEFA4 via SUMO (interval width borrowed from the physics-model parameter uncertainty)"
        warns.append("SUMO backend: load factor not passed to SUMO; HBEFA licence applies")

    payload_n = scn.payload_tonnes()
    payload_r = scn.vehicle.spec()["payload_capacity_t"] * dr["lf"]
    return UnifiedResult(
        scn.name, "road", level, method, float(ttw_n[0]), float(wtw_n[0]),
        stats(ttw_r), stats(wtw_r), float(payload_n), warns,
        kg_per_t_ttw=ttw_r / payload_r, kg_per_t_wtw=wtw_r / payload_r)
