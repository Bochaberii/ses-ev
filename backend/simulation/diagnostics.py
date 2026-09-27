from __future__ import annotations


class Diagnostics:
    """Fault manager for the EV simulation.

    This class centralizes the fault dictionary and computes whether the system is
    in a degraded or unsafe state. The logic is intentionally threshold-based so
    it stays easy to understand and test while still representing common EV safety
    concerns such as overheating and low state of charge.
    """

    def __init__(self):
        self.faults = {
            "HIGH_BATTERY_TEMPERATURE": {
                "code": "HIGH_BATTERY_TEMPERATURE",
                "name": "High Battery Temperature",
                "severity": "HIGH",
                "description": "Battery temperature exceeds safe limits.",
                "active": False,
            },
            "LOW_BATTERY_SOC": {
                "code": "LOW_BATTERY_SOC",
                "name": "Low Battery SOC",
                "severity": "MEDIUM",
                "description": "Battery state of charge is critically low.",
                "active": False,
            },
            "MOTOR_OVERTEMPERATURE": {
                "code": "MOTOR_OVERTEMPERATURE",
                "name": "Motor Overtemperature",
                "severity": "HIGH",
                "description": "Motor temperature exceeds thermal limit.",
                "active": False,
            },
            "COMMUNICATION_FAILURE": {
                "code": "COMMUNICATION_FAILURE",
                "name": "Communication Failure",
                "severity": "HIGH",
                "description": "One or more vehicle subsystems lost communication.",
                "active": False,
            },
        }
        self.system_health = 100.0
        self.communication_status = "OK"

    def update(self, battery_temp: float, soc: float, motor_temp: float, communication_failure: bool):
        # The simulation defines a set of critical conditions that trigger a fault
        # response. These thresholds are deliberately simple but map directly to the
        # safety decisions used elsewhere in the VCU and state machine.
        self.faults["HIGH_BATTERY_TEMPERATURE"]["active"] = battery_temp > 55.0
        self.faults["LOW_BATTERY_SOC"]["active"] = soc < 10.0
        self.faults["MOTOR_OVERTEMPERATURE"]["active"] = motor_temp > 95.0
        self.faults["COMMUNICATION_FAILURE"]["active"] = communication_failure

        active = [code for code, entry in self.faults.items() if entry["active"]]
        self.system_health = max(0.0, 100.0 - len(active) * 20.0)
        self.communication_status = "FAULT" if communication_failure else "OK"

        return active

    def get_state(self):
        active_faults = [code for code, entry in self.faults.items() if entry["active"]]
        return {
            "active_faults": active_faults,
            "system_health": round(self.system_health, 1),
            "communication_status": self.communication_status,
            "faults": [
                {
                    "code": entry["code"],
                    "name": entry["name"],
                    "severity": entry["severity"],
                    "description": entry["description"],
                    "active": entry["active"],
                }
                for entry in self.faults.values()
            ],
        }
