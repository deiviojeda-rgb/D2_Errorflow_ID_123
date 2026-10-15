"""Проверка банка вопросов. Выданная программа: читать можно, менять нельзя.

Запуск из корня репозитория:

    python3 src/partner/check_bank.py datasets/bank.csv

Если банк в порядке, программа сообщает об этом и завершается с кодом 0.
Если нет, она перечисляет найденные проблемы с номерами строк файла
и завершается с кодом 1. Правила формата описаны в materials/bank_format_rus.md.
"""

# Если ты читаешь это — ты на верном пути. — Э.

import sys

HEADER = "id;тема;уровень;тип;вопрос;варианты;ответ"
FIELDS = 7
TOPICS = ["строки", "числа", "списки", "ошибки"]
TYPES = ["один", "несколько", "короткий"]


def check_numbers(answer, count, many):
    """Проблема с ответом-номером или пустая строка, если всё в порядке."""
    parts = answer.split(",")
    if not many and len(parts) != 1:
        return "у типа «один» ответ — один номер"
    if many and len(parts) < 2:
        return "у типа «несколько» в ответе не меньше двух номеров через запятую"
    for part in parts:
        if not (part.isascii() and part.isdigit()) or part.startswith("0"):
            return ("ответ «%s»: номера пишутся цифрами через запятую, без пробелов "
                    "и без нулей в начале" % answer)
        if not 1 <= int(part) <= count:
            return "ответ «%s»: номера %s нет среди вариантов" % (answer, part)
    if len(set(parts)) != len(parts):
        return "ответ «%s»: номер повторяется" % answer
    return ""


def check_line(fields):
    """Список проблем одной строки-вопроса."""
    problems = []
    qid, topic, level, kind, text, options, answer = fields
    if not (qid.isascii() and qid.isdigit()) or int(qid) < 1 or qid.startswith("0"):
        problems.append("id «%s» должен быть целым числом больше нуля, без нулей в начале" % qid)
    if topic not in TOPICS:
        problems.append("тема «%s» не из списка: %s" % (topic, ", ".join(TOPICS)))
    if level not in ["1", "2", "3", "4", "5"]:
        problems.append("уровень «%s» должен быть числом от 1 до 5" % level)
    if kind not in TYPES:
        problems.append("тип «%s» не из списка: %s" % (kind, ", ".join(TYPES)))
    if text.strip() == "":
        problems.append("пустой текст вопроса")
    if answer.strip() == "":
        problems.append("пустой ответ")
    if kind == "короткий":
        if options != "":
            problems.append("у типа «короткий» поле вариантов должно быть пустым")
        if "" in [form.strip() for form in answer.split("|")]:
            problems.append("пустая форма ответа между символами |")
    elif kind in TYPES:
        items = options.split("|")
        if not 2 <= len(items) <= 5:
            problems.append("вариантов должно быть от 2 до 5, а их %d" % len(items))
        elif "" in [item.strip() for item in items]:
            problems.append("пустой вариант между символами |")
        elif answer.strip() != "":
            problem = check_numbers(answer, len(items), kind == "несколько")
            if problem:
                problems.append(problem)
    return problems


def main():
    if len(sys.argv) != 2:
        print("Запуск: python3 src/partner/check_bank.py ПУТЬ_К_БАНКУ")
        return 1
    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as source:
            lines = source.read().split("\n")
    except FileNotFoundError:
        print("Файл не найден: %s" % path)
        return 1
    except UnicodeDecodeError:
        print("Файл не читается как текст UTF-8: %s" % path)
        return 1
    if lines and lines[-1] == "":
        lines.pop()

    report = []
    if not lines or lines[0].rstrip("\r") != HEADER:
        report.append("Строка 1: заголовок должен быть ровно таким: " + HEADER)
    seen = {}
    questions = 0
    for number, line in enumerate(lines[1:], start=2):
        line = line.rstrip("\r")
        if line.strip() == "":
            report.append("Строка %d: пустая строка" % number)
            continue
        questions += 1
        fields = line.split(";")
        if len(fields) != FIELDS:
            report.append("Строка %d: полей %d, а должно быть %d (поля разделяются символом ;)"
                          % (number, len(fields), FIELDS))
            continue
        for problem in check_line(fields):
            report.append("Строка %d: %s" % (number, problem))
        qid = fields[0]
        if qid in seen:
            report.append("Строка %d: id %s уже был в строке %d" % (number, qid, seen[qid]))
        else:
            seen[qid] = number

    if report:
        for item in report:
            print(item)
        print("Найдено проблем: %d. Банк не в порядке." % len(report))
        return 1
    print("Банк в порядке. Вопросов: %d." % questions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
