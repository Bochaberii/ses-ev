from __future__ import annotations

import time

from .battery_model import BatteryModel
from .charging import ChargingSystem
from .diagnostics import Diagnostics
from .motor_model import MotorModel
from .state_machine import StateMachine, VehicleState
from .vehicle_model import VehicleModel
from .vcu import VCU


class SimulationEngine:
    def __init__(self):
        self.state_machine = StateMachine()
        self.vehicle_model = VehicleModel()
        self.battery = BatteryModel()
        self.motor = MotorModel()
        self.charger = ChargingSystem()
        self.diagnostics = Diagnostics()
        self.vcu = VCU()

        self.driver_inputs = {"accelerator": 0.0, "brake": 0.0}
        self.current_state = VehicleState.OFF
        self.running = False
        self.active_faults = []
        self.communication_failure = False
        self.start_time = time.time()
        self.last_tick = time.time()
        self.last_broadcast = time.time()
        self.history = {"speed_kph": [], "soc": [], "battery_power_kw": []}

    def apply_driver_inputs(self, accelerator: float = 0.0, brake: float = 0.0, charger_connected: bool = False):
        self.driver_inputs["accelerator"] = max(0.0, min(100.0, accelerator))
        self.driver_inputs["brake"] = max(0.0, min(100.0, brake))
        self.charger.connected = charger_connected

    def set_fault(self, fault_name: str):
        if fault_name == "COMMUNICATION_FAILURE":
            self.communication_failure = True
        else:
            self.active_faults = list(dict.fromkeys(self.active_faults + [fault_name]))

    def clear_fault(self, fault_name: str):
        if fault_name == "COMMUNICATION_FAILURE":
            self.communication_failure = False
        else:
            self.active_faults = [fault for fault in self.active_faults if fault != fault_name]

    def reset(self):
        self.state_machine = StateMachine()
        self.vehicle_model = VehicleModel()
        self.battery = BatteryModel()
        self.motor = MotorModel()
        self.charger = ChargingSystem()
        self.diagnostics = Diagnostics()
        self.current_state = VehicleState.OFF
        self.running = False
        self.active_faults = []
        self.communication_failure = False
        self.driver_inputs = {"accelerator": 0.0, "brake": 0.0}
        self.history = {"speed_kph": [], "soc": [], "battery_power_kw": []}

    def tick(self, dt: float = 0.1):
        accelerator = self.driver_inputs["accelerator"]
        brake = self.driver_inputs["brake"]
        charger_connected = self.charger.connected

        if self.current_state == VehicleState.OFF:
            self.current_state = VehicleState.INITIALIZING

        if self.current_state == VehicleState.FAULT:
            # Fault state is held until cleared externally.
            if not self.active_faults and not self.communication_failure:
                self.current_state = VehicleState.READY

        potential_faults = set(self.active_faults)
        if self.communication_failure:
            potential_faults.add("COMMUNICATION_FAILURE")
        if self.battery.temperature > 55:
            potential_faults.add("HIGH_BATTERY_TEMPERATURE")
        if self.battery.soc < 10:
            potential_faults.add("LOW_BATTERY_SOC")
        if self.motor.temperature > 95:
            potential_faults.add("MOTOR_OVERTEMPERATURE")

        self.active_faults = sorted(potential_faults)

        if self.active_faults or self.communication_failure:
            self.current_state = VehicleState.FAULT

        self.current_state = self.state_machine.update(
            current_state=self.current_state,
            accelerator=accelerator,
            brake=brake,
            speed_kph=self.vehicle_model.speed_kph,
            charger_connected=charger_connected,
            critical_fault_active=bool(self.active_faults or self.communication_failure),
        )

        if self.current_state == VehicleState.CHARGING:
            self.charger.update(dt, vehicle_stationary=self.vehicle_model.speed_kph <= 0.0)
            self.battery.update(power_kw=self.charger.charging_power_kw, dt=dt, charging=True)
          
        else:
            vcu_decision = self.vcu.evaluate(
                accelerator=accelerator,
                brake=brake,
                vehicle_state=self.current_state,
                charger_connected=charger_connected,
                battery_soc=self.battery.soc,
                battery_temp=self.battery.temperature,
                motor_temp=self.motor.temperature,
                active_faults=self.active_faults,
                communication_failure=self.communication_failure,
            )

            if self.current_state in {VehicleState.DRIVING, VehicleState.REGENERATIVE_BRAKING}:
                if vcu_decision["regenerative_braking"] or brake > 0:
                    self.current_state = VehicleState.REGENERATIVE_BRAKING
                    requested_torque = -min(200.0, brake * 2.8)
                else:
                    requested_torque = (accelerator / 100.0) * 220.0
            else:
                requested_torque = (accelerator / 100.0) * 180.0 if accelerator > 0 else 0.0

            if self.current_state == VehicleState.READY and charger_connected:
                self.current_state = VehicleState.CHARGING

            if self.current_state == VehicleState.FAULT:
                requested_torque = 0.0

            self.motor.update(requested_torque, self.vehicle_model.speed_kph, dt)

            if self.current_state == VehicleState.REGENERATIVE_BRAKING:
                power_kw = -max(0.0, self.motor.actual_torque_nm * self.motor.rpm * 2 * 3.14159 / 60.0 / 1000.0)
                self.battery.update(power_kw=power_kw, dt=dt, charging=False)
                self.vehicle_model.energy_recovered_kwh += max(0.0, abs(power_kw) * dt / 3600.0) * 0.35
                self.vehicle_model.speed_kph = max(0.0, self.vehicle_model.speed_kph - (brake / 100.0) * 25.0 * dt)
            elif self.current_state == VehicleState.DRIVING:
                power_kw = max(0.0, self.motor.power_kw)
                self.battery.update(power_kw=power_kw, dt=dt, charging=False)
                self.vehicle_model.energy_consumed_kwh += power_kw * dt / 3600.0
                self.vehicle_model.net_energy_kwh = self.vehicle_model.energy_consumed_kwh - self.vehicle_model.energy_recovered_kwh
            else:
                self.battery.update(power_kw=0.0, dt=dt, charging=False)

            self.vehicle_model.update(
                motor_torque_nm=self.motor.actual_torque_nm,
                brake_percent=brake,
                dt=dt,
            )

        self.diagnostics.update(
            battery_temp=self.battery.temperature,
            soc=self.battery.soc,
            motor_temp=self.motor.temperature,
            communication_failure=self.communication_failure,
        )

        if self.current_state == VehicleState.READY and self.charger.connected:
            self.current_state = VehicleState.CHARGING

        if self.current_state == VehicleState.CHARGING and not self.charger.connected:
            self.current_state = VehicleState.READY

        self.battery.available_power_kw = max(0.0, 100.0 - max(0.0, self.battery.temperature - 30.0) * 1.3)
        self.history["speed_kph"].append(self.vehicle_model.speed_kph)
        self.history["soc"].append(self.battery.soc)
        self.history["battery_power_kw"].append(self.battery.power_kw if hasattr(self.battery, 'power_kw') else 0.0)

        return self.get_state()

    def get_state(self):
        health = self.diagnostics.get_state()
        state = {
            "timestamp": time.time() - self.start_time,
            "vehicle": {
                "state": self.current_state.value,
                "speed_kph": round(self.vehicle_model.speed_kph, 2),
                "acceleration_mps2": round(self.vehicle_model.acceleration_mps2, 3),
                "distance_km": round(self.vehicle_model.distance_km, 3),
            },
            "driver": {
                "accelerator": round(self.driver_inputs["accelerator"], 2),
                "brake": round(self.driver_inputs["brake"], 2),
                "charger_connected": self.charger.connected,
            },
            "battery": {
                **self.battery.get_state(),
                "available_power_kw": round(self.battery.available_power_kw, 2),
                "power_kw": round(self.battery.current * self.battery.voltage / 1000.0, 2),
            },
            "motor": self.motor.get_state(),
            "energy": {
                "energy_consumed_kwh": round(self.vehicle_model.energy_consumed_kwh, 3),
                "energy_recovered_kwh": round(self.vehicle_model.energy_recovered_kwh, 3),
                "net_energy_consumed_kwh": round(self.vehicle_model.net_energy_kwh, 3),
            },
            "charging": self.charger.get_state(),
            "diagnostics": health,
            "system_status": {
                "vcu_status": "READY" if not self.active_faults else "FAULT",
                "bms_status": self.battery.status,
                "motor_controller_status": self.motor.status,
                "communication_status": "FAULT" if self.communication_failure else "OK",
            },
        }
        return state
