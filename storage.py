"""Сохранение задач и таймеров между запусками программы."""

import json
import os
from pathlib import Path

from task_manager import TaskManager
from time_tracker import TimeTracker


DATA_FILE = Path(__file__).resolve().parent / "tasks_data.json"


def save_data(manager: TaskManager, tracker: TimeTracker,
              path: Path = DATA_FILE) -> None:
    """Атомарная запись JSON: замена файла после успешной записи."""
    path = Path(path)
    temporary_path = path.with_name(path.name + ".tmp")
    content = {"manager": manager.to_dict(), "tracker": tracker.to_dict()}
    try:
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(content, handle, indent=2, ensure_ascii=False)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def load_data(path: Path = DATA_FILE) -> tuple[TaskManager, TimeTracker]:
    path = Path(path)
    if not path.exists():
        manager = TaskManager()
        return manager, TimeTracker(manager)
    with path.open("r", encoding="utf-8") as handle:
        content = json.load(handle)
    manager = TaskManager.from_dict(content["manager"])
    tracker = TimeTracker.from_dict(content["tracker"], manager)
    return manager, tracker
