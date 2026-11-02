"""
test_thermostat_oop.py — Unit tests for Category 1 artifacts
CS 499 ePortfolio Enhancement
Run with: pytest tests/test_thermostat_oop.py -v
"""

import sys
import os
import json
import tempfile
from datetime import datetime

# Allow imports from thermostat-oop folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "thermostat-oop"))

from sensor import TemperatureSensor
from heater import Heater
from scheduler import Scheduler
from controller import ThermostatController, ThermostatState


# ---------------------------------------------------------------------------
# TemperatureSensor tests
# ---------------------------------------------------------------------------

class TestTemperatureSensor:
    def test_read_returns_float(self):
        sensor = TemperatureSensor(simulation_mode=True, base_temp=70.0)
        reading = sensor.read()
        assert isinstance(reading, float)

    def test_reading_near_base_temp(self):
        sensor = TemperatureSensor(simulation_mode=True, base_temp=70.0)
        reading = sensor.read()
        # Drift is ±0.5, so reading must be within 1 °F of base
        assert abs(reading - 70.0) <= 1.0

    def test_last_reading_updated(self):
        sensor = TemperatureSensor(simulation_mode=True, base_temp=65.0)
        sensor.read()
        assert sensor.last_reading is not None

    def test_set_simulated_temp(self):
        sensor = TemperatureSensor(simulation_mode=True, base_temp=70.0)
        sensor.set_simulated_temp(50.0)
        reading = sensor.read()
        assert abs(reading - 50.0) <= 1.0


# ---------------------------------------------------------------------------
# Heater tests
# ---------------------------------------------------------------------------

class TestHeater:
    def test_starts_off(self):
        heater = Heater(simulation_mode=True)
        assert heater.is_on is False

    def test_turn_on(self):
        heater = Heater(simulation_mode=True)
        heater.turn_on()
        assert heater.is_on is True

    def test_turn_off(self):
        heater = Heater(simulation_mode=True)
        heater.turn_on()
        heater.turn_off()
        assert heater.is_on is False

    def test_set_true(self):
        heater = Heater(simulation_mode=True)
        heater.set(True)
        assert heater.is_on is True

    def test_set_false(self):
        heater = Heater(simulation_mode=True)
        heater.turn_on()
        heater.set(False)
        assert heater.is_on is False


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

def _make_schedule_file(data: dict) -> str:
    """Write a temp schedule JSON file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    )
    json.dump(data, f)
    f.close()
    return f.name


SAMPLE_SCHEDULE = {
    "default_setpoint": 68,
    "schedule": {
        "monday": {"06": 70, "08": 68, "17": 72, "22": 65}
    }
}


class TestScheduler:
    def test_loads_default(self):
        path = _make_schedule_file(SAMPLE_SCHEDULE)
        s = Scheduler(path)
        assert s.default_setpoint == 68.0

    def test_floor_lookup_exact_hour(self):
        path = _make_schedule_file(SAMPLE_SCHEDULE)
        s = Scheduler(path)
        # 17:00 Monday → should return 72
        dt = datetime(2026, 11, 2, 17, 0)  # Monday
        assert s.get_setpoint(dt) == 72.0

    def test_floor_lookup_between_hours(self):
        path = _make_schedule_file(SAMPLE_SCHEDULE)
        s = Scheduler(path)
        # 09:30 Monday → falls between 08 and 17, should return 68
        dt = datetime(2026, 11, 2, 9, 30)
        assert s.get_setpoint(dt) == 68.0

    def test_before_first_rule_returns_default(self):
        path = _make_schedule_file(SAMPLE_SCHEDULE)
        s = Scheduler(path)
        # 03:00 Monday → before first rule (06), returns default
        dt = datetime(2026, 11, 2, 3, 0)
        assert s.get_setpoint(dt) == 68.0

    def test_missing_day_returns_default(self):
        path = _make_schedule_file(SAMPLE_SCHEDULE)
        s = Scheduler(path)
        # Tuesday not in schedule → returns default
        dt = datetime(2026, 11, 3, 12, 0)  # Tuesday
        assert s.get_setpoint(dt) == 68.0


# ---------------------------------------------------------------------------
# ThermostatController tests
# ---------------------------------------------------------------------------

class TestThermostatController:
    def _make_ctrl(self, base_temp: float, setpoint: float):
        schedule_data = {
            "default_setpoint": setpoint,
            "schedule": {}
        }
        path = _make_schedule_file(schedule_data)
        sensor = TemperatureSensor(simulation_mode=True, base_temp=base_temp)
        heater = Heater(simulation_mode=True)
        scheduler = Scheduler(path)
        return ThermostatController(sensor, heater, scheduler)

    def test_heat_on_when_cold(self):
        ctrl = self._make_ctrl(base_temp=60.0, setpoint=70.0)
        state = ctrl.tick()
        assert state.heat_on is True

    def test_heat_off_when_warm(self):
        ctrl = self._make_ctrl(base_temp=75.0, setpoint=70.0)
        state = ctrl.tick()
        assert state.heat_on is False

    def test_elapsed_increments(self):
        ctrl = self._make_ctrl(base_temp=65.0, setpoint=70.0)
        ctrl.tick()
        ctrl.tick()
        assert ctrl.elapsed == 2

    def test_uart_output_format(self):
        ctrl = self._make_ctrl(base_temp=65.0, setpoint=70.0)
        state = ctrl.tick()
        uart = state.to_uart()
        assert "Temp=" in uart
        assert "SetPoint=" in uart
        assert "Heat=" in uart
        assert "Elapsed=" in uart

    def test_run_limited_cycles(self):
        ctrl = self._make_ctrl(base_temp=65.0, setpoint=70.0)
        # Override tick_interval to 0 so test doesn't sleep
        ctrl._tick_interval = 0
        ctrl.run(cycles=5)
        assert ctrl.elapsed == 5
