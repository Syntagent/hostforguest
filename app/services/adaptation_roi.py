"""
Transparent ROI helpers for adaptation projects (indicative only).

Formula (documented for UI tooltips):
- baseline_nights_year = 365 * (occupancy_0_1)  OR explicit nights_per_year if provided
- baseline_revenue_year = adr * baseline_nights_year
- uplift_rate: combined effect of % ADR increase and % occupancy increase:
  new_adr = adr * (1 + adr_uplift_pct/100)
  new_occ = min(1.0, occ * (1 + occ_uplift_pct/100))  # cap at 100%
  new_revenue_year = new_adr * (365 * new_occ)
  incremental_revenue_year = max(0, new_revenue_year - baseline_revenue_year)

Alternatively extra_eur_per_night adds (extra_eur_per_night * baseline_nights_year) to incremental.

simple_payback_months = (investment_mid_eur / (incremental_revenue_year / 12)) if incremental > 0 else None
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def compute_adaptation_roi(inputs: Dict[str, Any], investment_mid_eur: float) -> Dict[str, Any]:
    """
    Pure function for tests and API. All monetary values in EUR.
    """
    adr = float(inputs.get("adr") or 0)
    occupancy_pct = float(inputs.get("occupancy_pct") or 0)
    if occupancy_pct > 1.0:
        occ = min(1.0, occupancy_pct / 100.0)
    else:
        occ = min(1.0, max(0.0, occupancy_pct))

    nights_explicit = inputs.get("nights_per_year")
    if nights_explicit is not None:
        baseline_nights = float(nights_explicit)
    else:
        baseline_nights = 365.0 * occ

    baseline_revenue_year = adr * baseline_nights

    adr_uplift = float(inputs.get("adr_uplift_pct") or 0)
    occ_uplift = float(inputs.get("occ_uplift_pct") or 0)
    extra_per_night = float(inputs.get("extra_eur_per_night") or 0)

    new_adr = adr * (1.0 + adr_uplift / 100.0)
    new_occ = min(1.0, occ * (1.0 + occ_uplift / 100.0)) if occ_uplift else occ

    if nights_explicit is None:
        new_nights = 365.0 * new_occ
    else:
        new_nights = baseline_nights * (new_occ / occ) if occ > 0 else baseline_nights * new_occ
    new_revenue_year = new_adr * new_nights + extra_per_night * new_nights

    incremental_year = max(0.0, new_revenue_year - baseline_revenue_year)
    incremental_month = incremental_year / 12.0

    payback_months: Optional[float] = None
    if incremental_month > 0 and investment_mid_eur > 0:
        payback_months = investment_mid_eur / incremental_month

    return {
        "baseline_nights_year": round(baseline_nights, 2),
        "baseline_revenue_year": round(baseline_revenue_year, 2),
        "projected_revenue_year": round(new_revenue_year, 2),
        "incremental_revenue_year": round(incremental_year, 2),
        "incremental_revenue_month": round(incremental_month, 2),
        "simple_payback_months": round(payback_months, 2) if payback_months is not None else None,
        "disclaimer": "Indicative only — not financial advice. Verify with your bookings data.",
    }


def bom_totals(bom_lines: list) -> Tuple[float, float]:
    """Sum min/max from list of dicts with keys cost_min_eur, cost_max_eur (or mid)."""
    tmin = 0.0
    tmax = 0.0
    for line in bom_lines:
        if not isinstance(line, dict):
            continue
        cm = float(line.get("cost_min_eur") or line.get("cost_mid_eur") or 0)
        cx = float(line.get("cost_max_eur") or line.get("cost_mid_eur") or cm)
        tmin += cm
        tmax += cx
    return tmin, tmax
