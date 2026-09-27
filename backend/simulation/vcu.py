from __future__ import annotations

from .state_machine import VehicleState


class VCU:
    """Vehicle control unit for the prototype EV.

    The VCU acts as the safety gate between driver intent and drivetrain action.
    It decides whether propulsion, charging, or regenerative braking are allowed
    based on vehicle state, critical faults, and thermal/battery constraints.
    """

    def evaluate(
        self,
        accelerator: float,
        brake: float,
        vehicle_state: VehicleState,
        charger_connected: bool,
        battery_soc: float,
        battery_temp: float,
        motor_temp: float,
        active_faults: list[str],
        communication_failure: bool,
    ) -> dict:
        """Evaluate whether the drivetrain may move, charge, or recover energy.

        The return dictionary is intentionally simple: it exposes the current
        permission summary plus a brief status message, and the engine uses it to
        decide whether to request drive torque or enable regenerative braking.
        """
        critical_faults = {
            "HIGH_BATTERY_TEMPERATURE",
            "LOW_BATTERY_SOC",
            "MOTOR_OVERTEMPERATURE",
            "COMMUNICATION_FAILURE",
        }
        active_fault_set = set(active_faults)
        drive_allowed = (
            vehicle_state in {VehicleState.READY, VehicleState.DRIVING, VehicleState.REGENERATIVE_BRAKING}
            and not charger_connected
            and not communication_failure
            and not (active_fault_set & critical_faults)
            and battery_soc > 10
            and battery_temp < 60
            and motor_temp < 95
        )

        charging_allowed = (
            vehicle_state in {VehicleState.READY, VehicleState.CHARGING}
            and charger_connected
            and not communication_failure
            and not (active_fault_set & critical_faults)
            and battery_soc < 100
        )

        regenerative_braking = (
            vehicle_state in {VehicleState.DRIVING, VehicleState.REGENERATIVE_BRAKING}
            and brake > 0
            and accelerator == 0
            and not charger_connected
            and not communication_failure
            and not (active_fault_set & critical_faults)
        )

        return {
            "drive_allowed": drive_allowed,
            "charging_allowed": charging_allowed,
            "regenerative_braking": regenerative_braking,
            "requested_torque_nm": 0.0,
            "power_limit_kw": 100.0,
            "status": "READY",
            "reason": "Nominal operation" if drive_allowed else "Safety constraint active",
        }
