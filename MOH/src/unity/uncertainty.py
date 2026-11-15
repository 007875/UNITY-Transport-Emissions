"""Small helpers to summarise Monte-Carlo samples."""
import numpy as np


def summarize(x) -> dict:
    x = np.asarray(x, dtype=float)
    p5, p50, p95 = np.percentile(x, [5, 50, 95])
    return dict(p5=float(p5), p50=float(p50), p95=float(p95), mean=float(x.mean()),
                rel_half_width=float((p95 - p5) / (2.0 * p50)) if p50 else float("nan"))
