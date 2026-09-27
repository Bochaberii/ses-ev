from __future__ import annotations

from pydantic import BaseModel, Field


class FaultEntry(BaseModel):
    """Definition for a single fault condition in the EV diagnostic model."""

    code: str
    name: str
    severity: str
    description: str
    active: bool = False


class DiagnosticsState(BaseModel):
    """Typed structure for system-health and fault reporting."""

    active_faults: list[str] = []
    system_health: float = 100.0
    vcu_status: str = "READY"
    bms_status: str = "READY"
    motor_controller_status: str = "READY"
    communication_status: str = "OK"
    faults: list[FaultEntry] = []
