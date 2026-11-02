"""
event_scheduler.py — Category 2: Algorithms & Data Structures
CS 499 ePortfolio Enhancement

Enhancement: Replaces the original polling loop with a priority-queue-driven
event scheduler.  Instead of evaluating every possible time slot each tick
(O(n) scan), we use a min-heap so the next event is always O(1) to peek and
O(log n) to insert or remove.

Original approach (polling loop):
    every second:
        for each rule in schedule:        # O(n)
            if rule matches current time:
                apply rule

Enhanced approach (min-heap event queue):
    on startup: push all today's events → O(n log n)
    each tick:
        peek at heap top                  # O(1)
        if top.fire_time <= now:
            pop and apply                 # O(log n)
            push tomorrow's recurrence   # O(log n)
    → amortized O(log n) per tick

Big-O comparison:
    | Operation         | Polling Loop | Min-Heap Queue |
    |-------------------|--------------|----------------|
    | Next event lookup | O(n)         | O(1)           |
    | Apply + reschedule| O(1)         | O(log n)       |
    | Tick cost         | O(n)         | O(log n)       |
    | Space             | O(1)         | O(n)           |

For small n (< 50 rules) the difference is negligible, but the heap scales
gracefully to thousands of rules (smart building, industrial HVAC) where a
polling scan becomes a measurable bottleneck.
"""

import heapq
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional


@dataclass(order=True)
class ScheduledEvent:
    """
    One thermostat set-point change event in the priority queue.

    Ordered by fire_time so the heap always surfaces the soonest event.
    """
    fire_time: datetime
    set_point: float = field(compare=False)
    label: str = field(compare=False, default="")

    def reschedule_weekly(self) -> "ScheduledEvent":
        """Return a copy of this event scheduled for 7 days later."""
        return ScheduledEvent(
            fire_time=self.fire_time + timedelta(weeks=1),
            set_point=self.set_point,
            label=self.label,
        )


class EventScheduler:
    """
    Priority-queue-driven thermostat event scheduler.

    Loads events from the same schedule.json format as the OOP thermostat
    (Category 1) so both enhancements share one configuration file.
    """

    def __init__(
        self,
        schedule_path: str = "../thermostat-oop/schedule.json",
        on_setpoint_change: Optional[Callable[[float, str], None]] = None,
    ):
        """
        Args:
            schedule_path: Path to schedule.json.
            on_setpoint_change: Optional callback invoked whenever the
                active set-point changes: fn(new_setpoint, label).
        """
        self._heap: List[ScheduledEvent] = []
        self._current_setpoint: float = 68.0
        self._on_change = on_setpoint_change
        self._load(schedule_path)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _load(self, path: str) -> None:
        config = Path(path)
        if not config.exists():
            raise FileNotFoundError(f"Schedule file not found: {path}")
        with open(config) as f:
            data = json.load(f)
        self._current_setpoint = float(data.get("default_setpoint", 68.0))
        now = datetime.now()
        raw = data.get("schedule", {})

        # Build events for the next 7 days so the heap covers a full week
        day_names = ["monday", "tuesday", "wednesday", "thursday",
                     "friday", "saturday", "sunday"]
        today_idx = now.weekday()  # Monday=0

        for offset in range(7):
            day_idx = (today_idx + offset) % 7
            day_name = day_names[day_idx]
            rules = raw.get(day_name, {})
            event_date = now.date() + timedelta(days=offset)
            for hour_str, temp in rules.items():
                fire_dt = datetime(
                    event_date.year, event_date.month, event_date.day,
                    int(hour_str), 0, 0
                )
                if fire_dt > now:  # only future events
                    label = f"{day_name.capitalize()} {hour_str}:00"
                    heapq.heappush(
                        self._heap,
                        ScheduledEvent(fire_dt, float(temp), label)
                    )

    # ------------------------------------------------------------------
    # Runtime API
    # ------------------------------------------------------------------

    def tick(self, at: datetime = None) -> float:
        """
        Process any due events and return the current set-point.

        O(log n) amortised: only fired when an event is at the top.
        """
        if at is None:
            at = datetime.now()

        while self._heap and self._heap[0].fire_time <= at:
            event = heapq.heappop(self._heap)           # O(log n)
            old = self._current_setpoint
            self._current_setpoint = event.set_point
            if self._on_change and old != self._current_setpoint:
                self._on_change(self._current_setpoint, event.label)
            # Reschedule same event for next week
            heapq.heappush(self._heap, event.reschedule_weekly())  # O(log n)

        return self._current_setpoint

    def peek_next(self) -> Optional[ScheduledEvent]:
        """Return the next scheduled event without firing it. O(1)."""
        return self._heap[0] if self._heap else None

    def add_event(self, fire_time: datetime, set_point: float, label: str = "") -> None:
        """Dynamically insert a new event. O(log n)."""
        heapq.heappush(self._heap, ScheduledEvent(fire_time, set_point, label))

    @property
    def current_setpoint(self) -> float:
        return self._current_setpoint

    @property
    def queue_size(self) -> int:
        return len(self._heap)


# ---------------------------------------------------------------------------
# Demo / manual test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from datetime import datetime, timedelta

    fired_events = []

    def on_change(sp, label):
        fired_events.append((sp, label))
        print(f"  → Set-point changed to {sp}°F  [{label}]")

    # Build a scheduler with an in-memory fake future event
    sched = EventScheduler(
        schedule_path="../thermostat-oop/schedule.json",
        on_setpoint_change=on_change,
    )

    print(f"Queue size on startup: {sched.queue_size}")
    print(f"Current set-point:     {sched.current_setpoint}°F")
    if sched.peek_next():
        print(f"Next event:            {sched.peek_next().label} @ "
              f"{sched.peek_next().fire_time} → {sched.peek_next().set_point}°F")

    # Inject a fake event 2 seconds in the future for demonstration
    import time
    future = datetime.now() + timedelta(seconds=2)
    sched.add_event(future, 74.0, "Demo override")
    print(f"\nAdded demo event firing in 2 seconds → 74°F")
    print("Ticking for 3 seconds...")

    for i in range(3):
        time.sleep(1)
        sp = sched.tick()
        print(f"  tick {i+1}: set-point = {sp}°F")

    print(f"\nEvents fired: {fired_events}")
