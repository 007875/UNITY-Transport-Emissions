# What changed from v1 to v2 (response to the review)

| # | Review finding | Status in v2 |
|---|---|---|
| A1 | README numbers (152.354 kg) did not match the shipped files (189.367 kg) | **Fixed.** One reference scenario file; `run_all.py` regenerates all tables; README numbers are copied from `results/results.md`. The legacy SUMO file is kept in `data/legacy_sumo/` and re-checked by a test (189.367 kg). The unreproducible 152.354 figure is dropped. |
| A2 | Payload computed as GVW x load factor | **Fixed.** Payload = payload capacity x load factor (`scenario.payload_tonnes`, test `test_payload_uses_capacity_not_gvw`). Consumption is now L/km linear in payload with documented placeholder values (about 31.6 L/100 km at 60 % load for the rigid truck) instead of 0.036 L/t-km x 18 t = 64.8 L/100 km. |
| A3 | Unrealistic "motorway" trajectory (about 218 stops per 100 km) | **Fixed.** Road-type specific stop patterns, heavy-truck acceleration limits (0.5 / 0.8 m/s^2), cruise speed calibrated so the average speed is within 0.3 %. Tests check stops, speed and acceleration. Trajectories remain synthetic. |
| A4 | "Accuracy" not implemented | **Implemented (framework).** Monte-Carlo with parameter and model-form uncertainty per data level; p5/p50/p95 in every result. The uncertainty magnitudes are assumptions and still need calibration against reference data. |
| A5 | "Unified" was a manual if/else; diagram claimed more than the code | **Fixed.** `select_level()` chooses the method from available fields; `with_information()` builds an information ladder; the diagram is redrawn to match the code. |
| B1 | Models did not share the same inputs (load factor missing in SUMO) | **Fixed for the built-in models** (all use the same scenario and load factor). The optional SUMO backend still does not pass the load factor and says so in a warning. |
| B2 | Boundary / CO2e missing | **Improved.** TTW and WTW, CO2e with a non-CO2 share, boundary stated in every result. WTT and non-CO2 factors are placeholders to be replaced with cited values. |
| B3 | Ad-hoc stepwise medium factors | **Improved.** Smooth speed curve + road factors. Still illustrative; to be replaced by a published model in the research phase. |
| B4 | Hard-coded Option B, always-green message, trivial 0.86 % flip | **Fixed.** Option B is a real scenario; decision metrics are P(wrong decision), expected regret and agreement with the high-data reference; routing sweep and road vs rail comparison. |
| B5 | Windows-only hard-coded paths, distance not used, column indices | **Fixed.** SUMO found via env variables/PATH; results normalised by the run trace's own distance; no hard-coded paths. |
| B6 | Empty tests, empty folders, `__pycache__`, mislabelled files, duplicate dashboard | **Fixed.** 17 unit tests, clean repo, legacy files renamed and explained, single Streamlit dashboard. |
| B7 | Dashboard offered unsupported options | **Fixed.** Only supported options are offered. (Dashboard not launched in the preparation environment.) |
| C | Licence, requirements, run command, long README, open-source claim | **Done:** MIT licence, `requirements.txt`, `run_all.py`, README with summary first, HBEFA licence caveat, default physics backend independent of HBEFA. |
| New | Second mode, decision analysis for the project's part 3 | Rail (low data) and routing / road-vs-rail decision analysis added. |

## Not done / still open

* No validation against measured data; all vehicle, fuel-chain and uncertainty parameters are placeholders.
* SUMO/HBEFA4 backend not executed here. Dashboard not launched here.
* No first/last-mile for rail, no further modes, no optimisation solver yet (planned for the PhD).
