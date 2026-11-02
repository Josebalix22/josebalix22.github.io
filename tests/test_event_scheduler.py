"""
test_event_scheduler.py — Unit tests for Category 2 (min-heap event scheduler)
CS 499 ePortfolio Enhancement
Run with: pytest tests/test_event_scheduler.py -v
"""

import sys
import os
import json
import heapq
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "thermostat-scheduler"))

from event_scheduler import EventScheduler, ScheduledEvent


def _write_schedule(data: dict) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return f.name


MINIMAL_SCHEDULE = {
    "default_setpoint": 68,
    "schedule": {}
}


class TestScheduledEvent:
    def test_ordering_by_fire_time(self):
        now = datetime.now()
        e1 = ScheduledEvent(now + timedelta(hours=2), 70.0, "later")
        e2 = ScheduledEvent(now + timedelta(hours=1), 65.0, "sooner")
        heap = [e1, e2]
        heapq.heapify(heap)
        assert heapq.heappop(heap).label == "sooner"

    def test_reschedule_adds_one_week(self):
        now = datetime.now()
        e = ScheduledEvent(now, 72.0, "test")
        next_e = e.reschedule_weekly()
        assert next_e.fire_time == now + timedelta(weeks=1)
        assert next_e.set_point == 72.0


class TestEventScheduler:
    def test_default_setpoint_on_empty_schedule(self):
        path = _write_schedule(MINIMAL_SCHEDULE)
        sched = EventScheduler(schedule_path=path)
        assert sched.current_setpoint == 68.0

    def test_queue_empty_on_no_rules(self):
        path = _write_schedule(MINIMAL_SCHEDULE)
        sched = EventScheduler(schedule_path=path)
        assert sched.queue_size == 0

    def test_add_event_increases_queue(self):
        path = _write_schedule(MINIMAL_SCHEDULE)
        sched = EventScheduler(schedule_path=path)
        sched.add_event(datetime.now() + timedelta(hours=1), 72.0, "test")
        assert sched.queue_size == 1

    def test_tick_fires_due_event(self):
        path = _write_schedule(MINIMAL_SCHEDULE)
        sched = EventScheduler(schedule_path=path)
        past = datetime.now() - timedelta(seconds=1)
        sched.add_event(past, 75.0, "past event")
        result = sched.tick()
        assert result == 75.0

    def test_tick_does_not_fire_future_event(self):
        path = _write_schedule(MINIMAL_SCHEDULE)
        sched = EventScheduler(schedule_path=path)
        future = datetime.now() + timedelta(hours=2)
        sched.add_event(future, 80.0, "future")
        result = sched.tick()
        assert result == 68.0  # still default

    def test_callback_invoked_on_change(self):
        path = _write_schedule(MINIMAL_SCHEDULE)
        changes = []
        sched = EventScheduler(
            schedule_path=path,
            on_setpoint_change=lambda sp, lbl: changes.append((sp, lbl))
        )
        past = datetime.now() - timedelta(seconds=1)
        sched.add_event(past, 72.0, "fired")
        sched.tick()
        assert len(changes) == 1
        assert changes[0][0] == 72.0

    def test_fired_event_rescheduled_for_next_week(self):
        path = _write_schedule(MINIMAL_SCHEDULE)
        sched = EventScheduler(schedule_path=path)
        fire_time = datetime.now() - timedelta(seconds=1)
        sched.add_event(fire_time, 72.0, "weekly")
        sched.tick()
        # After firing, event should be rescheduled 7 days out
        next_event = sched.peek_next()
        assert next_event is not None
        assert next_event.set_point == 72.0
        expected = fire_time + timedelta(weeks=1)
        assert abs((next_event.fire_time - expected).total_seconds()) < 2

    def test_peek_next_is_o1_non_destructive(self):
        path = _write_schedule(MINIMAL_SCHEDULE)
        sched = EventScheduler(schedule_path=path)
        future = datetime.now() + timedelta(hours=1)
        sched.add_event(future, 70.0, "peek test")
        before = sched.peek_next()
        after = sched.peek_next()
        assert before == after  # peek didn't consume the event
        assert sched.queue_size == 1
