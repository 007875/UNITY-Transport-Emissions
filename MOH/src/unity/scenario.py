"""Scenario objects. Optional fields describe *which data are available*."""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Optional, Sequence
from . import params as P

ROAD_TYPES = ("motorway", "rural", "urban")


@dataclass
class Vehicle:
    vehicle_class: str                       # key of params.VEHICLES, or "rail"
    fuel_type: str = "diesel"
    euro_class: Optional[str] = "Euro VI"
    load_factor: Optional[float] = None      # share of PAYLOAD CAPACITY (not of GVW)
    traction: str = "diesel"                 # rail only: "diesel" | "electric"

    def spec(self) -> dict:
        if self.vehicle_class not in P.VEHICLES:
            raise ValueError(f"Unsupported road vehicle class: {self.vehicle_class!r}. "
                             f"Supported: {sorted(P.VEHICLES)}")
        return P.VEHICLES[self.vehicle_class]


@dataclass
class Trip:
    distance_km: float
    average_speed_kmh: Optional[float] = None
    road_type: Optional[str] = None
    speed_trace_kmh: Optional[Sequence[float]] = None     # 1 Hz speed trajectory


@dataclass
class TransportScenario:
    name: str
    mode: str                                 # "road" | "rail"
    vehicle: Vehicle
    trip: Trip
    shipment_tonnes: Optional[float] = None   # needed for rail

    def validate(self) -> None:
        if self.mode not in ("road", "rail"):
            raise ValueError("mode must be 'road' or 'rail'")
        if self.trip.distance_km <= 0:
            raise ValueError("distance_km must be > 0")
        lf = self.vehicle.load_factor
        if lf is not None and not (0 < lf <= 1):
            raise ValueError("load_factor must be in (0, 1]")
        if self.mode == "road":
            if self.vehicle.fuel_type.lower() != "diesel":
                raise ValueError("Only diesel road vehicles are supported in v2")
            self.vehicle.spec()
            rt = self.trip.road_type
            if rt is not None and rt not in ROAD_TYPES:
                raise ValueError(f"road_type must be one of {ROAD_TYPES}")
        else:
            if not self.shipment_tonnes or self.shipment_tonnes <= 0:
                raise ValueError("rail scenarios need shipment_tonnes > 0")
            if self.vehicle.traction not in ("diesel", "electric"):
                raise ValueError("traction must be 'diesel' or 'electric'")

    def payload_tonnes(self, load_factor: Optional[float] = None) -> float:
        """Payload = payload CAPACITY x load factor (v1 wrongly used GVW)."""
        if self.mode == "rail":
            return float(self.shipment_tonnes)
        lf = self.vehicle.load_factor if load_factor is None else load_factor
        if lf is None:
            lf = P.DEFAULT_LOAD_FACTOR_TRIANGULAR[1]
        return self.vehicle.spec()["payload_capacity_t"] * lf

    def copy(self, **kw) -> "TransportScenario":
        return replace(self, **kw)
