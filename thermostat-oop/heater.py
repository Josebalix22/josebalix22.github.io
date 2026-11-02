"""
heater.py — Thermostat OOP Port (Category 1: Software Design & Engineering)
CS 499 ePortfolio Enhancement
"""


class Heater:
    """
    Abstracts the heat output relay / LED.

    In production this wraps a GPIOZero LED or OutputDevice so that
    business logic never imports GPIO directly.  Swapping hardware
    (relay → PWM → simulated) only requires changing this class.
    """

    def __init__(self, simulation_mode: bool = True, gpio_pin: int = 17):
        """
        Args:
            simulation_mode: If True, track state in memory only.
            gpio_pin: BCM pin number for the relay/LED (Raspberry Pi).
        """
        self._simulation_mode = simulation_mode
        self._gpio_pin = gpio_pin
        self._is_on: bool = False
        self._hw_device = None

        if not simulation_mode:
            try:
                from gpiozero import LED  # type: ignore
                self._hw_device = LED(gpio_pin)
            except ImportError:
                raise RuntimeError(
                    "gpiozero is required for hardware mode. "
                    "Install it or use simulation_mode=True."
                )

    def turn_on(self) -> None:
        """Activate the heater / illuminate the heat LED."""
        self._is_on = True
        if self._hw_device:
            self._hw_device.on()

    def turn_off(self) -> None:
        """Deactivate the heater."""
        self._is_on = False
        if self._hw_device:
            self._hw_device.off()

    def set(self, state: bool) -> None:
        """Convenience method: True → on, False → off."""
        if state:
            self.turn_on()
        else:
            self.turn_off()

    @property
    def is_on(self) -> bool:
        return self._is_on

    def __repr__(self) -> str:
        return f"Heater(on={self._is_on}, pin={self._gpio_pin})"
