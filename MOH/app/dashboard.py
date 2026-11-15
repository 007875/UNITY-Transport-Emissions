"""Streamlit dashboard:  streamlit run app/dashboard.py

Only options that the model really supports are offered (v1 listed vans, petrol, Euro IV/V ...
that raised errors).  Option B of the decision panel is a real second scenario, not a constant.
"""
import os, sys
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from unity import Vehicle, Trip, TransportScenario, estimate, select_level, with_information, compare  # noqa
from unity.trajectory import build_trajectory, summarize                                              # noqa

st.set_page_config(page_title="UNITY v2", layout="wide")
st.title("UNITY v2 - transport emission estimates with uncertainty")
st.caption("Research prototype. All vehicle, fuel-chain and uncertainty numbers are placeholder "
           "assumptions (src/unity/params.py); results demonstrate the framework only.")


def scenario_form(prefix, defaults):
    c = st.columns(5)
    vc = c[0].selectbox("Vehicle", ["rigid_truck", "articulated_truck"], key=prefix + "vc",
                        index=["rigid_truck", "articulated_truck"].index(defaults["vc"]))
    lf = c[1].slider("Load factor (of payload capacity)", 0.1, 1.0, defaults["lf"], 0.05, key=prefix + "lf")
    dist = c[2].number_input("Distance (km)", 5.0, 2000.0, float(defaults["dist"]), key=prefix + "d")
    rt = c[3].selectbox("Road type", ["motorway", "rural", "urban"], key=prefix + "rt",
                        index=["motorway", "rural", "urban"].index(defaults["rt"]))
    maxv = {"motorway": 85, "rural": 70, "urban": 20}[rt]
    v = c[4].slider("Average speed (km/h)", 10, maxv, min(defaults["v"], maxv), key=prefix + "v")
    return vc, lf, dist, rt, float(v)


def build(name, vc, lf, dist, rt, v, seed):
    tr = build_trajectory(dist, v, rt, seed=seed)
    return TransportScenario(name, "road", Vehicle(vc, load_factor=lf), Trip(dist, None, rt, tr))


tab1, tab2 = st.tabs(["Estimate by data level", "Decision: route A vs route B"])

with tab1:
    vc, lf, dist, rt, v = scenario_form("a", dict(vc="rigid_truck", lf=0.6, dist=100, rt="motorway", v=80))
    n = st.select_slider("Monte-Carlo samples", [500, 1000, 3000], value=1000)
    try:
        scn = build("A", vc, lf, dist, rt, v, 1)
    except ValueError as e:
        st.error(str(e)); st.stop()
    ts = summarize(scn.trip.speed_trace_kmh)
    st.write(f"Synthetic trajectory: average {ts.average_speed_kmh:.1f} km/h, "
             f"{ts.stops_per_100km:.0f} stops per 100 km, max {ts.max_speed_kmh:.0f} km/h")
    rows = []
    for lv in ("low", "medium", "high"):
        r = estimate(with_information(scn, lv), lv, n=n, seed=42)
        rows.append(dict(level=lv, wtw_p5=r.wtw["p5"], wtw_p50=r.wtw["p50"], wtw_p95=r.wtw["p95"],
                         wtw_point=r.point_wtw_kg, ttw_point=r.point_ttw_kg, method=r.method))
    df = pd.DataFrame(rows)
    st.dataframe(df.round(1), use_container_width=True)
    st.bar_chart(df.set_index("level")[["wtw_p5", "wtw_p50", "wtw_p95"]])
    auto = select_level(scn)[0]
    st.info(f"With all inputs available the unified estimator would automatically use the '{auto}' level.")

with tab2:
    st.write("Same truck type and load; the two options differ in route (distance and speed profile).")
    ca, cb = st.columns(2)
    with ca:
        st.subheader("Route A"); pa = scenario_form("ra", dict(vc="rigid_truck", lf=0.6, dist=100, rt="motorway", v=80))
    with cb:
        st.subheader("Route B"); pb = scenario_form("rb", dict(vc="rigid_truck", lf=0.6, dist=90, rt="rural", v=55))
    try:
        A, B = build("A", *pa, 1), build("B", *pb, 2)
    except ValueError as e:
        st.error(str(e)); st.stop()
    out = []
    for lv in ("low", "medium", "high"):
        d = compare(estimate(with_information(A, lv), lv, n=1000, seed=42),
                    estimate(with_information(B, lv), lv, n=1000, seed=42))
        out.append(dict(level=lv, nominal_winner=d["nominal_winner"], difference_pct=d["nominal_difference_pct"],
                        p_wrong=d["p_wrong"], robust=d["robust"]))
    res = pd.DataFrame(out)
    st.dataframe(res.round(3), use_container_width=True)
    winners = set(res.nominal_winner)
    if len(winners) > 1:
        st.warning("The data levels disagree about the better route: the level of available data changes the decision.")
    else:
        st.success("All data levels pick the same route in this configuration.")
    st.caption("p_wrong covers parameter uncertainty inside a level; disagreement between levels reveals model-level error.")
