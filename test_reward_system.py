"""Проверки дополнительного модуля премирования сотрудников."""

import csv
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from reward_system import RewardSystem
from storage import save_data, load_data
from task_manager import Priority, Status, TaskManager
from time_tracker import TimeTracker


class TestRewardSystem(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 1, 1, 12, 0, 0)
        self.manager = TaskManager()
        self.anna = self.manager.create_user("Анна", "anna@example.com")
        self.ivan = self.manager.create_user("Иван", "ivan@example.com")
        self.task = self.create_task("Первая задача", self.anna.user_id)
        self.tracker = TimeTracker(self.manager)
        self.rewards = RewardSystem(self.manager, self.tracker)

    def create_task(self, name, user_id, due=None):
        task = self.manager.create_task(name, "", Priority.MEDIUM,
                                        due or self.start + timedelta(days=4))
        task.created_at = self.start
        if user_id is not None:
            self.manager.assign_task(task.task_id, user_id)
        return task

    def test_early_completion_gets_15_points(self):
        result = self.rewards.complete_task(self.task.task_id,
                                            self.start + timedelta(days=2))
        self.assertEqual(result["points"], 15)
        self.assertEqual(result["reason"], "Досрочно (не менее чем за сутки)")
        self.assertEqual(self.task.status, Status.DONE)

    def test_early_threshold_exactly_one_day(self):
        result = self.rewards.complete_task(self.task.task_id,
                                            self.start + timedelta(days=3))
        self.assertEqual(result["points"], 15)

    def test_on_time_earns_10_points(self):
        result = self.rewards.complete_task(self.task.task_id,
                                            self.start + timedelta(days=3, hours=1))
        self.assertEqual(result["points"], 10)
        self.assertEqual(result["reason"], "В срок")

    def test_exact_deadline_counts_as_on_time(self):
        result = self.rewards.complete_task(self.task.task_id,
                                            self.task.due_date)
        self.assertEqual(result["points"], 10)

    def test_late_task_gets_zero(self):
        result = self.rewards.complete_task(self.task.task_id,
                                            self.task.due_date + timedelta(seconds=1))
        self.assertEqual(result["points"], 0)
        self.assertEqual(result["reason"], "Просрочено")

    def test_no_double_rewards(self):
        self.rewards.complete_task(self.task.task_id, self.start + timedelta(days=2))
        with self.assertRaises(ValueError):
            self.rewards.complete_task(self.task.task_id, self.start + timedelta(days=2))
        self.assertEqual(self.rewards.get_leaderboard()[0]["points"], 15)

    def test_cannot_complete_without_assignee(self):
        other = self.create_task("Без исполнителя", None)
        with self.assertRaisesRegex(ValueError, "назначьте исполнителя"):
            self.rewards.complete_task(other.task_id)
        self.assertEqual(other.status, Status.TODO)

    def test_cannot_complete_while_timer_runs(self):
        self.tracker.start_timer(self.task.task_id)
        with self.assertRaisesRegex(ValueError, "остановите таймер"):
            self.rewards.complete_task(self.task.task_id)
        self.assertNotEqual(self.task.status, Status.DONE)

    def test_unknown_task(self):
        with self.assertRaises(ValueError):
            self.rewards.complete_task(999)

    def test_leaderboard_order_and_cumulative_points(self):
        second = self.create_task("Вторая задача", self.ivan.user_id)
        third = self.create_task("Третья задача", self.anna.user_id)
        self.rewards.complete_task(self.task.task_id, self.start + timedelta(days=2))
        self.rewards.complete_task(second.task_id, second.due_date)
        self.rewards.complete_task(third.task_id, third.due_date)
        ranking = self.rewards.get_leaderboard()
        self.assertEqual([row["name"] for row in ranking], ["Анна", "Иван"])
        self.assertEqual([row["points"] for row in ranking], [25, 10])
        self.assertEqual([row["completed_count"] for row in ranking], [2, 1])

    def test_unrewarded_employee_present_in_ranking(self):
        self.rewards.complete_task(self.task.task_id, self.task.due_date)
        ranking = self.rewards.get_leaderboard()
        self.assertEqual(ranking[1]["name"], "Иван")
        self.assertEqual(ranking[1]["points"], 0)

    def test_persistence_preserves_rewards(self):
        self.rewards.complete_task(self.task.task_id, self.start + timedelta(days=2))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tasks_data.json"
            save_data(self.manager, self.tracker, path)
            manager, tracker = load_data(path)
            loaded = manager.tasks[self.task.task_id]
            self.assertEqual(loaded.reward_points, 15)
            self.assertEqual(loaded.reward_reason, "Досрочно (не менее чем за сутки)")
            self.assertEqual(loaded.completed_at, self.start + timedelta(days=2))
            with self.assertRaises(ValueError):
                RewardSystem(manager, tracker).complete_task(loaded.task_id)

    def test_legacy_data_without_bonus_fields_still_loads(self):
        data = self.manager.to_dict()
        for entry in data["tasks"]:
            entry.pop("reward_points")
            entry.pop("reward_reason")
            entry.pop("completed_at")
        loaded = TaskManager.from_dict(data)
        self.assertEqual(loaded.tasks[self.task.task_id].reward_points, 0)
        self.assertIsNone(loaded.tasks[self.task.task_id].completed_at)

    def test_no_new_timer_after_completion(self):
        self.rewards.complete_task(self.task.task_id, self.start + timedelta(days=2))
        with self.assertRaises(ValueError):
            self.tracker.start_timer(self.task.task_id)

    def test_no_reassignment_after_completion(self):
        self.rewards.complete_task(self.task.task_id, self.start + timedelta(days=2))
        self.assertFalse(self.manager.assign_task(self.task.task_id, self.ivan.user_id))
        self.assertEqual(self.task.assignee.user_id, self.anna.user_id)

    def test_export_rewards_csv(self):
        self.rewards.complete_task(self.task.task_id, self.task.due_date)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rewards.csv"
            self.rewards.export_csv(str(path))
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle, delimiter=";"))
            self.assertEqual(rows[0][-1], "Баллы")
            self.assertEqual(rows[1][2], "Анна")
            self.assertEqual(rows[1][4], "10")

    def test_completion_records_date_and_status(self):
        finished = self.start + timedelta(days=2)
        self.rewards.complete_task(self.task.task_id, finished)
        self.assertEqual(self.task.completed_at, finished)
        self.assertEqual(self.task.status, Status.DONE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
