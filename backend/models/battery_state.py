from __future__ import annotations

from pydantic import BaseModel, Field


class BatteryState(BaseModel):
    """Typed battery snapshot used to structure the simulation state."""

    soc: float = Field(default=80.0, ge=0.0, le=100.0)
    voltage: float = 360.0
    current: float = 0.0
    temperature: float = 30.0
    power_kw: float = 0.0
    available_power_kw: float = 0.0
    charging_power_kw: float = 0.0
    capacity_kwh: float = 60.0
    max_charge_power_kw: float = 50.0
    max_discharge_power_kw: float = 100.0
    status: str = "OK"
    active_faults: list[str] = []
