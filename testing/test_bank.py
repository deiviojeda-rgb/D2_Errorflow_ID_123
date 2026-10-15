"""Тесты для src/bank.py. Выданная программа: читать можно, менять нельзя.

Запуск из корня репозитория:

    python3 tests/test_bank.py        все задания
    python3 tests/test_bank.py 2      только Задание 2

Тесты вызывают функции из src/bank.py и сравнивают, что они вернули,
с тем, что должно получиться. Для каждого задания печатается одна строка:
«пройдено», «не пройдено» с первой найденной причиной или «не начато».
"""

import os
import sys
import tempfile

sys.path.insert(0, "src")

BANK = os.path.join("datasets", "bank.csv")
DIRTY = os.path.join("datasets", "bank_dirty.csv")
HEADER = "id;тема;уровень;тип;вопрос;варианты;ответ"
KEYS = ["id", "topic", "level", "type", "text", "options", "answer"]

SMALL = [
    HEADER,
    "7;числа;3;один;Сколько будет 2 + 2?;3|4|5;2",
    "8;ошибки;3;короткий;Что напечатает код?\\nprint(1)\\nprint(2);;2",
    "9;числа;5;несколько;Какие числа чётные?;2|3|4;1,3",
]
SMALL_DIRTY = [
    HEADER,
    "7;числа;3;один;Сколько будет 2 + 2?;3|4|5;2",
    "",
    "10;числа;1;короткий;Два поля лишние;;1;x;y",
    "  ",
    "11;числа;0;короткий;Нулевой уровень?;;0",
    "12;строки;три;короткий;Уровень словом?;;да",
    "9;числа;5;несколько;Какие числа чётные?;2|3|4;1,3",
]


class NotStarted(Exception):
    pass


class Failed(Exception):
    pass


def expect(condition, message):
    if not condition:
        raise Failed(message)


def write_temp(lines):
    handle, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(handle, "w", encoding="utf-8") as target:
        target.write("\n".join(lines) + "\n")
    return path


def load(bank, path):
    result = bank.load_bank(path)
    expect(isinstance(result, tuple) and len(result) == 2,
           "load_bank должна возвращать два значения: список вопросов и число пропущенных")
    questions, skipped = result
    expect(isinstance(questions, list), "первое значение load_bank должно быть списком")
    return questions, skipped


def by_id(questions, qid):
    for question in questions:
        if isinstance(question, dict) and question.get("id") == qid:
            return question
    raise Failed("в списке нет вопроса с \"id\" = %d (id должен быть числом)" % qid)


def task_1(bank):
    questions, skipped = load(bank, BANK)
    if questions == [] and skipped == 0:
        raise NotStarted()
    expect(len(questions) == 40, "из datasets/bank.csv прочитано %d вопросов, а их 40"
           % len(questions))
    expect(skipped == 0, "в datasets/bank.csv нет испорченных строк, а пропущено %s" % skipped)
    first = questions[0]
    expect(isinstance(first, dict), "вопрос должен быть словарём")
    expect(sorted(first) == sorted(KEYS),
           "у вопроса должны быть ключи %s" % ", ".join(KEYS))
    expect(first["id"] == 1 and first["level"] == 1,
           "\"id\" и \"level\" должны быть числами: у первого вопроса 1 и 1")
    expect(first["topic"] == "строки" and first["type"] == "один" and first["answer"] == "2",
           "у первого вопроса тема «строки», тип «один», ответ «2»")
    path = write_temp(SMALL)
    try:
        small, _ = load(bank, path)
    finally:
        os.remove(path)
    expect(len(small) == 3, "в файле из трёх вопросов прочитано %d — число вопросов не должно "
           "быть вписано в код" % len(small))
    try:
        bank.load_bank(os.path.join("datasets", "нет_такого_файла.csv"))
    except FileNotFoundError:
        return
    raise Failed("на несуществующем файле load_bank должна дать ошибку FileNotFoundError, "
                 "чтобы main.py сообщил «Файл не найден»")


def task_2(bank):
    if bank.find_question([], 1) is None and bank.question_lines({"text": "a", "options": []}) == []:
        raise NotStarted()
    questions, _ = load(bank, BANK)
    q1 = by_id(questions, 1)
    q23 = by_id(questions, 23)
    expect(q1["options"] == ["print", "input", "int", "len"],
           "у вопроса 1 \"options\" должен быть списком из четырёх вариантов")
    expect(q23["options"] == [], "у вопроса типа «короткий» \"options\" — пустой список")
    expect(q23["text"] == "Что напечатает код?\nitems = [3, 1, 2]\nprint(items[0])",
           "в \"text\" символы \\n из файла должны стать настоящими переносами строки")
    found = bank.find_question(questions, 23)
    expect(isinstance(found, dict) and found.get("id") == 23,
           "find_question(вопросы, 23) должна вернуть вопрос с id 23")
    expect(bank.find_question(questions, 99) is None,
           "find_question(вопросы, 99) должна вернуть None: такого вопроса нет")
    expect(bank.question_lines(q1) == ["Какая функция читает строку, которую ввёл человек?",
                                       "1) print", "2) input", "3) int", "4) len"],
           "question_lines для вопроса 1: текст, затем варианты «1) print» … «4) len»")
    expect(bank.question_lines(q23) == ["Что напечатает код?", "items = [3, 1, 2]",
                                        "print(items[0])"],
           "question_lines для вопроса 23: три строки текста, вариантов нет")


def task_3(bank):
    if bank.count_levels([]) == {} and bank.count_topics([]) == {} and \
            bank.count_levels([{"level": 1, "topic": "строки"}]) == {}:
        raise NotStarted()
    questions, _ = load(bank, BANK)
    levels = bank.count_levels(questions)
    topics = bank.count_topics(questions)
    expect(levels == {1: 10, 2: 9, 3: 8, 4: 7, 5: 6},
           "count_levels на datasets/bank.csv вернула %s" % levels)
    expect(topics == {"строки": 12, "числа": 10, "списки": 9, "ошибки": 9},
           "count_topics на datasets/bank.csv вернула %s" % topics)
    path = write_temp(SMALL)
    try:
        small, _ = load(bank, path)
    finally:
        os.remove(path)
    small_levels = {key: value for key, value in bank.count_levels(small).items() if value}
    small_topics = {key: value for key, value in bank.count_topics(small).items() if value}
    expect(small_levels == {3: 2, 5: 1},
           "на маленьком банке count_levels должна дать 2 вопроса уровня 3 и 1 — уровня 5")
    expect(small_topics == {"числа": 2, "ошибки": 1},
           "на маленьком банке count_topics должна дать 2 вопроса «числа» и 1 — «ошибки»")


def task_4(bank):
    questions, skipped = load(bank, BANK)
    if questions == [] and skipped == 0:
        raise NotStarted()
    dirty, dirty_skipped = load(bank, DIRTY)
    expect(len(dirty) == 40, "из datasets/bank_dirty.csv должно остаться 40 вопросов, а осталось %d"
           % len(dirty))
    expect(dirty_skipped == 6, "в datasets/bank_dirty.csv 6 испорченных строк, а пропущено %s"
           % dirty_skipped)
    path = write_temp(SMALL_DIRTY)
    try:
        small, small_skipped = load(bank, path)
    finally:
        os.remove(path)
    expect([q.get("id") for q in small] == [7, 9],
           "в маленьком испорченном банке должны остаться вопросы 7 и 9")
    expect(small_skipped == 5, "в маленьком испорченном банке 5 испорченных строк, а пропущено %s"
           % small_skipped)


def task_7(bank):
    if bank.count_matrix([]) == {} and bank.count_matrix([{"level": 1, "topic": "строки"}]) == {}:
        raise NotStarted()
    questions, _ = load(bank, BANK)
    table = bank.count_matrix(questions)
    expected = {"строки": [4, 2, 3, 3, 0], "числа": [3, 3, 0, 2, 2],
                "списки": [0, 2, 3, 2, 2], "ошибки": [3, 2, 2, 0, 2]}
    for topic, row in expected.items():
        got = [table.get(topic, {}).get(level, 0) for level in [1, 2, 3, 4, 5]]
        expect(got == row, "count_matrix: для темы «%s» получилось %s, а должно быть %s"
               % (topic, got, row))


TASKS = [(1, "Задание 1", task_1), (2, "Задание 2", task_2), (3, "Задание 3", task_3),
         (4, "Задание 4", task_4), (7, "Задание 7 (дополнительное)", task_7)]


def main():
    if not os.path.isfile(os.path.join("src", "bank.py")):
        print("Нет файла src/bank.py. Запускай тесты из корня репозитория.")
        return 1
    try:
        import bank
    except Exception as error:
        print("src/bank.py не загружается: %s: %s" % (type(error).__name__, error))
        return 1
    only = sys.argv[1] if len(sys.argv) > 1 else None
    chosen = [task for task in TASKS if only is None or str(task[0]) == only]
    if not chosen:
        print("Тесты есть для заданий 1, 2, 3, 4 и 7.")
        return 1
    passed, failed, broken = [], [], False
    for number, name, test in chosen:
        try:
            test(bank)
            passed.append(number)
            print("%s: пройдено" % name)
        except NotStarted:
            print("%s: не начато" % name)
            if number != 7:
                failed.append(number)
        except Failed as problem:
            failed.append(number)
            broken = True
            print("%s: не пройдено — %s" % (name, problem))
        except Exception as error:
            failed.append(number)
            broken = True
            print("%s: не пройдено — функция упала: %s: %s" % (name, type(error).__name__, error))
    if broken:
        print("…шум в эфире… эта функция отвечает не то. Смотри, что она возвращает. — Э.")
    if failed:
        return 1
    if only is None:
        print("Ну, самое главное уже готово. Осталось только самое сложное )) — Э.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
