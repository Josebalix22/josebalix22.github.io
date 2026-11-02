"""
sensor.py — Thermostat OOP Port (Category 1: Software Design & Engineering)
CS 499 ePortfolio Enhancement
Original artifact: CS 350 Raspberry Pi thermostat (Python/GPIOZero)
Enhancement: Refactored into object-oriented architecture with dependency injection
"""

import random


class TemperatureSensor:
    """
    Abstracts temperature reading from a hardware sensor.

    In production this would wrap a real I2C/SPI sensor library
    (e.g. Adafruit CircuitPython TMP006 or DS18B20).
    In simulation mode it returns a configurable mock value so the
    rest of the system can be unit-tested without physical hardware.
    """

    def __init__(self, simulation_mode: bool = True, base_temp: float = 68.0):
        """
        Args:
            simulation_mode: If True, return synthetic readings instead of
                             querying real hardware.
            base_temp: Starting temperature for simulation (Fahrenheit).
        """
        self._simulation_mode = simulation_mode
        self._base_temp = base_temp
        self._last_reading: float = base_temp

    def read(self) -> float:
        """
        Return current temperature in Fahrenheit.

        Simulation adds ±0.5 °F of random drift each call to mimic a
        real sensor; real hardware would replace this body with an
        actual register read.
        """
        if self._simulation_mode:
            drift = random.uniform(-0.5, 0.5)
            self._last_reading = round(self._base_temp + drift, 1)
        else:
            # Replace with real hardware read, e.g.:
            # self._last_reading = self._hw_sensor.temperature * 9/5 + 32
            pass
        return self._last_reading

    def set_simulated_temp(self, temp: float) -> None:
        """Adjust the simulated base temperature (for testing)."""
        self._base_temp = temp

    @property
    def last_reading(self) -> float:
        return self._last_reading
