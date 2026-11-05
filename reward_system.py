"""Дополнительная функция: премирование за выполнение задач в срок.

Баллы (не деньги):
- 15, если задача завершена минимум за 24 часа до дедлайна;
- 10, если задача завершена в срок, но не настолько рано;
- 0, если дедлайн пропущен.

Баллы назначаются исполнителю один раз при завершении задачи.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from task_manager import Status, TaskManager
from time_tracker import TimeTracker


class RewardSystem:
    EARLY_POINTS = 15
    ON_TIME_POINTS = 10
    LATE_POINTS = 0
    EARLY_MARGIN = timedelta(hours=24)

    def __init__(self, manager: TaskManager, tracker: TimeTracker) -> None:
        self.manager = manager
        self.tracker = tracker

    def complete_task(self, task_id: int,
                      completed_at: Optional[datetime] = None) -> dict:
        """Завершить задачу, однократно начислить баллы и вернуть результат."""
        task = self.manager.tasks.get(task_id)
        if task is None:
            raise ValueError(f"Задача с ID {task_id} не найдена")
        if task.status is Status.DONE:
            raise ValueError("Эта задача уже завершена; повторное начисление запрещено")
        if task.assignee is None:
            raise ValueError("Сначала назначьте исполнителя задачи (пункт 7)")
        if self.tracker.is_running(task_id):
            raise ValueError("Сначала остановите таймер задачи (пункт 4)")

        finished_at = completed_at if completed_at is not None else datetime.now()
        if (finished_at.tzinfo is None) != (task.due_date.tzinfo is None):
            raise ValueError("Время завершения и срок должны быть в одной временной зоне")

        if finished_at > task.due_date:
            points, reason = self.LATE_POINTS, "Просрочено"
        elif task.due_date - finished_at >= self.EARLY_MARGIN:
            points, reason = self.EARLY_POINTS, "Досрочно (не менее чем за сутки)"
        else:
            points, reason = self.ON_TIME_POINTS, "В срок"

        task.update_status(Status.DONE)
        task.completed_at = finished_at
        task.reward_points = points
        task.reward_reason = reason
        return {
            "task_id": task.task_id,
            "title": task.title,
            "employee": task.assignee.name,
            "points": points,
            "reason": reason,
            "completed_at": finished_at.isoformat(),
        }

    def get_leaderboard(self) -> list[dict]:
        """Рейтинг всех сотрудников, в том числе с 0 баллов."""
        leaderboard = []
        for user in self.manager.users.values():
            finished = [task for task in self.manager.tasks.values()
                        if (task.assignee is not None
                            and task.assignee.user_id == user.user_id
                            and task.status is Status.DONE)]
            leaderboard.append({
                "user_id": user.user_id,
                "name": user.name,
                "completed_count": len(finished),
                "points": sum(task.reward_points for task in finished),
            })
        leaderboard.sort(key=lambda row: (-row["points"], row["name"].casefold(), row["user_id"]))
        return leaderboard

    def export_csv(self, path: str = "reward_report.csv") -> Path:
        """Сохранить рейтинг в CSV, который можно открыть в Excel."""
        result_path = Path(path)
        with result_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(["Место", "ID сотрудника", "Сотрудник",
                             "Завершено задач", "Баллы"])
            for place, row in enumerate(self.get_leaderboard(), 1):
                writer.writerow([place, row["user_id"], row["name"],
                                 row["completed_count"], row["points"]])
        return result_path
