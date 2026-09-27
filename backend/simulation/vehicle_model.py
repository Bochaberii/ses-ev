from __future__ import annotations


class VehicleModel:
    """The simplified longitudinal vehicle dynamics model.

    This class converts drivetrain force into acceleration, then integrates that
    acceleration over time to estimate vehicle speed and distance. It models the
    dominant effects that matter for a beginner-level EV prototype: motor force,
    rolling resistance, drag, and brake force.
    """

    def __init__(
        self,
        mass_kg: float = 1500.0,
        wheel_radius_m: float = 0.30,
        max_motor_torque_nm: float = 250.0,
        max_motor_power_kw: float = 100.0,
    ):
        # Prototype assumptions for a compact EV. These values are intentionally
        # simple, visible, and easy to tune during experimentation.
        self.mass_kg = mass_kg
        self.wheel_radius_m = wheel_radius_m
        self.max_motor_torque_nm = max_motor_torque_nm
        self.max_motor_power_kw = max_motor_power_kw
        self.speed_kph = 0.0
        self.acceleration_mps2 = 0.0
        self.distance_km = 0.0
        self.energy_consumed_kwh = 0.0
        self.energy_recovered_kwh = 0.0
        self.net_energy_kwh = 0.0

    def update(self, motor_torque_nm: float, brake_percent: float, dt: float):
        # In a basic vehicle model, net force is the difference between traction and
        # resisting forces. This is the key relationship that translates motor output
        # into acceleration and then speed.
        mass = self.mass_kg
        rolling_resistance_n = 0.01 * mass * 9.81
        drag_coefficient = 0.3
        frontal_area_m2 = 2.2
        air_density = 1.225
        speed_mps = self.speed_kph / 3.6
        drag_force_n = 0.5 * air_density * drag_coefficient * frontal_area_m2 * speed_mps * speed_mps

        rolling_force_n = rolling_resistance_n
        brake_force_n = (brake_percent / 100.0) * 6000.0
        motor_force_n = (motor_torque_nm / self.wheel_radius_m) if speed_mps >= 0 else 0.0

        net_force_n = motor_force_n - rolling_force_n - drag_force_n - brake_force_n
        self.acceleration_mps2 = net_force_n / mass
        self.speed_kph = max(0.0, self.speed_kph + (self.acceleration_mps2 * dt * 3.6))
        self.distance_km += (self.speed_kph * dt / 3600.0)

        if self.speed_kph <= 0.0:
            self.speed_kph = 0.0
            self.acceleration_mps2 = 0.0

        return self.speed_kph

    def get_state(self):
        return {
            "speed_kph": round(self.speed_kph, 2),
            "acceleration_mps2": round(self.acceleration_mps2, 3),
            "distance_km": round(self.distance_km, 3),
            "energy_consumed_kwh": round(self.energy_consumed_kwh, 3),
            "energy_recovered_kwh": round(self.energy_recovered_kwh, 3),
            "net_energy_kwh": round(self.net_energy_kwh, 3),
        }
