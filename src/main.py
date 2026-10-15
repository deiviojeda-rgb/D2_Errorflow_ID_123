"""Точка входа. Этот файл уже готов, менять его не нужно.

Он разбирает аргументы запуска, вызывает функции из bank.py и печатает
результат. Сам банк он не читает и ничего не считает: это работа bank.py.

    python3 src/main.py ПУТЬ_К_БАНКУ              сколько вопросов
    python3 src/main.py ПУТЬ_К_БАНКУ --show ID    показать вопрос
    python3 src/main.py ПУТЬ_К_БАНКУ --stats      сколько вопросов каких
    python3 src/main.py ПУТЬ_К_БАНКУ --matrix     таблица тем и уровней
"""

import sys

import bank


def show(questions, raw_id):
    question = None
    if raw_id.isdigit():
        question = bank.find_question(questions, int(raw_id))
    if question is None:
        print("Нет вопроса с id " + raw_id)
        return 1
    for line in bank.question_lines(question):
        print(line)
    return 0


def stats(questions):
    levels = bank.count_levels(questions)
    for level in [1, 2, 3, 4, 5]:
        print("Уровень %d: %d" % (level, levels.get(level, 0)))
    topics = bank.count_topics(questions)
    for topic in bank.TOPICS:
        print("%s: %d" % (topic, topics.get(topic, 0)))
    return 0


def matrix(questions):
    table = bank.count_matrix(questions)
    print("\t".join(["тема", "1", "2", "3", "4", "5"]))
    for topic in bank.TOPICS:
        row = [topic]
        for level in [1, 2, 3, 4, 5]:
            row.append(str(table.get(topic, {}).get(level, 0)))
        print("\t".join(row))
    return 0


def main():
    if len(sys.argv) < 2:
        print("Запуск: python3 src/main.py ПУТЬ_К_БАНКУ")
        return 1
    path = sys.argv[1]
    flags = sys.argv[2:]
    try:
        questions, skipped = bank.load_bank(path)
    except FileNotFoundError:
        print("Файл не найден: " + path)
        return 1

    if not flags:
        print("Вопросов: %d" % len(questions))
        if skipped > 0:
            print("Пропущено строк: %d" % skipped)
        return 0
    if flags[0] == "--show":
        raw_id = flags[1] if len(flags) > 1 else ""
        return show(questions, raw_id)
    if flags[0] == "--stats":
        return stats(questions)
    if flags[0] == "--matrix":
        return matrix(questions)
    print("Неизвестный флаг: " + flags[0])
    return 1


if __name__ == "__main__":
    sys.exit(main())
