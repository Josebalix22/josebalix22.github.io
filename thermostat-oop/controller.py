"""
controller.py — Thermostat OOP Port (Category 1: Software Design & Engineering)
CS 499 ePortfolio Enhancement

ThermostatController ties together Sensor, Heater, and Scheduler into
the main state machine that mirrors the original Raspberry Pi project's
control loop, now expressed as a clean, testable class.
"""

import time
from datetime import datetime
from typing import Optional

from sensor import TemperatureSensor
from heater import Heater
from scheduler import Scheduler


class ThermostatState:
    """Immutable snapshot of the thermostat at one point in time."""
    __slots__ = ("timestamp", "current_temp", "set_point", "heat_on", "elapsed")

    def __init__(self, current_temp: float, set_point: float,
                 heat_on: bool, elapsed: int):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_temp = current_temp
        self.set_point = set_point
        self.heat_on = heat_on
        self.elapsed = elapsed

    def to_uart(self) -> str:
        """Format a UART-style log line matching the original project output."""
        status = "ON " if self.heat_on else "OFF"
        return (
            f"[{self.timestamp}] "
            f"Temp={self.current_temp:.1f}F  "
            f"SetPoint={self.set_point:.1f}F  "
            f"Heat={status}  "
            f"Elapsed={self.elapsed}s"
        )


class ThermostatController:
    """
    Main state machine for the thermostat.

    Orchestrates Sensor → decision logic → Heater output, and logs
    each cycle in UART format.  The 1-second tick matches the hardware
    timer interval from the original embedded project.
    """

    def __init__(
        self,
        sensor: TemperatureSensor,
        heater: Heater,
        scheduler: Scheduler,
        tick_interval: float = 1.0,
    ):
        self._sensor = sensor
        self._heater = heater
        self._scheduler = scheduler
        self._tick_interval = tick_interval
        self._elapsed: int = 0
        self._running: bool = False
        self._last_state: Optional[ThermostatState] = None

    def tick(self, at: datetime = None) -> ThermostatState:
        """
        Execute one control cycle.

        Reads the sensor, gets the active set-point, updates the
        heater, and returns the current state snapshot.
        """
        current_temp = self._sensor.read()
        set_point = self._scheduler.get_setpoint(at)

        # State machine: heat ON when temp is below set-point
        heat_on = current_temp < set_point
        self._heater.set(heat_on)
        self._elapsed += 1

        state = ThermostatState(current_temp, set_point, heat_on, self._elapsed)
        self._last_state = state
        return state

    def run(self, cycles: int = None) -> None:
        """
        Run the control loop.

        Args:
            cycles: Number of ticks before stopping.  None = run until
                    interrupted with Ctrl-C.
        """
        self._running = True
        count = 0
        print("Thermostat started. Press Ctrl-C to stop.")
        try:
            while self._running:
                state = self.tick()
                print(state.to_uart())
                count += 1
                if cycles is not None and count >= cycles:
                    break
                time.sleep(self._tick_interval)
        except KeyboardInterrupt:
            pass
        finally:
            self._heater.turn_off()
            print("Thermostat stopped.")

    def stop(self) -> None:
        self._running = False

    @property
    def last_state(self) -> Optional[ThermostatState]:
        return self._last_state

    @property
    def elapsed(self) -> int:
        return self._elapsed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Raspberry Pi Thermostat Simulation")
    parser.add_argument("--schedule", default="schedule.json",
                        help="Path to weekly schedule JSON file")
    parser.add_argument("--temp", type=float, default=68.0,
                        help="Simulated starting temperature (°F)")
    parser.add_argument("--cycles", type=int, default=None,
                        help="Number of cycles to run (default: infinite)")
    args = parser.parse_args()

    sensor = TemperatureSensor(simulation_mode=True, base_temp=args.temp)
    heater = Heater(simulation_mode=True)
    scheduler = Scheduler(schedule_path=args.schedule)
    ctrl = ThermostatController(sensor, heater, scheduler)
    ctrl.run(cycles=args.cycles)
