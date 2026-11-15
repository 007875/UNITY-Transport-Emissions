"""UNITY v2 - Unified Model for Estimating Transport Emissions and Assessing Their Accuracy.

Research prototype. See README.md for scope and limitations.
"""
from .scenario import Vehicle, Trip, TransportScenario
from .unified import estimate, select_level, with_information, UnifiedResult
from .decision import compare

__all__ = ["Vehicle", "Trip", "TransportScenario", "estimate", "select_level",
           "with_information", "UnifiedResult", "compare"]
__version__ = "2.0.0"
