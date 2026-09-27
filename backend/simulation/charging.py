from __future__ import annotations


class ChargingSystem:
    """Represents the vehicle's charger connection and charge delivery.

    The prototype models a single fixed-power charger. It does not try to model a
    full AC/DC converter, negotiation protocol, or battery-management charger
    communication stack; it focuses on whether charging is allowed and how much
    energy flows into the battery while the vehicle is stationary.
    """

    def __init__(self):
        self.connected = False
        self.charging_power_kw = 0.0
        self.energy_delivered_kwh = 0.0
        self.status = "DISCONNECTED"

    def connect(self):
        self.connected = True
        self.status = "CONNECTED"
        self.charging_power_kw = 50.0

    def disconnect(self):
        self.connected = False
        self.status = "DISCONNECTED"
        self.charging_power_kw = 0.0

    def update(self, dt: float, vehicle_stationary: bool):
        # Charging is only allowed while the vehicle is effectively at rest. This
        # matches the safety logic used throughout the simulation.
        if self.connected and vehicle_stationary:
            self.status = "CHARGING"
            self.charging_power_kw = 50.0
            self.energy_delivered_kwh += self.charging_power_kw * dt / 3600.0
        else:
            self.status = "WAITING" if self.connected else "DISCONNECTED"
            self.charging_power_kw = 0.0

    def get_state(self):
        return {
            "connected": self.connected,
            "charging_power_kw": round(self.charging_power_kw, 2),
            "energy_delivered_kwh": round(self.energy_delivered_kwh, 3),
            "status": self.status,
        }
