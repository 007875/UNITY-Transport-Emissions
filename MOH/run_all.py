"""Reproduce EVERY number, table and figure of the prototype with one command:

    python run_all.py

Outputs (results/): levels_table.csv, decision_table.csv, results.md, figures/*.png,
results.json.  README numbers are copied from results.md.
"""
import json, os, sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
from unity import Vehicle, Trip, TransportScenario, estimate, with_information, compare   # noqa: E402
from unity.trajectory import build_trajectory, summarize                                    # noqa: E402

OUT = os.path.join(ROOT, "results")
FIG = os.path.join(OUT, "figures")
os.makedirs(FIG, exist_ok=True)


def load_config():
    with open(os.path.join(ROOT, "data", "scenarios", "reference_scenarios.json")) as f:
        return json.load(f)


def build_road_scenario(s):
    tr = build_trajectory(s["distance_km"], s["avg_speed_kmh"], s["road_type"], seed=s["traj_seed"])
    return TransportScenario(f'{s["id"]} {s["name"]}', "road",
                             Vehicle(s["vehicle_class"], load_factor=s["load_factor"]),
                             Trip(s["distance_km"], None, s["road_type"], tr))


def main():
    cfg = load_config()
    n, seed = cfg["n_monte_carlo"], cfg["seed"]
    rows, dec_rows, traj_rows = [], [], []
    store = {}
    for s in cfg["scenarios"]:
        full = build_road_scenario(s)
        ts = summarize(full.trip.speed_trace_kmh)
        traj_rows.append(dict(scenario=s["id"], target_speed=s["avg_speed_kmh"],
                              realised_speed=round(ts.average_speed_kmh, 2),
                              max_speed=round(ts.max_speed_kmh, 1), stops_per_100km=round(ts.stops_per_100km, 1),
                              max_acc=round(ts.max_acceleration_ms2, 2), max_dec=round(ts.max_deceleration_ms2, 2)))
        res = {lv: estimate(with_information(full, lv), lv, n=n, seed=seed) for lv in ("low", "medium", "high")}
        store[s["id"]] = res
        for lv, r in res.items():
            rows.append(dict(scenario=s["id"], name=s["name"], **{k: v for k, v in r.summary_row().items()
                                                                  if k not in ("scenario",)}))
        # decision: road (at each data level) vs rail alternatives, same shipment
        payload = res["high"].payload_t
        for alt in cfg["rail_alternatives"]:
            rail = TransportScenario(f'{alt["label"]}', "rail", Vehicle("rail", traction=alt["traction"]),
                                     Trip(s["distance_km"] * cfg["route_factor_rail"]), shipment_tonnes=payload)
            rr = estimate(rail, n=n, seed=seed + 1)
            for lv in ("low", "medium", "high"):
                d = compare(res[lv], rr, "wtw")
                dec_rows.append(dict(scenario=s["id"], road_level=lv, alternative=alt["label"],
                                     **{k: d[k] for k in ("nominal_winner", "nominal_difference_pct", "p_wrong",
                                                          "expected_regret_kg_per_t", "ratio_a_over_b_p5",
                                                          "ratio_a_over_b_p95", "robust")}))
    lv_df, dec_df, tr_df = pd.DataFrame(rows), pd.DataFrame(dec_rows), pd.DataFrame(traj_rows)
    lv_df.to_csv(os.path.join(OUT, "levels_table.csv"), index=False)
    dec_df.to_csv(os.path.join(OUT, "decision_table.csv"), index=False)
    tr_df.to_csv(os.path.join(OUT, "trajectory_checks.csv"), index=False)


    # ----- routing decision: longer motorway route (A) vs shorter rural route (B) -----
    # Same truck, same load; options share the Monte-Carlo draws (same seed), so common
    # vehicle uncertainty cancels and only route-specific information matters.
    A = res_s1 = store["S1"]
    base_s = cfg["scenarios"][0]
    scn_a = build_road_scenario(base_s)
    route_rows = []
    for dist_b in np.arange(70.0, 100.1, 2.5):
        trb = build_trajectory(float(dist_b), 55, "rural", seed=11)
        scn_b = TransportScenario(f"B rural {dist_b:.1f} km", "road", Vehicle("rigid_truck", load_factor=0.6),
                                  Trip(float(dist_b), None, "rural", trb))
        for lv in ("low", "medium", "high"):
            ra = estimate(with_information(scn_a, lv), lv, n=n, seed=seed)
            rb = estimate(with_information(scn_b, lv), lv, n=n, seed=seed)
            d = compare(ra, rb, "wtw")
            route_rows.append(dict(dist_b_km=float(dist_b), level=lv, nominal_winner=d["nominal_winner"],
                                   nominal_difference_pct=d["nominal_difference_pct"],
                                   signed_b_minus_a_pct=(d["nominal_b_kg_per_t"] - d["nominal_a_kg_per_t"]) / d["nominal_a_kg_per_t"] * 100,
                                   p_wrong=d["p_wrong"], expected_regret_kg_per_t=d["expected_regret_kg_per_t"]))
    route_df = pd.DataFrame(route_rows)
    # Decision quality against the high-data model used as REFERENCE (itself a placeholder model):
    # a coarse level is "wrong" if it picks a different route than the high-data estimate.
    ref = route_df[route_df.level == "high"].set_index("dist_b_km")
    wrong, regret = [], []
    for _, r_ in route_df.iterrows():
        rr_ = ref.loc[r_.dist_b_km]
        is_wrong = r_.nominal_winner != rr_.nominal_winner
        # regret in % of the best option's high-data emissions when the coarse winner is followed
        gap = abs(rr_.signed_b_minus_a_pct)
        wrong.append(bool(is_wrong))
        regret.append(float(gap / (100 + min(rr_.signed_b_minus_a_pct, 0)) * 100) if is_wrong else 0.0)
    route_df["wrong_vs_high_reference"] = wrong
    route_df["regret_vs_high_pct"] = regret
    route_df.to_csv(os.path.join(OUT, "routing_decision_table.csv"), index=False)

    # ----- figures -----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sc_ids = [s["id"] for s in cfg["scenarios"]]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    w, cols = 0.25, {"low": "#6aa84f", "medium": "#3d85c6", "high": "#8e63b8"}
    for j, lv in enumerate(("low", "medium", "high")):
        sub = lv_df[lv_df.level == lv].set_index("scenario").loc[sc_ids]
        x = np.arange(len(sc_ids)) + (j - 1) * w
        ax.bar(x, sub.wtw_p50, w, color=cols[lv], label=f"{lv} data (median)",
               yerr=[sub.wtw_p50 - sub.wtw_p5, sub.wtw_p95 - sub.wtw_p50], capsize=3)
    ax.set_xticks(range(len(sc_ids))); ax.set_xticklabels(sc_ids)
    ax.set_ylabel("kg CO2e per trip (WTW), median with 5-95 % interval")
    ax.set_title("Estimate and uncertainty by data level (placeholder assumptions)")
    ax.legend(); fig.tight_layout(); fig.savefig(os.path.join(FIG, "uncertainty_by_level.png"), dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.6))
    for j, lv in enumerate(("low", "medium", "high")):
        sub = dec_df[(dec_df.road_level == lv) & (dec_df.alternative == "Rail (electric)")].set_index("scenario").loc[sc_ids]
        ax.bar(np.arange(len(sc_ids)) + (j - 1) * w, sub.p_wrong, w, color=cols[lv], label=f"{lv} data")
    ax.axhline(0.05, color="red", ls="--", lw=1, label="5 % threshold")
    ax.set_xticks(range(len(sc_ids))); ax.set_xticklabels(sc_ids)
    ax.set_ylabel("P(wrong decision)"); ax.set_title("Road vs electric rail: probability the nominal winner is truly worse")
    ax.legend(); fig.tight_layout(); fig.savefig(os.path.join(FIG, "decision_p_wrong.png"), dpi=150); plt.close(fig)


    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4))
    for lv in ("low", "medium", "high"):
        sub = route_df[route_df.level == lv]
        axs[0].plot(sub.dist_b_km, sub.signed_b_minus_a_pct, marker="o", ms=3, color=cols[lv], label=f"{lv} data")
        axs[1].plot(sub.dist_b_km, sub.p_wrong, marker="o", ms=3, color=cols[lv], label=f"{lv} data")
        axs[2].plot(sub.dist_b_km, sub.regret_vs_high_pct, marker="o", ms=3, color=cols[lv], label=f"{lv} data")
    axs[0].axhline(0, color="k", lw=0.8); axs[0].set_xlabel("length of route B (km)")
    axs[0].set_ylabel("nominal (B - A) / A  [%]"); axs[0].set_title("Nominal advantage of the shorter rural route B")
    axs[1].axhline(0.05, color="red", ls="--", lw=1); axs[1].set_xlabel("length of route B (km)")
    axs[1].set_ylabel("P(wrong decision)"); axs[1].set_title("Probability that the nominal winner is truly worse")
    axs[2].set_xlabel("length of route B (km)"); axs[2].set_ylabel("regret vs high-data reference [%]"); axs[2].set_title("Cost of deciding with coarser data")
    axs[0].legend(); fig.tight_layout(); fig.savefig(os.path.join(FIG, "routing_decision.png"), dpi=150); plt.close(fig)

    s0 = build_road_scenario(cfg["scenarios"][0]).trip.speed_trace_kmh
    s3 = build_road_scenario(cfg["scenarios"][2]).trip.speed_trace_kmh
    fig, axs = plt.subplots(2, 1, figsize=(9, 5))
    axs[0].plot(np.asarray(s0[:1500]), lw=0.8); axs[0].set_title("S1 motorway trajectory (first 25 min)")
    axs[1].plot(np.asarray(s3[:1500]), lw=0.8, color="darkorange"); axs[1].set_title("S3 urban trajectory (first 25 min)")
    for a in axs: a.set_ylabel("km/h")
    axs[1].set_xlabel("s"); fig.tight_layout(); fig.savefig(os.path.join(FIG, "trajectories.png"), dpi=150); plt.close(fig)

    # ----- markdown -----
    def f(x, d=1): return f"{x:.{d}f}"
    md = ["# UNITY v2 - generated results", "",
          f"Monte-Carlo samples: {n}, seed: {seed}. All inputs are placeholder assumptions (src/unity/params.py); "
          "these numbers demonstrate the framework, they are not validated findings.", "",
          "## Trajectory checks", "", tr_df.to_markdown(index=False), "",
          "## Estimates by data level (kg CO2e per trip, WTW)", ""]
    t = lv_df[["scenario", "level", "wtw_point_kg", "wtw_p5", "wtw_p50", "wtw_p95", "wtw_rel_half_width", "ttw_point_kg"]].copy()
    for c in t.columns[2:]: t[c] = t[c].map(lambda v: round(v, 3 if c == "wtw_rel_half_width" else 1))
    md += [t.to_markdown(index=False), "", "## Decision: road vs rail (per tonne, WTW; scenarios S1 and S4 shown)", ""]
    d = dec_df.copy()
    for c in ("nominal_difference_pct", "expected_regret_kg_per_t"): d[c] = d[c].round(2)
    for c in ("p_wrong", "ratio_a_over_b_p5", "ratio_a_over_b_p95"): d[c] = d[c].round(3)
    md += [d[d.scenario.isin(["S1", "S4"])].to_markdown(index=False), ""]
    r = route_df[["dist_b_km", "level", "nominal_winner", "signed_b_minus_a_pct", "p_wrong",
                  "wrong_vs_high_reference", "regret_vs_high_pct"]].copy()
    for c in ("signed_b_minus_a_pct", "regret_vs_high_pct"): r[c] = r[c].round(2)
    r["p_wrong"] = r["p_wrong"].round(3)
    md += ["## Routing decision: route A (100 km motorway, 80 km/h) vs route B (rural, 55 km/h, varying length)", "",
           "signed_b_minus_a_pct < 0: B has lower nominal emissions. p_wrong = probability the nominal winner is truly worse INSIDE that level (parameter uncertainty only, paired draws). wrong_vs_high_reference = the level picks a different route than the high-data estimate (model-level error; high-data model used as reference, itself a placeholder).", "",
           r.to_markdown(index=False), ""]
    with open(os.path.join(OUT, "results.md"), "w") as fh:
        fh.write("\n".join(md))
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(dict(levels=rows, decisions=dec_rows, trajectories=traj_rows), fh, indent=1)
    print("\n".join(md))


if __name__ == "__main__":
    main()
