from __future__ import annotations

from pydantic import BaseModel, Field


class VehicleStateModel(BaseModel):
    """Physical state of the vehicle body in the simulation snapshot."""

    state: str = Field(default="OFF")
    speed_kph: float = 0.0
    acceleration_mps2: float = 0.0
    distance_km: float = 0.0
    heading: float = 0.0


class DriverInput(BaseModel):
    """User-facing control inputs received by the backend via the API."""

    accelerator: float = Field(default=0.0, ge=0.0, le=100.0)
    brake: float = Field(default=0.0, ge=0.0, le=100.0)
    start: bool = False
    stop: bool = False
    charger_connected: bool = False
    fault_injection: str | None = None


class SimulationState(BaseModel):
    """Top-level snapshot shipped to the dashboard and API clients."""

    timestamp: float = 0.0
    vehicle: VehicleStateModel = VehicleStateModel()
    driver: DriverInput = DriverInput()
    battery: dict = {}
    motor: dict = {}
    energy: dict = {}
    charging: dict = {}
    diagnostics: dict = {}
    system_status: dict = {}
