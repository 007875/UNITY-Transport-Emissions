"""Decision analysis: does the accuracy of the estimates change the decision?"""
from __future__ import annotations
import numpy as np
from .unified import UnifiedResult


def compare(a: UnifiedResult, b: UnifiedResult, boundary: str = "wtw",
            confidence: float = 0.95) -> dict:
    """Compare two options per tonne of freight.

    Samples are compared pairwise (sample i of A against sample i of B).  If both options
    were estimated with the SAME seed and vehicle, the common-parameter draws are shared
    (positively correlated), which is the right model for "same truck, different route".
    For unrelated options (road vs rail) use different seeds (independent).

    Returns the nominal winner, the probability that it is truly worse
    (``p_wrong``), expected regret (kg CO2e per tonne) and the ratio interval.
    ``robust`` is True if p_wrong <= 1 - confidence.
    """
    if boundary not in ("wtw", "ttw"):
        raise ValueError("boundary must be 'wtw' or 'ttw'")
    xa = a.kg_per_t_wtw if boundary == "wtw" else a.kg_per_t_ttw
    xb = b.kg_per_t_wtw if boundary == "wtw" else b.kg_per_t_ttw
    n = min(len(xa), len(xb))
    xa, xb = xa[:n], xb[:n]
    pa = (a.point_wtw_kg if boundary == "wtw" else a.point_ttw_kg) / a.payload_t
    pb = (b.point_wtw_kg if boundary == "wtw" else b.point_ttw_kg) / b.payload_t
    a_wins_nominal = pa <= pb
    chosen, other = (xa, xb) if a_wins_nominal else (xb, xa)
    p_wrong = float(np.mean(chosen > other))
    regret = float(np.mean(np.maximum(chosen - other, 0.0)))
    ratio = xa / xb
    lo, med, hi = np.percentile(ratio, [5, 50, 95])
    return dict(
        option_a=f"{a.scenario_name} [{a.level}]", option_b=f"{b.scenario_name} [{b.level}]",
        boundary=boundary,
        nominal_a_kg_per_t=float(pa), nominal_b_kg_per_t=float(pb),
        nominal_winner="A" if a_wins_nominal else "B",
        nominal_difference_pct=float(abs(pa - pb) / max(pa, pb) * 100.0),
        p_wrong=p_wrong, expected_regret_kg_per_t=regret,
        ratio_a_over_b_p5=float(lo), ratio_a_over_b_p50=float(med), ratio_a_over_b_p95=float(hi),
        robust=bool(p_wrong <= 1.0 - confidence))
