"""Консольное приложение для работы с задачами и учёта времени."""

from datetime import datetime, timedelta

from storage import load_data, save_data
from task_manager import Priority
from reward_system import RewardSystem
from time_tracker import format_duration


def show_tasks(manager, tracker) -> None:
    if not manager.tasks:
        print("Задач пока нет. Создайте первую задачу (пункт 1).")
        return
    print("\n--- СПИСОК ЗАДАЧ ---")
    for task in sorted(manager.tasks.values(), key=lambda t: t.task_id):
        active = " [ТАЙМЕР ИДЁТ]" if tracker.is_running(task.task_id) else ""
        reward = (f" | Премия: {task.reward_points} баллов"
                  if task.completed_at else "")
        print(f"{task.task_id}. {task.title} | {task.status.value} | "
              f"Время: {format_duration(tracker.get_total_seconds(task.task_id))}{active}{reward}")


def create_task(manager) -> None:
    title = input("Название задачи: ").strip()
    description = input("Описание (можно пропустить): ").strip()
    print("Приоритет: 1 - низкий; 2 - средний; 3 - высокий; 4 - критический")
    priority = Priority(int(input("Выберите приоритет [1-4]: ")))
    days_raw = input("Срок выполнения через сколько дней? [по умолчанию 7]: ").strip()
    days = int(days_raw) if days_raw else 7
    if days < 0:
        raise ValueError("Срок не может быть отрицательным")
    task = manager.create_task(title, description, priority,
                               datetime.now() + timedelta(days=days))
    print(f"Задача создана. Её ID: {task.task_id}")


def create_user_and_assign(manager) -> None:
    if not manager.tasks:
        print("Сначала создайте задачу.")
        return
    task_id = int(input("ID задачи для назначения: "))
    if task_id not in manager.tasks:
        raise ValueError("Задача не найдена")
    name = input("Имя исполнителя: ").strip()
    email = input("Email исполнителя: ").strip()
    user = next((u for u in manager.users.values() if u.email == email), None)
    if user is None:
        user = manager.create_user(name, email)
    if not manager.assign_task(task_id, user.user_id):
        raise ValueError("Нельзя изменить исполнителя завершённой задачи")
    print(f"Задача {task_id} назначена: {user.name}")


def show_report(tracker) -> None:
    report = tracker.generate_report()
    print("\n--- ОТЧЁТ ПО ВРЕМЕНИ ---")
    print("Сформирован:", report["generated_at"])
    for row in report["tasks"]:
        active = " (таймер работает)" if row["running"] else ""
        print(f"{row['task_id']}. {row['title']} — {row['total_time']} "
              f"| запусков: {row['sessions_count']} "
              f"| исполнитель: {row['assignee']}{active}")
    print("ОБЩЕЕ ВРЕМЯ:", report["total_time"])


def main() -> None:
    try:
        manager, tracker = load_data()
    except (OSError, ValueError, KeyError) as error:
        print(f"Не удалось загрузить сохранённые данные: {error}")
        return
    rewards = RewardSystem(manager, tracker)
    print("СИСТЕМА УПРАВЛЕНИЯ ЗАДАЧАМИ — УЧЁТ ВРЕМЕНИ И ПРЕМИРОВАНИЕ")
    while True:
        print("\n1 - Создать задачу")
        print("2 - Показать задачи")
        print("3 - Запустить таймер")
        print("4 - Остановить таймер")
        print("5 - Показать отчёт")
        print("6 - Экспортировать отчёт в CSV")
        print("7 - Назначить исполнителя задачи")
        print("8 - Завершить задачу и начислить премиальные баллы")
        print("9 - Показать рейтинг сотрудников")
        print("10 - Экспортировать рейтинг в CSV")
        print("0 - Выход")
        choice = input("Выберите действие: ").strip()
        try:
            if choice == "1":
                create_task(manager)
                save_data(manager, tracker)
            elif choice == "2":
                show_tasks(manager, tracker)
            elif choice == "3":
                task_id = int(input("ID задачи: "))
                tracker.start_timer(task_id)
                save_data(manager, tracker)
                print(f"Таймер задачи {task_id} запущен.")
            elif choice == "4":
                task_id = int(input("ID задачи: "))
                elapsed = tracker.stop_timer(task_id)
                save_data(manager, tracker)
                print(f"Таймер остановлен. Сеанс: {format_duration(elapsed)}")
                print(f"Всего по задаче: {format_duration(tracker.get_total_seconds(task_id))}")
            elif choice == "5":
                show_report(tracker)
            elif choice == "6":
                path = tracker.export_csv("time_report.csv")
                print(f"Отчёт сохранён: {path.resolve()}")
            elif choice == "7":
                create_user_and_assign(manager)
                save_data(manager, tracker)
            elif choice == "8":
                task_id = int(input("ID завершённой задачи: "))
                result = rewards.complete_task(task_id)
                save_data(manager, tracker)
                print(f"Задача завершена. Исполнитель: {result['employee']}")
                print(f"Премия: +{result['points']} баллов. {result['reason']}")
            elif choice == "9":
                print("\n--- РЕЙТИНГ СОТРУДНИКОВ ---")
                leaderboard = rewards.get_leaderboard()
                if not leaderboard:
                    print("Сотрудников пока нет. Назначьте исполнителя через пункт 7.")
                for place, person in enumerate(leaderboard, 1):
                    print(f"{place}. {person['name']} | "
                          f"баллов: {person['points']} | "
                          f"выполнено задач: {person['completed_count']}")
            elif choice == "10":
                path = rewards.export_csv()
                print(f"Рейтинг сохранён: {path.resolve()}")
            elif choice == "0":
                save_data(manager, tracker)
                print("Данные сохранены. До свидания!")
                break
            else:
                print("Нет такого пункта меню.")
        except (ValueError, OSError) as error:
            print(f"Ошибка: {error}")


if __name__ == "__main__":
    main()
