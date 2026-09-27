from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.simulation.simulation_engine import SimulationEngine
from backend.simulation.state_machine import VehicleState

router = APIRouter(prefix="/api")
engine = SimulationEngine()


class DriverCommand(BaseModel):
    """Validated driver inputs sent by the dashboard.

    These values represent the human-facing controls for accelerator, brake, and
    charger connection state. The thresholds are intentionally simple and keep the
    frontend/backend interface easy to inspect and test.
    """

    accelerator: float = Field(default=0.0, ge=0.0, le=100.0)
    brake: float = Field(default=0.0, ge=0.0, le=100.0)
    charger_connected: bool = False


class FaultCommand(BaseModel):
    """Request to inject or clear a named fault in the simulation."""

    fault: str


class ConnectionManager:
    """Track WebSocket clients and broadcast the latest vehicle state to each one.

    The live dashboard relies on this channel for real-time updates without the
    frontend having to poll the API every few milliseconds.
    """

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a frontend client and keep it in the active connection list."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected client from the active list."""
        self.active_connections = [client for client in self.active_connections if client != websocket]

    async def broadcast(self, message: dict):
        """Send the latest simulation state to every connected dashboard client."""
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


@router.get("/state")
async def get_state():
    """Return the full simulation snapshot used by the dashboard."""
    return engine.get_state()


@router.post("/start")
async def start_vehicle():
    """Start the simulation loop and initialize the vehicle in a safe startup state."""
    engine.running = True
    engine.current_state = VehicleState.INITIALIZING
    engine.apply_driver_inputs(accelerator=0.0, brake=0.0, charger_connected=False)
    return engine.get_state()


@router.post("/stop")
async def stop_vehicle():
    engine.running = False
    engine.current_state = VehicleState.OFF
    engine.apply_driver_inputs(accelerator=0.0, brake=0.0, charger_connected=False)
    return engine.get_state()


@router.post("/reset")
async def reset_vehicle():
    engine.reset()
    return engine.get_state()


@router.post("/inputs")
async def update_inputs(command: DriverCommand):
    engine.running = True
    engine.apply_driver_inputs(
        accelerator=command.accelerator,
        brake=command.brake,
        charger_connected=command.charger_connected,
    )
    return engine.get_state()


@router.post("/charger/connect")
async def connect_charger():
    engine.running = True
    engine.charger.connect()
    engine.apply_driver_inputs(accelerator=0.0, brake=0.0, charger_connected=True)
    return engine.get_state()


@router.post("/charger/disconnect")
async def disconnect_charger():
    engine.charger.disconnect()
    engine.apply_driver_inputs(accelerator=0.0, brake=0.0, charger_connected=False)
    return engine.get_state()


@router.post("/fault")
async def inject_fault(command: FaultCommand):
    if not command.fault:
        raise HTTPException(status_code=400, detail="Fault name is required.")
    engine.running = True
    engine.set_fault(command.fault)
    return engine.get_state()


@router.post("/fault/clear")
async def clear_fault(command: FaultCommand):
    if not command.fault:
        raise HTTPException(status_code=400, detail="Fault name is required.")
    engine.clear_fault(command.fault)
    return engine.get_state()


@router.websocket("/ws")
async def vehicle_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
