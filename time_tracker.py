"""Учёт рабочего времени для задач существующего TaskManager."""

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

from task_manager import TaskManager, Status


def format_duration(seconds: float) -> str:
    """Время в формате часы:минуты:секунды (часы не ограничены 24)."""
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


@dataclass
class TimeEntry:
    task_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None

    def elapsed_seconds(self, now: datetime) -> float:
        end = self.ended_at if self.ended_at is not None else now
        return max(0.0, (end - self.started_at).total_seconds())


class TimeTracker:
    """Таймеры привязаны к ID задач из TaskManager."""

    def __init__(self, manager: TaskManager,
                 clock: Optional[Callable[[], datetime]] = None) -> None:
        self.manager = manager
        self.entries: List[TimeEntry] = []
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _check_task(self, task_id: int) -> None:
        if task_id not in self.manager.tasks:
            raise ValueError(f"Задача с ID {task_id} не найдена")

    def is_running(self, task_id: int) -> bool:
        self._check_task(task_id)
        return any(entry.task_id == task_id and entry.ended_at is None
                   for entry in self.entries)

    def start_timer(self, task_id: int) -> TimeEntry:
        """Начать новый интервал; нельзя запустить два таймера одной задачи."""
        self._check_task(task_id)
        if self.manager.tasks[task_id].status is Status.DONE:
            raise ValueError("Нельзя запускать таймер завершённой задачи")
        if self.is_running(task_id):
            raise ValueError(f"Таймер задачи {task_id} уже запущен")
        entry = TimeEntry(task_id, self._clock())
        self.entries.append(entry)
        return entry

    def stop_timer(self, task_id: int) -> float:
        """Остановить таймер и вернуть продолжительность интервала в секундах."""
        self._check_task(task_id)
        for entry in reversed(self.entries):
            if entry.task_id == task_id and entry.ended_at is None:
                ended_at = self._clock()
                if ended_at < entry.started_at:
                    raise ValueError("Время окончания раньше времени старта")
                entry.ended_at = ended_at
                return entry.elapsed_seconds(ended_at)
        raise ValueError(f"Для задачи {task_id} нет запущенного таймера")

    def get_total_seconds(self, task_id: int, include_running: bool = True) -> float:
        """Сумма завершённых интервалов и, при необходимости, текущего."""
        self._check_task(task_id)
        now = self._clock()
        return sum(
            entry.elapsed_seconds(now)
            for entry in self.entries
            if entry.task_id == task_id and (include_running or entry.ended_at is not None)
        )

    def generate_report(self) -> dict:
        """Сводный отчёт для всех существующих задач."""
        now = self._clock()  # Одинаковый момент расчёта для всех строк
        rows = []
        for task in sorted(self.manager.tasks.values(), key=lambda t: t.task_id):
            intervals = [entry for entry in self.entries if entry.task_id == task.task_id]
            seconds = sum(entry.elapsed_seconds(now) for entry in intervals)
            rows.append({
                "task_id": task.task_id,
                "title": task.title,
                "assignee": task.assignee.name if task.assignee else "Не назначен",
                "status": task.status.value,
                "total_seconds": round(seconds, 2),
                "total_time": format_duration(seconds),
                "sessions_count": len(intervals),
                "running": any(entry.ended_at is None for entry in intervals),
            })
        return {
            "generated_at": now.isoformat(),
            "tasks": rows,
            "total_seconds": round(sum(row["total_seconds"] for row in rows), 2),
            "total_time": format_duration(sum(row["total_seconds"] for row in rows)),
        }

    def export_csv(self, path: str) -> Path:
        """Экспорт отчёта в CSV, пригодный для Excel (UTF-8 с BOM)."""
        report = self.generate_report()
        output = Path(path)
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(["ID задачи", "Название", "Исполнитель", "Статус",
                             "Затрачено (ЧЧ:ММ:СС)", "Секунды", "Число запусков", "Таймер работает"])
            for row in report["tasks"]:
                writer.writerow([
                    row["task_id"], row["title"], row["assignee"], row["status"],
                    row["total_time"], row["total_seconds"], row["sessions_count"],
                    "Да" if row["running"] else "Нет",
                ])
            writer.writerow(["", "ИТОГО", "", "", report["total_time"],
                             report["total_seconds"], "", ""])
        return output

    def to_dict(self) -> dict:
        return {
            "entries": [
                {
                    "task_id": entry.task_id,
                    "started_at": entry.started_at.isoformat(),
                    "ended_at": entry.ended_at.isoformat() if entry.ended_at else None,
                }
                for entry in self.entries
            ]
        }

    @classmethod
    def from_dict(cls, data: dict, manager: TaskManager,
                  clock: Optional[Callable[[], datetime]] = None) -> "TimeTracker":
        tracker = cls(manager, clock)
        for item in data.get("entries", []):
            if item["task_id"] not in manager.tasks:
                raise ValueError("Данные таймера ссылаются на несуществующую задачу")
            tracker.entries.append(TimeEntry(
                task_id=item["task_id"],
                started_at=datetime.fromisoformat(item["started_at"]),
                ended_at=(datetime.fromisoformat(item["ended_at"])
                          if item.get("ended_at") else None),
            ))
        return tracker
