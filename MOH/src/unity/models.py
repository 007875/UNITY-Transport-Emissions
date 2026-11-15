"""Emission models at three data levels (+ rail).

Each road model computes FUEL (litres) from a dictionary of "draws".  The point
estimate uses the nominal draw (all multipliers = 1), the Monte-Carlo analysis
uses random draws - so point estimate and uncertainty always come from the SAME
model code.

Level      | needs                              | method
-----------+------------------------------------+----------------------------------
low        | class, distance (+ load factor)    | consumption(L/km) linear in payload
medium     | + average speed, road type         | low x speed/road curve
high       | + 1 Hz speed trajectory            | physics (road-load) model per second
"""
from __future__ import annotations
import numpy as np
from . import params as P
from .scenario import TransportScenario
from .trajectory import summarize

LEVELS = ("low", "medium", "high")


# ----------------------------------------------------------------- draws ---
def _ln(rng, sigma, n):
    return rng.lognormal(0.0, sigma, n)


def nominal_draws(scn: TransportScenario) -> dict:
    lf = scn.vehicle.load_factor
    if lf is None:
        lf = P.DEFAULT_LOAD_FACTOR_TRIANGULAR[1]
    one = np.ones(1)
    return dict(lf=np.array([lf]), base=one, cond=one, curve=one, cda=one, crr=one,
                eng=one, tare=one, model=one,
                ttw_ef=np.array([P.DIESEL_TTW_KG_CO2_PER_L]),
                wtt_ef=np.array([P.DIESEL_WTT_KG_CO2E_PER_L]),
                non_co2=np.array([P.NON_CO2_FRACTION_OF_TTW]))


def random_draws(scn: TransportScenario, n: int, rng: np.random.Generator) -> dict:
    S = P.SIG
    lf0 = scn.vehicle.load_factor
    if lf0 is None:
        a, c, b = P.DEFAULT_LOAD_FACTOR_TRIANGULAR
        lf = rng.triangular(a, c, b, n)
    else:
        lf = np.clip(rng.normal(lf0, S["load_factor_sd"], n), 0.05, 1.0)
    return dict(
        lf=lf, base=_ln(rng, S["base_consumption"], n), cond=_ln(rng, S["conditions_low"], n),
        curve=_ln(rng, S["curve_medium"], n), cda=_ln(rng, S["cda"], n),
        crr=_ln(rng, S["crr"], n), eng=_ln(rng, S["engine_eff"], n),
        tare=_ln(rng, S["tare"], n), model=_ln(rng, S["model_high"], n),
        ttw_ef=P.DIESEL_TTW_KG_CO2_PER_L * _ln(rng, S["ttw_ef"], n),
        wtt_ef=P.DIESEL_WTT_KG_CO2E_PER_L * _ln(rng, S["wtt_ef"], n),
        non_co2=P.NON_CO2_FRACTION_OF_TTW * _ln(rng, S["non_co2"], n))


# ------------------------------------------------------------ road fuel ----
def _per_km_base(scn, d):
    s = scn.vehicle.spec()
    return s["l_per_km_empty"] + (s["l_per_km_full"] - s["l_per_km_empty"]) * d["lf"]


def speed_curve(v_kmh: float) -> float:
    """Relative consumption g(v) = A + B/v + C v^2 (illustrative, g(V_REF)=1)."""
    v = max(v_kmh, 5.0)
    return P.G_A + P.G_B / v + P.G_C * v ** 2


def fuel_low(scn, d):
    return _per_km_base(scn, d) * scn.trip.distance_km * d["base"] * d["cond"]


def fuel_medium(scn, d):
    t = scn.trip
    return (_per_km_base(scn, d) * t.distance_km * speed_curve(t.average_speed_kmh)
            * P.ROAD_FACTOR[t.road_type] * d["base"] * d["curve"])


def fuel_high(scn, d, chunk: int = 200):
    """Physics (road-load) fuel model on a 1 Hz speed trace; vectorised over draws."""
    s = scn.vehicle.spec()
    v = np.asarray(scn.trip.speed_trace_kmh, dtype=float) / 3.6          # m/s
    a = np.diff(v, prepend=v[0])                                          # m/s^2 (dt=1 s)
    summ = summarize(scn.trip.speed_trace_kmh)
    scale = scn.trip.distance_km / summ.distance_km                       # trace -> scenario distance
    n = d["lf"].size
    out = np.empty(n)
    lhv = P.DIESEL_LHV_MJ_PER_L * 1e6                                     # J / L
    for i in range(0, n, chunk):
        sl = slice(i, min(i + chunk, n))
        payload = s["payload_capacity_t"] * d["lf"][sl]
        mass = (s["tare_t"] * d["tare"][sl] + payload)[:, None] * 1000.0   # kg
        cda = (s["cda_m2"] * d["cda"][sl])[:, None]
        crr = (s["crr"] * d["crr"][sl])[:, None]
        force = mass * (a[None, :] + P.G * crr) + 0.5 * P.RHO_AIR * cda * v[None, :] ** 2
        p_wheel = np.maximum(force * v[None, :], 0.0)                      # W, no regeneration
        eta_eng = (s["engine_marginal_eff"] * d["eng"][sl])[:, None]
        fuel_s = p_wheel / s["drivetrain_eff"] / (eta_eng * lhv)           # L per second
        idle = s["baseline_l_per_h"] / 3600.0                              # friction/idle baseline
        out[sl] = (fuel_s.sum(axis=1) + idle * v.size) * scale * d["model"][sl]
    return out


FUEL_FUNCS = {"low": fuel_low, "medium": fuel_medium, "high": fuel_high}


def co2e_from_fuel(fuel_l, d):
    ttw = fuel_l * d["ttw_ef"] * (1.0 + d["non_co2"])
    wtt = fuel_l * d["wtt_ef"]
    return ttw, ttw + wtt


# ----------------------------------------------------------------- rail ----
def rail_per_tkm(scn: TransportScenario, n: int, rng: np.random.Generator | None):
    """Return (ttw, wtw) kg CO2e per tonne-km as arrays (nominal if rng is None)."""
    R = P.RAIL
    if rng is None:
        mult, gmult = np.ones(n), np.ones(n)
    else:
        mult, gmult = _ln(rng, R["sigma"], n), _ln(rng, R["grid_sigma"], n)
    if scn.vehicle.traction == "diesel":
        ttw = R["diesel_ttw_kg_co2e_per_tkm"] * mult
        wtw = ttw + ttw * (P.DIESEL_WTT_KG_CO2E_PER_L / P.DIESEL_TTW_KG_CO2_PER_L)
    else:
        ttw = np.zeros(n)
        wtw = R["electric_kwh_per_tkm"] * mult * R["grid_kg_co2e_per_kwh"] * gmult
    return ttw, wtw
