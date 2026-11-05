"""Модели задач и менеджер задач на основе примера из лекции № 5."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Status(Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    DONE = "Done"


@dataclass
class User:
    user_id: int
    name: str
    email: str


@dataclass
class Task:
    task_id: int
    title: str
    description: str
    priority: Priority
    due_date: datetime
    status: Status = Status.TODO
    assignee: Optional[User] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    reward_points: int = 0
    reward_reason: str = ""

    def assign_to(self, user: User) -> None:
        """Назначить задачу пользователю."""
        self.assignee = user
        self.status = Status.IN_PROGRESS

    def update_status(self, new_status: Status) -> None:
        self.status = new_status

    def is_overdue(self) -> bool:
        return datetime.now() > self.due_date and self.status is not Status.DONE


class TaskManager:
    """Создание, назначение и хранение задач (по структуре лекции)."""

    def __init__(self) -> None:
        self.tasks: Dict[int, Task] = {}
        self.users: Dict[int, User] = {}
        self.next_task_id = 1
        self.next_user_id = 1

    def create_user(self, name: str, email: str) -> User:
        if not name.strip() or not email.strip():
            raise ValueError("Имя и email пользователя не должны быть пустыми")
        user = User(self.next_user_id, name.strip(), email.strip())
        self.users[user.user_id] = user
        self.next_user_id += 1
        return user

    def create_task(self, title: str, description: str,
                    priority: Priority, due_date: datetime) -> Task:
        if not title.strip():
            raise ValueError("Название задачи не должно быть пустым")
        task = Task(self.next_task_id, title.strip(), description.strip(),
                    priority, due_date)
        self.tasks[task.task_id] = task
        self.next_task_id += 1
        return task

    def assign_task(self, task_id: int, user_id: int) -> bool:
        task = self.tasks.get(task_id)
        user = self.users.get(user_id)
        if task is None or user is None or task.status is Status.DONE:
            return False
        task.assign_to(user)
        return True

    def get_overdue_tasks(self) -> List[Task]:
        return [task for task in self.tasks.values() if task.is_overdue()]

    def get_user_tasks(self, user_id: int) -> List[Task]:
        return [task for task in self.tasks.values()
                if task.assignee is not None and task.assignee.user_id == user_id]

    def generate_report(self) -> dict:
        """Отчёт по задачам из примера лекции."""
        counts = {}
        for task in self.tasks.values():
            counts[task.status.value] = counts.get(task.status.value, 0) + 1
        return {
            "total_tasks": len(self.tasks),
            "overdue_tasks": len(self.get_overdue_tasks()),
            "status_distribution": counts,
            "report_generated_at": datetime.now().isoformat(),
        }

    def to_dict(self) -> dict:
        """Подготовить задачи и пользователей для сохранения в JSON."""
        return {
            "next_task_id": self.next_task_id,
            "next_user_id": self.next_user_id,
            "users": [vars(user) for user in self.users.values()],
            "tasks": [
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "description": task.description,
                    "priority": task.priority.name,
                    "due_date": task.due_date.isoformat(),
                    "status": task.status.name,
                    "assignee_id": task.assignee.user_id if task.assignee else None,
                    "created_at": task.created_at.isoformat(),
                    "completed_at": (task.completed_at.isoformat()
                                     if task.completed_at else None),
                    "reward_points": task.reward_points,
                    "reward_reason": task.reward_reason,
                }
                for task in self.tasks.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskManager":
        manager = cls()
        for item in data.get("users", []):
            user = User(**item)
            manager.users[user.user_id] = user
        for item in data.get("tasks", []):
            assignee_id = item.get("assignee_id")
            task = Task(
                task_id=item["task_id"],
                title=item["title"],
                description=item["description"],
                priority=Priority[item["priority"]],
                due_date=datetime.fromisoformat(item["due_date"]),
                status=Status[item["status"]],
                assignee=manager.users.get(assignee_id),
                created_at=datetime.fromisoformat(item["created_at"]),
                completed_at=(datetime.fromisoformat(item["completed_at"])
                              if item.get("completed_at") else None),
                reward_points=int(item.get("reward_points", 0)),
                reward_reason=item.get("reward_reason", ""),
            )
            manager.tasks[task.task_id] = task
        manager.next_task_id = max(
            data.get("next_task_id", 1), max(manager.tasks, default=0) + 1)
        manager.next_user_id = max(
            data.get("next_user_id", 1), max(manager.users, default=0) + 1)
        return manager
