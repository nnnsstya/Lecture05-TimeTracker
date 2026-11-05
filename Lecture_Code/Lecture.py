# -*- coding: utf-8 -*-
"""Лекция №5 «Этапы разработки программного продукта» — весь код в одном файле.

Объединены исправленные примеры разделов 2.1–2.6 и 3.1.
Все классы и функции находятся в одном модуле: никакие соседние .py файлы не требуются.

Запуск из PyCharm: Run 'Lecture05_All_In_One' → выбрать пункт 1–7 или 8.
Командная строка: python Lecture05_All_In_One.py --all
                   python Lecture05_All_In_One.py --tests

При выборе этапа 2.5 создаётся папка deploy с копией этого файла и config.json.
"""

import json
import os
import shutil
import subprocess
import sys
import logging
import time
import unittest
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Dict, List, Optional, Any


# ================== 2.1 АНАЛИЗ ТРЕБОВАНИЙ ==================

class TaskRequirement:
    def __init__(self, description, priority, category):
        self.description = description
        self.priority = priority  # High, Medium, Low
        self.category = category  # Functional, Non-functional

    def validate(self):
        """Валидация требований"""
        if not self.description:
            raise ValueError("Требование должно иметь описание")
        return True

def demo_requirements():
    requirements = [
        TaskRequirement("Система должна позволять создавать задачи", "High", "Functional"),
        TaskRequirement("Время отклика менее 2 секунд", "Medium", "Non-functional"),
    ]
    print("Собранные требования:")
    for req in requirements:
        req.validate()
        print(f"- {req.description} ({req.category}, {req.priority})")



# ================== 2.2 ПРОЕКТИРОВАНИЕ ==================

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

class User:
    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email

    def __str__(self):
        return f"User({self.name}, {self.email})"

class Task:
    def __init__(self, task_id: int, title: str, description: str,
                 priority: Priority, due_date: datetime):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.priority = priority
        self.due_date = due_date
        self.status = Status.TODO
        self.assignee: Optional[User] = None
        self.created_at = datetime.now()

    def assign_to(self, user: User):
        """Назначение задачи пользователю"""
        self.assignee = user
        self.status = Status.IN_PROGRESS

    def update_status(self, new_status: Status):
        """Обновление статуса задачи"""
        self.status = new_status

    def is_overdue(self) -> bool:
        """Проверка просрочки задачи"""
        return datetime.now() > self.due_date

    def __str__(self):
        return f"Task '{self.title}' ({self.status.value})"

# Пример использования проектирования
def demonstrate_design():
    # Создаем пользователей
    user1 = User(1, "Иван Петров", "ivan@company.com")
    user2 = User(2, "Мария Сидорова", "maria@company.com")

    # Создаем задачу
    due_date = datetime.now() + timedelta(days=7)
    task = Task(1, "Разработать модуль аутентификации",
                "Создать систему входа и регистрации пользователей",
                Priority.HIGH, due_date)

    # Назначаем задачу
    task.assign_to(user1)
    print(f"Задача создана: {task}")
    print(f"Исполнитель: {task.assignee}")


# ================== 2.3 РЕАЛИЗАЦИЯ ==================

class TaskManager:
    """Класс для управления задачами"""

    def __init__(self):
        self.tasks: Dict[int, Task] = {}
        self.users: Dict[int, User] = {}
        self.next_task_id = 1
        self.next_user_id = 1

    def create_user(self, name: str, email: str) -> User:
        """Создание нового пользователя"""
        user = User(self.next_user_id, name, email)
        self.users[self.next_user_id] = user
        self.next_user_id += 1
        return user

    def create_task(self, title: str, description: str,
                   priority: Priority, due_date: datetime) -> Task:
        """Создание новой задачи"""
        task = Task(self.next_task_id, title, description, priority, due_date)
        self.tasks[self.next_task_id] = task
        self.next_task_id += 1
        return task

    def assign_task(self, task_id: int, user_id: int) -> bool:
        """Назначение задачи пользователю"""
        task = self.tasks.get(task_id)
        user = self.users.get(user_id)

        if task and user:
            task.assign_to(user)
            return True
        return False

    def get_overdue_tasks(self) -> List[Task]:
        """Получение списка просроченных задач"""
        return [task for task in self.tasks.values() if task.is_overdue()]

    def get_user_tasks(self, user_id: int) -> List[Task]:
        """Получение задач конкретного пользователя"""
        return [task for task in self.tasks.values()
                if task.assignee and task.assignee.user_id == user_id]

    def generate_report(self) -> Dict:
        """Генерация отчета по задачам"""
        total_tasks = len(self.tasks)
        overdue_tasks = len(self.get_overdue_tasks())

        status_count = {}
        for task in self.tasks.values():
            status_count[task.status] = status_count.get(task.status, 0) + 1

        return {
            "total_tasks": total_tasks,
            "overdue_tasks": overdue_tasks,
            "status_distribution": {status.value: count for status, count in status_count.items()},
            "report_generated_at": datetime.now().isoformat()
        }

# Демонстрация работы системы
def demo_implementation():
    manager = TaskManager()

    # Создаем пользователей
    developer = manager.create_user("Алексей Кодлов", "alexey@company.com")
    tester = manager.create_user("Елена Тестова", "elena@company.com")

    # Создаем задачи
    task1 = manager.create_task(
        "Разработать REST API",
        "Создать API для управления задачами",
        Priority.HIGH,
        datetime.now() + timedelta(days=14)
    )

    task2 = manager.create_task(
        "Написать unit-тесты",
        "Покрыть код модульными тестами",
        Priority.MEDIUM,
        datetime.now() + timedelta(days=7)
    )

    # Назначаем задачи
    manager.assign_task(task1.task_id, developer.user_id)
    manager.assign_task(task2.task_id, tester.user_id)

    # Генерируем отчет
    report = manager.generate_report()
    print("Отчет по задачам:")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    # Показываем задачи разработчика
    dev_tasks = manager.get_user_tasks(developer.user_id)
    print(f"\nЗадачи разработчика {developer.name}:")
    for task in dev_tasks:
        print(f"  - {task.title} ({task.status.value})")


# ================== 2.4 ТЕСТИРОВАНИЕ ==================

class TestTaskSystem(unittest.TestCase):
    def setUp(self):
        """Настройка тестовой среды"""
        self.manager = TaskManager()
        self.user = self.manager.create_user("Тест User", "test@test.com")
        self.due_date = datetime.now() + timedelta(days=5)

    def test_task_creation(self):
        """Тест создания задачи"""
        task = self.manager.create_task(
            "Тестовая задача",
            "Описание тестовой задачи",
            Priority.MEDIUM,
            self.due_date
        )

        self.assertEqual(task.title, "Тестовая задача")
        self.assertEqual(task.status, Status.TODO)
        self.assertIsNone(task.assignee)

    def test_task_assignment(self):
        """Тест назначения задачи"""
        task = self.manager.create_task(
            "Назначаемая задача",
            "Должна быть назначена пользователю",
            Priority.HIGH,
            self.due_date
        )

        # Назначаем задачу
        success = self.manager.assign_task(task.task_id, self.user.user_id)

        self.assertTrue(success)
        self.assertEqual(task.assignee.user_id, self.user.user_id)
        self.assertEqual(task.status, Status.IN_PROGRESS)

    def test_overdue_detection(self):
        """Тест обнаружения просроченных задач"""
        # Создаем просроченную задачу
        past_date = datetime.now() - timedelta(days=1)
        overdue_task = self.manager.create_task(
            "Просроченная задача",
            "Должна быть обнаружена как просроченная",
            Priority.LOW,
            past_date
        )

        overdue_tasks = self.manager.get_overdue_tasks()
        self.assertIn(overdue_task, overdue_tasks)

    def test_user_tasks_retrieval(self):
        """Тест получения задач пользователя"""
        task1 = self.manager.create_task("Задача 1", "Описание 1", Priority.MEDIUM, self.due_date)
        task2 = self.manager.create_task("Задача 2", "Описание 2", Priority.LOW, self.due_date)

        self.manager.assign_task(task1.task_id, self.user.user_id)
        self.manager.assign_task(task2.task_id, self.user.user_id)

        user_tasks = self.manager.get_user_tasks(self.user.user_id)
        self.assertEqual(len(user_tasks), 2)

    def test_report_generation(self):
        """Тест генерации отчета"""
        # Создаем несколько задач
        for i in range(3):
            self.manager.create_task(
                f"Задача {i}",
                f"Описание {i}",
                Priority.MEDIUM,
                self.due_date
            )

        report = self.manager.generate_report()

        self.assertEqual(report["total_tasks"], 3)
        self.assertEqual(report["status_distribution"]["To Do"], 3)


# ================== 2.5 РАЗВЁРТЫВАНИЕ ==================

class DeploymentManager:
    """Пример развёртывания, адаптированный для одного исходного файла."""

    def __init__(self, project_path: str, deploy_path: str):
        self.project_path = Path(project_path)
        self.deploy_path = Path(deploy_path)

    def validate_environment(self) -> bool:
        print("Проверка окружения...")
        if sys.version_info < (3, 8):
            print("Ошибка: нужен Python 3.8 или новее")
            return False
        if not (self.project_path / "Lecture05_All_In_One.py").is_file():
            print("Ошибка: не найден Lecture05_All_In_One.py")
            return False
        print("✓ Окружение проверено успешно")
        return True

    def install_dependencies(self) -> bool:
        # Используются только модули стандартной библиотеки Python.
        print("Внешние зависимости отсутствуют: установка не нужна")
        return True

    def deploy_files(self) -> bool:
        print("Копирование файлов...")
        try:
            self.deploy_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(
                self.project_path / "Lecture05_All_In_One.py",
                self.deploy_path / "Lecture05_All_In_One.py",
            )
            config = {
                "database_path": str(self.deploy_path / "tasks.db"),
                "log_level": "INFO",
                "max_users": 100,
            }
            (self.deploy_path / "config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print("✓ Исходный файл и config.json скопированы")
            return True
        except OSError as exc:
            print(f"Ошибка при копировании файлов: {exc}")
            return False

    def run_tests(self) -> bool:
        print("Запуск тестов из развёрнутого файла...")
        try:
            result = subprocess.run(
                [sys.executable, str(self.deploy_path / "Lecture05_All_In_One.py"), "--tests"],
                cwd=self.deploy_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            print(result.stdout)
            print(result.stderr)
            if result.returncode == 0:
                print("✓ Все тесты пройдены успешно")
                return True
            print("Не все тесты пройдены")
            return False
        except OSError as exc:
            print(f"Ошибка при запуске тестов: {exc}")
            return False

    def deploy(self) -> bool:
        print("Начало процесса развёртывания...")
        steps = [
            ("Проверка окружения", self.validate_environment),
            ("Проверка зависимостей", self.install_dependencies),
            ("Копирование файлов", self.deploy_files),
            ("Запуск тестов", self.run_tests),
        ]
        for title, action in steps:
            print(f"\n--- {title} ---")
            if not action():
                print(f"Развёртывание остановлено на этапе: {title}")
                return False
        print(f"\nРазвёртывание завершено: {self.deploy_path}")
        return True


def demo_deployment():
    project_path = Path(__file__).resolve().parent
    deploy_path = project_path / "deploy"
    return DeploymentManager(str(project_path), str(deploy_path)).deploy()



# ================== 2.6 СОПРОВОЖДЕНИЕ ==================

class MonitoringSystem:
    """Система мониторинга для сопровождения ПО"""

    def __init__(self):
        self.setup_logging()
        self.performance_metrics: Dict[str, list] = {
            'response_times': [],
            'error_count': 0,
            'tasks_created': 0
        }

    def setup_logging(self):
        """Настройка системы логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('TaskManager')

    def log_operation(self, operation: str, duration: float = None, success: bool = True):
        """Логирование операций"""
        if duration is not None:
            self.performance_metrics['response_times'].append(duration)

        if not success:
            self.performance_metrics['error_count'] += 1

        if operation == 'create_task':
            self.performance_metrics['tasks_created'] += 1

        level = logging.INFO if success else logging.ERROR
        duration_text = f"{duration:.3f}s" if duration is not None else "нет данных"
        message = f"Operation: {operation}, Duration: {duration_text}, Success: {success}"
        self.logger.log(level, message)

    @staticmethod
    def measure_performance(operation_name: str):
        """Декоратор методов MonitoredTaskManager.

        Адаптация примера лекции: монитор берётся у экземпляра менеджера,
        поэтому декоратор корректно работает при создании класса.
        """
        def decorator(func):
            @wraps(func)
            def wrapper(manager, *args, **kwargs):
                start_time = time.perf_counter()
                try:
                    result = func(manager, *args, **kwargs)
                except Exception as exc:
                    duration = time.perf_counter() - start_time
                    manager.monitor.log_operation(operation_name, duration, False)
                    manager.monitor.logger.error(f"Error in {operation_name}: {exc}")
                    raise
                duration = time.perf_counter() - start_time
                manager.monitor.log_operation(operation_name, duration, result is not False)
                return result
            return wrapper
        return decorator

    def generate_maintenance_report(self) -> Dict[str, Any]:
        """Генерация отчета для сопровождения"""
        response_times = self.performance_metrics['response_times']
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        report = {
            'timestamp': datetime.now().isoformat(),
            'performance_metrics': {
                'average_response_time': avg_response_time,
                'total_operations': len(response_times),
                'error_rate': self.performance_metrics['error_count'] / max(len(response_times), 1),
                'total_tasks_created': self.performance_metrics['tasks_created']
            },
            'recommendations': self.generate_recommendations(avg_response_time)
        }
        return report

    def generate_recommendations(self, avg_response_time: float) -> List[str]:
        """Генерация рекомендаций по улучшению"""
        recommendations = []

        if avg_response_time > 1.0:
            recommendations.append("Рассмотреть оптимизацию базы данных - высокое время ответа")

        if self.performance_metrics['error_count'] > 10:
            recommendations.append("Провести анализ ошибок - высокий уровень ошибок")

        if self.performance_metrics['tasks_created'] > 1000:
            recommendations.append("Рассмотреть масштабирование системы - высокий уровень использования")

        return recommendations if recommendations else ["Система работает стабильно"]

# Модифицированный TaskManager с мониторингом
class MonitoredTaskManager(TaskManager):
    def __init__(self):
        super().__init__()
        self.monitor = MonitoringSystem()

    @MonitoringSystem.measure_performance('create_task')
    def create_task(self, title: str, description: str,
                   priority: Priority, due_date: datetime) -> Task:
        return super().create_task(title, description, priority, due_date)

    @MonitoringSystem.measure_performance('assign_task')
    def assign_task(self, task_id: int, user_id: int) -> bool:
        return super().assign_task(task_id, user_id)

# Демонстрация системы мониторинга
def demo_maintenance():
    manager = MonitoredTaskManager()

    # Имитация работы системы
    for i in range(5):
        try:
            task = manager.create_task(
                f"Тестовая задача {i}",
                "Описание",
                Priority.MEDIUM,
                datetime.now() + timedelta(days=7)
            )

            if i % 3 == 0:  # Имитация occasional ошибок
                manager.assign_task(999, 999)  # Несуществующие ID
            else:
                user = manager.create_user(f"User{i}", f"user{i}@test.com")
                manager.assign_task(task.task_id, user.user_id)

        except Exception:
            pass  # Ошибки уже залогированы

    # Генерация отчета сопровождения
    report = manager.monitor.generate_maintenance_report()
    print("Отчет сопровождения:")
    for key, value in report.items():
        print(f"{key}: {value}")


# ================== 3.1 AGILE ==================

@dataclass
class KanbanBoard:
    """Канбан-доска для Agile управления"""
    todo: List[Task]
    in_progress: List[Task]
    review: List[Task]
    done: List[Task]

    def move_task(self, task: Task, from_column: str, to_column: str):
        """Перемещение задачи между колонками"""
        # Удаляем из исходной колонки
        getattr(self, from_column).remove(task)

        # Добавляем в целевую колонку
        getattr(self, to_column).append(task)

        # Обновляем статус задачи
        status_mapping = {
            'todo': Status.TODO,
            'in_progress': Status.IN_PROGRESS,
            'review': Status.REVIEW,
            'done': Status.DONE
        }
        task.update_status(status_mapping[to_column])

    def get_board_stats(self) -> Dict:
        """Статистика по доске"""
        return {
            'todo': len(self.todo),
            'in_progress': len(self.in_progress),
            'review': len(self.review),
            'done': len(self.done),
            'completion_rate': len(self.done) / max(sum([
                len(self.todo), len(self.in_progress),
                len(self.review), len(self.done)
            ]), 1)
        }

# Небольшой демонстрационный сценарий добавлен для запуска из PyCharm.
def demo_kanban():
    task = Task(
        1, "Подготовить отчёт", "Пример Agile-доски",
        Priority.MEDIUM, datetime.now() + timedelta(days=3)
    )
    board = KanbanBoard(todo=[task], in_progress=[], review=[], done=[])
    print("Доска до перемещения:", board.get_board_stats())
    board.move_task(task, "todo", "in_progress")
    print("После перемещения:", board.get_board_stats())
    board.move_task(task, "in_progress", "review")
    board.move_task(task, "review", "done")
    print("Завершено:", board.get_board_stats())


# ---------------------- Общее меню программы ----------------------
def run_tests() -> bool:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestTaskSystem)
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    return result.wasSuccessful()


EXAMPLES = {
    "1": ("2.1 Сбор и анализ требований", demo_requirements),
    "2": ("2.2 Проектирование", demonstrate_design),
    "3": ("2.3 Реализация системы задач", demo_implementation),
    "4": ("2.4 Автоматическое тестирование", run_tests),
    "5": ("2.5 Внедрение и развёртывание", demo_deployment),
    "6": ("2.6 Сопровождение и мониторинг", demo_maintenance),
    "7": ("3.1 Agile / Канбан-доска", demo_kanban),
}


def run_example(number: str) -> bool:
    title, func = EXAMPLES[number]
    print(f"\n{'=' * 14} {title} {'=' * 14}")
    value = func()
    return value is not False


def run_all() -> bool:
    success = True
    for number in EXAMPLES:
        success = run_example(number) and success
    return success


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--tests":
            return 0 if run_tests() else 1
        if arg == "--all":
            return 0 if run_all() else 1
        if arg.startswith("--part=") and arg.split("=", 1)[1] in EXAMPLES:
            return 0 if run_example(arg.split("=", 1)[1]) else 1
        print("Допустимые аргументы: --tests, --all, --part=1 ... --part=7")
        return 2

    while True:
        print("\nЛЕКЦИЯ №5 — ПРИМЕРЫ КОДА В ОДНОМ ФАЙЛЕ")
        for number, (title, _) in EXAMPLES.items():
            print(f"{number} — {title}")
        print("8 — Запустить все примеры")
        print("0 — Выход")
        try:
            choice = input("Выберите действие: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nЗавершение программы")
            return 0
        if choice == "0":
            print("Готово")
            return 0
        if choice == "8":
            run_all()
        elif choice in EXAMPLES:
            run_example(choice)
        else:
            print("Нет такого пункта меню")


if __name__ == "__main__":
    raise SystemExit(main())
