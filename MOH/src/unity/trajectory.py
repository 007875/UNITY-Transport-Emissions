"""Synthetic but realistic 1 Hz heavy-truck speed trajectories.

v1 problem: the generator stopped the truck every ~1 km (even on a "motorway")
and did not actually control the mean speed.  v2 fixes both:

* road type decides the stop pattern (motorway: no stops except the end points;
  rural: rare junction stops and slow zones; urban: frequent stops),
* heavy-truck acceleration/deceleration limits are used (0.5 / 0.8 m/s^2),
* the cruise speed is calibrated by bisection so the realised trip-average
  speed matches the requested one (tolerance 0.3 %).

The trajectories are still SYNTHETIC (seeded, reproducible).  They are meant
as controlled benchmark inputs, not as measured driving cycles.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

ACC_MS2 = 0.5
DEC_MS2 = 0.8
V_MAX_KMH = 90.0

_PATTERN = {
    # mean stop spacing (m) or None, stop dwell range (s), speed noise (rel. sd),
    # slow-zone: (mean spacing m, length m, speed factor)
    "motorway": dict(vmax=90.0, stop_every=None, dwell=(0, 0), noise=0.03, zone=(25000, 800, 0.65)),
    "rural": dict(vmax=80.0, stop_every=15000, dwell=(10, 30), noise=0.06, zone=(5000, 500, 0.55)),
    "urban": dict(vmax=60.0, stop_every=450, dwell=(5, 25), noise=0.10, zone=None),
}


@dataclass
class TrajectorySummary:
    duration_s: float
    distance_km: float
    average_speed_kmh: float
    moving_average_speed_kmh: float
    max_speed_kmh: float
    max_acceleration_ms2: float
    max_deceleration_ms2: float
    n_stops: int            # intermediate stops (start and end excluded)
    stops_per_100km: float


def summarize(speed_kmh) -> TrajectorySummary:
    v = np.asarray(speed_kmh, dtype=float)
    if v.size < 2:
        raise ValueError("trajectory needs at least 2 points")
    ms = v / 3.6
    dist_m = float(np.sum((ms[1:] + ms[:-1]) / 2.0))        # dt = 1 s
    dur = float(v.size - 1)
    acc = np.diff(ms)
    moving = v > 0.5
    stopped = ~moving
    # intermediate stops = transitions moving -> stopped, excluding the final one
    trans = np.where(moving[:-1] & stopped[1:])[0]
    n_stops = max(len(trans) - 1, 0)
    km = dist_m / 1000.0
    return TrajectorySummary(
        duration_s=dur, distance_km=km,
        average_speed_kmh=km / (dur / 3600.0),
        moving_average_speed_kmh=float(v[moving].mean()) if moving.any() else 0.0,
        max_speed_kmh=float(v.max()), max_acceleration_ms2=float(acc.max()),
        max_deceleration_ms2=float(-acc.min()), n_stops=n_stops,
        stops_per_100km=n_stops / km * 100.0 if km > 0 else 0.0)


def _simulate(distance_km, cruise_kmh, road_type, seed):
    pat = _PATTERN[road_type]
    rng = np.random.default_rng(seed)
    D = distance_km * 1000.0
    # stop positions (+ the final stop at D)
    stops = []
    if pat["stop_every"]:
        p = 0.0
        while True:
            p += max(150.0, rng.exponential(pat["stop_every"]))
            if p >= D - 300.0:
                break
            stops.append((p, int(rng.integers(pat["dwell"][0], pat["dwell"][1] + 1))))
    stops.append((D, 0))
    # slow zones
    zones = []
    if pat["zone"]:
        p = 0.0
        while True:
            p += rng.exponential(pat["zone"][0])
            if p >= D:
                break
            zones.append((p, p + pat["zone"][1]))
    vc = cruise_kmh / 3.6
    pos, v, k, dwell_left, ou = 0.0, 0.0, 0, 0, 0.0
    trace = [0.0]
    for _ in range(200000):
        if k >= len(stops):
            break
        stop_pos, stop_dwell = stops[k]
        if dwell_left > 0:
            dwell_left -= 1
            trace.append(0.0)
            if dwell_left == 0:
                k += 1
            continue
        ou = 0.98 * ou + rng.normal(0.0, pat["noise"] * 0.2)       # slowly varying noise
        vdes = vc * max(0.5, 1.0 + ou)
        if any(a <= pos <= b for a, b in zones):
            vdes *= pat["zone"][2]
        gap = stop_pos - pos
        vdes = min(vdes, pat['vmax'] / 3.6, np.sqrt(max(2.0 * DEC_MS2 * 0.7 * gap, 0.0)))
        dv = np.clip(vdes - v, -DEC_MS2, ACC_MS2)
        vn = max(v + dv, 0.0)
        step = 0.5 * (v + vn)
        if v <= 1.0 and (pos + step >= stop_pos - 0.5 or gap < 2.0):
            pos, v = stop_pos, 0.0
            trace.append(0.0)
            if stop_dwell > 0:
                dwell_left = stop_dwell
            else:
                k += 1
            continue
        if vn < 0.3 and gap > 3.0:
            vn = 0.3                                              # avoid creeping deadlock
        pos, v = min(pos + 0.5 * (v + vn), stop_pos), vn
        trace.append(vn * 3.6)
    return np.array(trace)


def build_trajectory(distance_km: float, avg_speed_kmh: float, road_type: str = "motorway",
                     seed: int = 0, tol: float = 0.003) -> np.ndarray:
    """Return a 1 Hz speed trace (km/h) whose trip-average speed is within ``tol``."""
    if distance_km <= 0 or avg_speed_kmh <= 0:
        raise ValueError("distance and average speed must be > 0")
    if road_type not in _PATTERN:
        raise ValueError(f"road_type must be one of {tuple(_PATTERN)}")
    lo, hi = 5.0, _PATTERN[road_type]['vmax'] + 20.0
    best = None
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        tr = _simulate(distance_km, mid, road_type, seed)
        s = summarize(tr)
        best = (tr, s)
        err = s.average_speed_kmh / avg_speed_kmh - 1.0
        if abs(err) <= tol:
            break
        if err < 0:
            lo = mid
        else:
            hi = mid
    tr, s = best
    if abs(s.average_speed_kmh / avg_speed_kmh - 1.0) > 0.01 or s.max_speed_kmh > _PATTERN[road_type]['vmax'] + 5:
        raise ValueError(
            f"Average speed {avg_speed_kmh} km/h is not feasible for a heavy truck on "
            f"'{road_type}' roads with this trajectory model "
            f"(achieved {s.average_speed_kmh:.1f} km/h, max {s.max_speed_kmh:.1f} km/h).")
    return tr


def save_sumo_timeline(speed_kmh, path: str) -> None:
    """Write the ``time;speed`` file expected by SUMO's emissionsDrivingCycle (--kmh)."""
    with open(path, "w", newline="") as f:
        for t, v in enumerate(speed_kmh):
            f.write(f"{t};{v:.3f}\n")
