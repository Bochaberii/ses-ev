from __future__ import annotations

from pydantic import BaseModel, Field


class MotorState(BaseModel):
    """Typed representation of the electric motor operating condition."""

    rpm: float = 0.0
    torque_nm: float = 0.0
    power_kw: float = 0.0
    temperature: float = 35.0
    requested_torque_nm: float = 0.0
    actual_torque_nm: float = 0.0
    status: str = "STANDBY"
