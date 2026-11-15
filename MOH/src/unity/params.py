"""All numeric assumptions of the prototype in ONE place.

IMPORTANT - status of the numbers
---------------------------------
Every value below is a *placeholder assumption* chosen to be physically
plausible so that the modelling framework can be demonstrated.  None of them
has been validated here.  Before any result is used in a publication or a
decision, each value marked ASSUMPTION must be replaced by a value with a
citable source (e.g. GLEC Framework defaults, HBEFA, COPERT, manufacturer or
measurement data) - this is part of the planned PhD work (UNITY part 1).

Reporting boundary
------------------
TTW = tank-to-wheel (combustion).  WTT = well-to-tank (fuel supply chain).
WTW = TTW + WTT.  Results are reported as CO2e (CO2 + a small non-CO2 share).
"""

# --- fuel / emission factors (per litre of diesel) --------------------------
DIESEL_TTW_KG_CO2_PER_L = 2.628          # kept from v1; verify source (TTW CO2 only)
DIESEL_WTT_KG_CO2E_PER_L = 0.60          # ASSUMPTION placeholder (well-to-tank)
NON_CO2_FRACTION_OF_TTW = 0.003          # ASSUMPTION placeholder (CH4 + N2O share)
DIESEL_LHV_MJ_PER_L = 35.9               # approx. lower heating value

# --- vehicle classes ---------------------------------------------------------
# tare/capacity in tonnes; consumption in L/km at empty and at full payload.
# ASSUMPTION placeholders (plausible heavy-duty ranges, not validated).
VEHICLES = {
    "rigid_truck": dict(
        gvw_t=30.0, tare_t=12.0, payload_capacity_t=18.0,
        l_per_km_empty=0.25, l_per_km_full=0.36,
        cda_m2=5.5, crr=0.007, drivetrain_eff=0.90, engine_marginal_eff=0.40,
        baseline_l_per_h=3.0,
        hbefa4_class="HBEFA4/RT_gt28-32t_Euro-VI_A-C",
    ),
    "articulated_truck": dict(
        gvw_t=40.0, tare_t=15.0, payload_capacity_t=25.0,
        l_per_km_empty=0.28, l_per_km_full=0.42,
        cda_m2=6.5, crr=0.007, drivetrain_eff=0.90, engine_marginal_eff=0.40,
        baseline_l_per_h=3.5,
        hbefa4_class="HBEFA4/TT_AT_gt34-40t_Euro-VI_A-C",
    ),
}

# --- medium-data operational model (illustrative curve, NOT validated) -------
# relative consumption g(v) = A + B/v + C*v^2, normalised so that g(V_REF) = 1
V_REF_KMH = 70.0
G_A, G_B = 0.55, 6.0
G_C = (1.0 - G_A - G_B / V_REF_KMH) / V_REF_KMH ** 2
ROAD_FACTOR = {"motorway": 1.00, "rural": 1.05, "urban": 1.40}   # ASSUMPTION

# --- rail (low-data only; ASSUMPTION placeholders) ---------------------------
RAIL = dict(
    diesel_ttw_kg_co2e_per_tkm=0.022,
    electric_kwh_per_tkm=0.022,
    grid_kg_co2e_per_kwh=0.40,           # strongly country dependent
    sigma=0.25,                           # log-sd of the intensity
    grid_sigma=0.20,
)

# --- uncertainty assumptions (log-normal log-sd unless stated) --------------
# These describe how much we *do not know* at each data level.  They are
# assumptions, not measurements; the shape of the result (how interval width
# changes with data level) depends on them and must be calibrated against
# reference data in the research phase.
SIG = dict(
    base_consumption=0.18,     # generic class-level consumption (low, medium)
    conditions_low=0.12,       # unknown speed/road conditions (low only)
    curve_medium=0.07,         # speed/road curve error (medium)
    cda=0.08, crr=0.15, engine_eff=0.06, tare=0.05,   # physics parameters (high)
    model_high=0.06,           # residual model-form error (high)
    load_factor_sd=0.05,       # absolute sd of a *given* load factor
    ttw_ef=0.01, wtt_ef=0.20, non_co2=0.50,
)
DEFAULT_LOAD_FACTOR_TRIANGULAR = (0.30, 0.60, 0.90)   # used if load factor unknown

# --- physics ------------------------------------------------------------------
G = 9.81
RHO_AIR = 1.2
