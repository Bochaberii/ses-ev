from backend.simulation.state_machine import VehicleState, StateMachine
from backend.simulation.vcu import VCU


def test_state_machine_ready_to_driving():
    machine = StateMachine()
    state = machine.update(
        current_state=VehicleState.OFF,
        accelerator=0,
        brake=0,
        speed_kph=0,
        charger_connected=False,
        critical_fault_active=False,
    )
    assert state == VehicleState.INITIALIZING

    state = machine.update(
        current_state=VehicleState.INITIALIZING,
        accelerator=0,
        brake=0,
        speed_kph=0,
        charger_connected=False,
        critical_fault_active=False,
    )
    assert state == VehicleState.READY

    state = machine.update(
        current_state=VehicleState.READY,
        accelerator=70,
        brake=0,
        speed_kph=5,
        charger_connected=False,
        critical_fault_active=False,
    )
    assert state == VehicleState.DRIVING


def test_vcu_blocks_drive_on_fault():
    vcu = VCU()
    decision = vcu.evaluate(
        accelerator=50,
        brake=0,
        vehicle_state=VehicleState.READY,
        charger_connected=False,
        battery_soc=25,
        battery_temp=42,
        motor_temp=70,
        active_faults=["HIGH_BATTERY_TEMPERATURE"],
        communication_failure=False,
    )
    assert decision["drive_allowed"] is False
    assert decision["charging_allowed"] is False


def test_vcu_allows_regenerative_braking_when_safe():
    vcu = VCU()
    decision = vcu.evaluate(
        accelerator=0,
        brake=40,
        vehicle_state=VehicleState.DRIVING,
        charger_connected=False,
        battery_soc=80,
        battery_temp=35,
        motor_temp=60,
        active_faults=[],
        communication_failure=False,
    )
    assert decision["regenerative_braking"] is True
