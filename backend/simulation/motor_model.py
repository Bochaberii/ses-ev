from __future__ import annotations


class MotorModel:
    """Simplified traction motor model for the EV simulation.

    The code uses a basic torque-to-power relationship and converts vehicle speed
    into motor RPM using wheel radius assumptions. This is enough to demonstrate
    acceleration, drivetrain load, and regenerative braking in a beginner-friendly
    control architecture.
    """

    def __init__(self, max_torque_nm: float = 250.0, max_power_kw: float = 100.0):
        self.max_torque_nm = max_torque_nm
        self.max_power_kw = max_power_kw
        self.rpm = 0.0
        self.torque_nm = 0.0
        self.power_kw = 0.0
        self.temperature = 35.0
        self.requested_torque_nm = 0.0
        self.actual_torque_nm = 0.0
        self.status = "STANDBY"

    def update(self, requested_torque_nm: float, speed_kph: float, dt: float):
        # Convert vehicle speed from km/h into m/s so the wheel rotation can be
        # estimated using a simplified wheel-radius model.
        speed_mps = speed_kph / 3.6
        wheel_radius = 0.30
        wheel_rpm = (speed_mps / (2 * 3.14159 * wheel_radius)) * 60.0
        # The motor speed is approximated as a fixed multiplier of wheel speed to
        # reflect a gear reduction between wheel and electric machine.
        self.rpm = max(0.0, wheel_rpm * 4.0)

        torque_limit = self.max_torque_nm
        self.requested_torque_nm = max(-torque_limit, min(torque_limit, requested_torque_nm))
        self.actual_torque_nm = self.requested_torque_nm

        angular_speed_rad_s = self.rpm * 2 * 3.14159 / 60.0
        # Mechanical power is approximated as torque multiplied by angular speed.
        # A negative value represents regenerative power flow back into the battery.
        self.power_kw = (self.actual_torque_nm * angular_speed_rad_s) / 1000.0
        self.power_kw = max(-100.0, min(100.0, self.power_kw))

        self.temperature = min(110.0, self.temperature + 0.01 * abs(self.actual_torque_nm) * dt / 10.0)
        self.status = "RUNNING" if abs(self.actual_torque_nm) > 0 else "STANDBY"

        return self.actual_torque_nm

    def get_state(self):
        return {
            "rpm": round(self.rpm, 1),
            "torque_nm": round(self.actual_torque_nm, 2),
            "power_kw": round(self.power_kw, 2),
            "temperature": round(self.temperature, 2),
            "requested_torque_nm": round(self.requested_torque_nm, 2),
            "actual_torque_nm": round(self.actual_torque_nm, 2),
            "status": self.status,
        }
