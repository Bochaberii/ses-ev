from __future__ import annotations

from enum import Enum


class VehicleState(str, Enum):
    """High-level operating modes for the simplified EV controller.

    These states represent the vehicle lifecycle in the prototype: startup,
    readiness, motion, charging, regenerative braking, and fault response.
    """

    OFF = "OFF"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    DRIVING = "DRIVING"
    REGENERATIVE_BRAKING = "REGENERATIVE_BRAKING"
    CHARGING = "CHARGING"
    FAULT = "FAULT"


class StateMachine:
    """Enforce the EV state transitions used throughout the simulation.

    The state machine is intentionally simple: it ensures that propulsion, charging,
    and regenerative braking happen only in compatible system states and that a
    critical fault forces the vehicle into a safe mode.
    """

    def __init__(self):
        self.state = VehicleState.OFF

    def update(
        self,
        current_state: VehicleState,
        accelerator: float,
        brake: float,
        speed_kph: float,
        charger_connected: bool,
        critical_fault_active: bool,
    ) -> VehicleState:
        """Return the next state after evaluating driver inputs and powertrain conditions.

        A critical fault takes precedence over all other transitions. This is the
        safety gate that prevents the vehicle from continuing normal operation in
        an unsafe condition.
        """
        state = current_state

        if critical_fault_active:
            return VehicleState.FAULT

        if state in (VehicleState.OFF, VehicleState.FAULT):
            if state == VehicleState.OFF:
                state = VehicleState.INITIALIZING
            elif state == VehicleState.FAULT:
                state = VehicleState.READY
            return state

        if state == VehicleState.INITIALIZING:
            state = VehicleState.READY
            return state

        if state == VehicleState.READY:
            # A charger-connected vehicle is treated as charging before it can be
            # commanded to drive. This prevents propulsion while plugged in.
            if charger_connected:
                return VehicleState.CHARGING
            if accelerator > 0 and speed_kph >= 0:
                return VehicleState.DRIVING
            return VehicleState.READY

        if state == VehicleState.DRIVING:
            # Regenerative braking is prioritized when the driver is braking and the
            # vehicle is already moving. This is the main handoff between drive and
            # energy recovery modes.
            if brake > 0 and speed_kph > 0:
                return VehicleState.REGENERATIVE_BRAKING
            if speed_kph <= 0:
                return VehicleState.READY
            return VehicleState.DRIVING

        if state == VehicleState.REGENERATIVE_BRAKING:
            if brake <= 0 or speed_kph <= 0:
                return VehicleState.READY if speed_kph <= 0 else VehicleState.DRIVING
            return VehicleState.REGENERATIVE_BRAKING

        if state == VehicleState.CHARGING:
            if not charger_connected:
                return VehicleState.READY
            return VehicleState.CHARGING

        return state

    def apply_transition(self, current_state: VehicleState, **kwargs) -> VehicleState:
        """Compatibility helper used by the project for direct transition evaluation."""
        return self.update(current_state, **kwargs)
