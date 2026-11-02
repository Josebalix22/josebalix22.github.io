"""
scheduler.py — Thermostat OOP Port (Category 1: Software Design & Engineering)
CS 499 ePortfolio Enhancement

Reads a JSON schedule file and returns the active set-point for any
datetime, replacing the manual button-press workflow from the original
Raspberry Pi project.
"""

import json
from datetime import datetime
from pathlib import Path


class Scheduler:
    """
    Manages time-based temperature set-point rules loaded from JSON.

    The JSON file defines per-day, per-hour set-points.  The scheduler
    performs a floor lookup: for any given hour, it finds the highest
    scheduled hour that is ≤ the current hour and returns that set-point.

    Example schedule.json entry:
        "monday": { "06": 70, "08": 68, "17": 72, "22": 65 }

    At 09:30 on Monday the active set-point is 68 (the 08:00 rule).
    """

    def __init__(self, schedule_path: str = "schedule.json"):
        self._default: float = 68.0
        self._schedule: dict = {}
        self._load(schedule_path)

    def _load(self, path: str) -> None:
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Schedule file not found: {path}. "
                "Create a schedule.json or pass a valid path."
            )
        with open(config_path) as f:
            data = json.load(f)
        self._default = float(data.get("default_setpoint", 68.0))
        raw = data.get("schedule", {})
        # Normalize: keys are day names (lower), values are {int_hour: float_temp}
        self._schedule = {
            day.lower(): {int(h): float(t) for h, t in hours.items()}
            for day, hours in raw.items()
        }

    def get_setpoint(self, at: datetime = None) -> float:
        """
        Return the active set-point for the given datetime.

        Args:
            at: The datetime to evaluate.  Defaults to now.

        Returns:
            Temperature in Fahrenheit.
        """
        if at is None:
            at = datetime.now()
        day_name = at.strftime("%A").lower()
        current_hour = at.hour
        day_rules = self._schedule.get(day_name, {})
        if not day_rules:
            return self._default
        # Floor lookup: largest scheduled hour ≤ current hour
        eligible = [h for h in day_rules if h <= current_hour]
        if not eligible:
            # Before first rule of the day — use yesterday's last rule
            return self._default
        active_hour = max(eligible)
        return day_rules[active_hour]

    @property
    def default_setpoint(self) -> float:
        return self._default
