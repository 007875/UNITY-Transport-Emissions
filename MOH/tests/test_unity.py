import os, sys, unittest
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from unity import Vehicle, Trip, TransportScenario, estimate, select_level, with_information, compare  # noqa
from unity.trajectory import build_trajectory, summarize                                         # noqa
from unity import sumo_backend, params as P                                                      # noqa


def road(lf=0.6, dist=100, speed=None, rt=None, trace=None, vc="rigid_truck"):
    return TransportScenario("t", "road", Vehicle(vc, load_factor=lf), Trip(dist, speed, rt, trace))


class TestScenario(unittest.TestCase):
    def test_payload_uses_capacity_not_gvw(self):
        s = road(lf=0.6)
        self.assertAlmostEqual(s.payload_tonnes(), 0.6 * P.VEHICLES["rigid_truck"]["payload_capacity_t"])
        self.assertLess(s.payload_tonnes(), 0.6 * P.VEHICLES["rigid_truck"]["gvw_t"])

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError): road(lf=1.5).validate()
        with self.assertRaises(ValueError): road(dist=-1).validate()
        with self.assertRaises(ValueError): road(vc="van").validate()
        s = TransportScenario("x", "road", Vehicle("rigid_truck", fuel_type="petrol"), Trip(10))
        with self.assertRaises(ValueError): s.validate()


class TestTrajectory(unittest.TestCase):
    def test_motorway_is_realistic(self):
        s = summarize(build_trajectory(100, 80, "motorway", seed=1))
        self.assertLessEqual(s.n_stops, 1)                      # v1 had ~218 stops
        self.assertLess(abs(s.average_speed_kmh / 80 - 1), 0.01)
        self.assertLessEqual(s.max_acceleration_ms2, 0.55)
        self.assertLessEqual(s.max_deceleration_ms2, 1.1)
        self.assertLess(abs(s.distance_km - 100), 1.0)

    def test_urban_has_many_stops(self):
        s = summarize(build_trajectory(50, 18, "urban", seed=3))
        self.assertGreater(s.stops_per_100km, 50)

    def test_infeasible_speed_raises(self):
        with self.assertRaises(ValueError): build_trajectory(50, 40, "urban", seed=1)

    def test_reproducible(self):
        a, b = build_trajectory(30, 70, "rural", seed=5), build_trajectory(30, 70, "rural", seed=5)
        np.testing.assert_array_equal(a, b)


class TestUnified(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tr = build_trajectory(100, 80, "motorway", seed=1)
        cls.full = road(speed=None, rt="motorway", trace=cls.tr)

    def test_auto_level_selection(self):
        self.assertEqual(select_level(road())[0], "low")
        self.assertEqual(select_level(road(speed=60, rt="rural"))[0], "medium")
        self.assertEqual(select_level(self.full)[0], "high")
        self.assertEqual(select_level(road(speed=60))[0], "low")          # needs speed AND road type

    def test_forced_level_checks_inputs(self):
        with self.assertRaises(ValueError): estimate(road(), "high")
        with self.assertRaises(ValueError): estimate(road(), "medium")

    def test_interval_ordering_and_wtw_above_ttw(self):
        for lv in ("low", "medium", "high"):
            r = estimate(with_information(self.full, lv), lv, n=500, seed=1)
            self.assertLess(r.wtw["p5"], r.wtw["p50"]); self.assertLess(r.wtw["p50"], r.wtw["p95"])
            self.assertGreater(r.point_wtw_kg, r.point_ttw_kg)

    def test_deterministic_with_seed(self):
        a = estimate(road(), n=400, seed=7); b = estimate(road(), n=400, seed=7)
        self.assertEqual(a.wtw, b.wtw)

    def test_high_level_interval_narrower_than_low(self):
        lo = estimate(with_information(self.full, "low"), "low", n=1500, seed=3)
        hi = estimate(with_information(self.full, "high"), "high", n=1500, seed=3)
        self.assertLess(hi.wtw["rel_half_width"], lo.wtw["rel_half_width"])   # follows from the assumed sigmas

    def test_payload_scaling(self):
        a = estimate(road(lf=0.3), "low", n=300); b = estimate(road(lf=0.9), "low", n=300)
        self.assertLess(a.point_ttw_kg, b.point_ttw_kg)

    def test_rail(self):
        rail = TransportScenario("r", "rail", Vehicle("rail", traction="electric"), Trip(115), shipment_tonnes=10)
        r = estimate(rail, n=300)
        self.assertEqual(r.mode, "rail"); self.assertEqual(r.point_ttw_kg, 0.0); self.assertGreater(r.point_wtw_kg, 0)
        with self.assertRaises(ValueError): estimate(rail, "high")


class TestDecision(unittest.TestCase):
    def test_probability_bounds_and_symmetry(self):
        a = estimate(road(speed=80, rt="motorway"), n=800, seed=1)
        b = estimate(road(speed=55, rt="rural", dist=95), n=800, seed=1)
        d1, d2 = compare(a, b), compare(b, a)
        self.assertTrue(0.0 <= d1["p_wrong"] <= 1.0)
        self.assertAlmostEqual(d1["p_wrong"], d2["p_wrong"])
        self.assertNotEqual(d1["nominal_winner"], d2["nominal_winner"])

    def test_identical_options_are_not_robust(self):
        a = estimate(road(), n=1000, seed=1); b = estimate(road(), n=1000, seed=2)
        self.assertFalse(compare(a, b)["robust"])


class TestSumoBackend(unittest.TestCase):
    def test_legacy_result_reproduces_v1_number(self):
        res = sumo_backend.read_result(os.path.join(ROOT, "data", "legacy_sumo", "v1_hbefa4_truck_result_36.7kmh.csv"))
        self.assertAlmostEqual(res["co2_kg"], 189.367, places=2)

    def test_missing_sumo_gives_clear_error(self):
        if sumo_backend.find_sumo_exe() is None:
            with self.assertRaises(FileNotFoundError):
                sumo_backend.run_hbefa4(np.zeros(10), "rigid_truck")


if __name__ == "__main__":
    unittest.main()
