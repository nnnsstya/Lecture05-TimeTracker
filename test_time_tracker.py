"""Автоматические тесты для основных требований практического задания."""

import csv
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from storage import load_data, save_data
from task_manager import Priority, Status, TaskManager
from time_tracker import TimeTracker, format_duration


class TestTimeTracker(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 29, 10, 0, tzinfo=timezone.utc)
        self.manager = TaskManager()
        self.task = self.manager.create_task(
            "Подготовить отчёт", "Описать работу модуля", Priority.HIGH,
            datetime.now() + timedelta(days=7)
        )
        self.tracker = TimeTracker(self.manager, clock=lambda: self.now)

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)

    def test_task_creation(self):
        self.assertEqual(self.task.title, "Подготовить отчёт")
        self.assertEqual(self.task.status, Status.TODO)

    def test_task_assignment_from_lecture(self):
        user = self.manager.create_user("Анна", "anna@example.com")
        self.assertTrue(self.manager.assign_task(self.task.task_id, user.user_id))
        self.assertEqual(self.task.assignee.name, "Анна")
        self.assertEqual(self.task.status, Status.IN_PROGRESS)

    def test_cannot_start_for_unknown_task(self):
        with self.assertRaises(ValueError):
            self.tracker.start_timer(999)

    def test_timer_starts(self):
        entry = self.tracker.start_timer(self.task.task_id)
        self.assertIsNone(entry.ended_at)
        self.assertTrue(self.tracker.is_running(self.task.task_id))

    def test_cannot_start_same_timer_twice(self):
        self.tracker.start_timer(self.task.task_id)
        with self.assertRaises(ValueError):
            self.tracker.start_timer(self.task.task_id)

    def test_timer_stops_and_counts_seconds(self):
        self.tracker.start_timer(self.task.task_id)
        self.advance(120)
        self.assertEqual(self.tracker.stop_timer(self.task.task_id), 120)
        self.assertFalse(self.tracker.is_running(self.task.task_id))

    def test_cannot_stop_unstarted_timer(self):
        with self.assertRaises(ValueError):
            self.tracker.stop_timer(self.task.task_id)

    def test_sum_of_multiple_sessions(self):
        self.tracker.start_timer(self.task.task_id)
        self.advance(100)
        self.tracker.stop_timer(self.task.task_id)
        self.advance(10)
        self.tracker.start_timer(self.task.task_id)
        self.advance(60)
        self.tracker.stop_timer(self.task.task_id)
        self.assertEqual(self.tracker.get_total_seconds(self.task.task_id), 160)

    def test_running_session_included(self):
        self.tracker.start_timer(self.task.task_id)
        self.advance(75)
        self.assertEqual(self.tracker.get_total_seconds(self.task.task_id), 75)
        self.assertEqual(self.tracker.get_total_seconds(self.task.task_id, False), 0)

    def test_different_tasks_tracked_separately(self):
        second = self.manager.create_task(
            "Вторая задача", "", Priority.LOW, datetime.now() + timedelta(days=2)
        )
        self.tracker.start_timer(self.task.task_id)
        self.advance(30)
        self.tracker.stop_timer(self.task.task_id)
        self.tracker.start_timer(second.task_id)
        self.advance(60)
        self.tracker.stop_timer(second.task_id)
        self.assertEqual(self.tracker.get_total_seconds(self.task.task_id), 30)
        self.assertEqual(self.tracker.get_total_seconds(second.task_id), 60)

    def test_report_has_correct_total_and_running_flag(self):
        self.tracker.start_timer(self.task.task_id)
        self.advance(125)
        report = self.tracker.generate_report()
        self.assertEqual(report["total_time"], "00:02:05")
        self.assertTrue(report["tasks"][0]["running"])
        self.assertEqual(report["tasks"][0]["sessions_count"], 1)

    def test_report_includes_tasks_with_zero_time(self):
        report = self.tracker.generate_report()
        self.assertEqual(report["tasks"][0]["total_seconds"], 0)
        self.assertEqual(report["total_time"], "00:00:00")

    def test_csv_report(self):
        self.tracker.start_timer(self.task.task_id)
        self.advance(60)
        self.tracker.stop_timer(self.task.task_id)
        with tempfile.TemporaryDirectory() as directory:
            output = self.tracker.export_csv(str(Path(directory) / "report.csv"))
            with output.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle, delimiter=";"))
            self.assertEqual(rows[1][1], "Подготовить отчёт")
            self.assertEqual(rows[1][4], "00:01:00")
            self.assertEqual(rows[-1][1], "ИТОГО")

    def test_json_persistence_completed_entry(self):
        user = self.manager.create_user("Анна", "anna@example.com")
        self.manager.assign_task(self.task.task_id, user.user_id)
        self.tracker.start_timer(self.task.task_id)
        self.advance(42)
        self.tracker.stop_timer(self.task.task_id)
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "data.json"
            save_data(self.manager, self.tracker, filename)
            loaded_manager, loaded_tracker = load_data(filename)
            self.assertEqual(len(loaded_manager.tasks), 1)
            self.assertEqual(loaded_manager.tasks[1].assignee.name, "Анна")
            self.assertEqual(len(loaded_tracker.entries), 1)
            self.assertEqual(loaded_tracker.entries[0].elapsed_seconds(self.now), 42)

    def test_json_persistence_running_timer(self):
        self.tracker.start_timer(self.task.task_id)
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "data.json"
            save_data(self.manager, self.tracker, filename)
            _, loaded_tracker = load_data(filename)
            self.assertTrue(loaded_tracker.is_running(self.task.task_id))

    def test_negative_duration_rejected(self):
        self.tracker.start_timer(self.task.task_id)
        self.advance(-15)
        with self.assertRaises(ValueError):
            self.tracker.stop_timer(self.task.task_id)

    def test_duration_longer_than_a_day(self):
        self.assertEqual(format_duration(27 * 3600 + 61), "27:01:01")


if __name__ == "__main__":
    unittest.main(verbosity=2)
