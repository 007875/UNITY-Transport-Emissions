"""Optional SUMO / HBEFA4 backend for the high-data level.

SUMO is NOT required: the default high-data model is the open physics model in
``models.py``.  This adapter lets you cross-check against HBEFA4 if SUMO is
installed.  Fixes compared with v1:

* the executable is found via ``UNITY_SUMO_EMISSIONS_EXE`` / ``SUMO_HOME`` / PATH
  (no hard-coded Windows path),
* results are normalised with the distance of the trace that was actually run,
* the same 1 Hz trace, class and scenario are used as for the other models.

Note: the HBEFA4 class is chosen from the vehicle class; the load factor is not
passed to SUMO here (check your SUMO version for a vehicle-mass option) - this
is reported as a warning by ``unified.estimate``.  Check the HBEFA/SUMO licence
terms before redistributing HBEFA-derived data.
"""
from __future__ import annotations
import csv, os, shutil, subprocess, tempfile
from .trajectory import save_sumo_timeline, summarize
from . import params as P


def find_sumo_exe() -> str | None:
    env = os.environ.get("UNITY_SUMO_EMISSIONS_EXE")
    if env and os.path.exists(env):
        return env
    home = os.environ.get("SUMO_HOME")
    if home:
        for name in ("emissionsDrivingCycle", "emissionsDrivingCycle.exe"):
            p = os.path.join(home, "bin", name)
            if os.path.exists(p):
                return p
    return shutil.which("emissionsDrivingCycle") or shutil.which("emissionsDrivingCycle.exe")


def read_result(path: str) -> dict:
    """Sum a SUMO emissionsDrivingCycle result (1 Hz, values in mg/s -> mg per step)."""
    tot = dict(co2_mg=0.0, co_mg=0.0, hc_mg=0.0, pmx_mg=0.0, nox_mg=0.0, fuel_mg=0.0, rows=0)
    with open(path, newline="") as f:
        for row in csv.reader(f, delimiter=";"):
            if not row:
                continue
            tot["co_mg"] += float(row[4]); tot["co2_mg"] += float(row[5])
            tot["hc_mg"] += float(row[6]); tot["pmx_mg"] += float(row[7])
            tot["nox_mg"] += float(row[8]); tot["fuel_mg"] += float(row[9])
            tot["rows"] += 1
    tot["co2_kg"] = tot["co2_mg"] / 1e6
    tot["fuel_kg"] = tot["fuel_mg"] / 1e6
    return tot


def run_hbefa4(speed_trace_kmh, vehicle_class: str) -> dict:
    exe = find_sumo_exe()
    if exe is None:
        raise FileNotFoundError(
            "SUMO emissionsDrivingCycle not found. Set UNITY_SUMO_EMISSIONS_EXE or SUMO_HOME, "
            "or use the default physics backend (high_backend='physics').")
    cls = P.VEHICLES[vehicle_class]["hbefa4_class"]
    with tempfile.TemporaryDirectory() as tmp:
        tl, out = os.path.join(tmp, "timeline.csv"), os.path.join(tmp, "result.csv")
        save_sumo_timeline(speed_trace_kmh, tl)
        cmd = [exe, "--timeline-file", tl, "--kmh", "--compute-a", "--emission-class", cls,
               "--output-file", out]
        done = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if done.returncode != 0 or not os.path.exists(out):
            raise RuntimeError(f"SUMO failed:\nSTDOUT:{done.stdout}\nSTDERR:{done.stderr}")
        res = read_result(out)
    res["trace_distance_km"] = summarize(speed_trace_kmh).distance_km
    return res
