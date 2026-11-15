# Legacy v1 SUMO/HBEFA4 files (kept for transparency)

* `v1_hbefa4_truck_result.csv` - SUMO emissionsDrivingCycle output of the v1 truck run
  (9810 s, 1 Hz). Summing the CO2 column gives **189.367 kg**, i.e. the value used by the v1
  scripts. The v1 README table (152.354 kg at 60 km/h) is **not** reproducible from any file
  and has been dropped.
* `v1_trajectory_100km_36.7kmh.csv` - the matching v1 trajectory: 100 km at 36.7 km/h average with
  about 218 full stops (stop-and-go pattern, not a motorway). Superseded by
  `src/unity/trajectory.py`.
* Other v1 result files were removed: one had a different emission class (about 20.9 kg) and was
  mislabelled.

`tests/test_unity.py` re-reads the truck result file to keep the 189.367 kg check alive.
