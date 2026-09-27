from __future__ import annotations


class BatteryModel:
    """Simplified battery pack model for the EV prototype.

    This is not an electrochemical cell model. It captures the vehicle-level
    behaviour needed for the simulation: SOC drift, current flow, charge and
    discharge power, and simple thermal effects. The model is intentionally easy
    to inspect and reason about for a beginner-friendly SDV prototype.
    """

    def __init__(self, capacity_kwh: float = 60.0, initial_soc: float = 80.0):
        self.capacity_kwh = capacity_kwh
        self.soc = initial_soc
        self.voltage = 360.0
        self.current = 0.0
        self.temperature = 30.0
        self.available_power_kw = 70.0
        self.charging_power_kw = 0.0
        self.status = "OK"
        self.active_faults = []

    def update(self, power_kw: float, dt: float, charging: bool = False):
        """Advance the battery state over a single simulation timestep.

        Positive power means the battery is supplying energy to the drivetrain.
        Negative power means energy is flowing back into the battery, such as from
        regenerative braking or an external charger. This convention matches the
        simplified energy balance used by the system.
        """
        if charging:
            self.charging_power_kw = max(0.0, min(50.0, abs(power_kw)))
            energy_change_kwh = self.charging_power_kw * dt / 3600.0
            # A simple percent-of-capacity update: charging adds energy to the pack
            # and the SOC rises until it reaches the upper bound of 100%.
            self.soc = min(100.0, self.soc + (energy_change_kwh / self.capacity_kwh) * 100.0)
            self.current = -self.charging_power_kw / max(self.voltage / 1000.0, 0.1)
            self.temperature = min(60.0, self.temperature + 0.02 * self.charging_power_kw)
            self.status = "CHARGING"
            return

        self.charging_power_kw = 0.0
        # Current is approximated from power and voltage using a simple electrical
        # relationship: P = V * I. In this prototype, the battery behaves like a
        # lumped 360 V source instead of a detailed equivalent-circuit model.
        self.current = power_kw / max(self.voltage / 1000.0, 0.1)

        if power_kw > 0:
            # Discharge: vehicle draws power from the pack. SOC drops according to
            # the proportion of energy consumed over the timestep.
            energy_change_percent = (abs(power_kw) * dt / 3600.0 / self.capacity_kwh) * 100.0
            self.soc = max(0.0, self.soc - energy_change_percent)
            self.temperature = min(60.0, self.temperature + 0.01 * abs(power_kw))
            self.status = "DISCHARGING"
        elif power_kw < 0:
            # Regeneration: power flows back into the battery. The code uses a
            # positive-energy recovery approach that reflects a simplified charge event.
            energy_change_percent = (abs(power_kw) * dt / 3600.0 / self.capacity_kwh) * 100.0
            self.soc = min(100.0, self.soc + energy_change_percent)
            self.temperature = min(60.0, self.temperature + 0.005 * abs(power_kw))
            self.status = "REGENERATING"
        else:
            self.status = "IDLE"

        self.available_power_kw = max(0.0, 100.0 - max(0.0, self.temperature - 30.0) * 1.5)

    def get_state(self):
        return {
            "soc": round(self.soc, 2),
            "voltage": round(self.voltage, 1),
            "current": round(self.current, 2),
            "temperature": round(self.temperature, 2),
            "power_kw": round(self.current * self.voltage / 1000.0, 2),
            "available_power_kw": round(self.available_power_kw, 2),
            "charging_power_kw": round(self.charging_power_kw, 2),
            "capacity_kwh": self.capacity_kwh,
            "status": self.status,
            "active_faults": self.active_faults,
        }
