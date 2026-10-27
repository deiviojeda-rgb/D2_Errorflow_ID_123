"""Банк вопросов: чтение файла и подсчёты.

Этот модуль ничего не печатает. Он возвращает результат, а печатает main.py.
Названия функций и то, что они принимают, менять нельзя: их вызывают
main.py и тесты. Меняй только тела функций — то, что под описанием.

Пока тела не написаны, функции возвращают пустые значения: программа
запускается, но отвечает нулями.
"""

# Э.: начни с одной строки. Разбери её на поля — остальные сорок устроены так же.

TOPICS = ["строки", "числа", "списки", "ошибки"]

def load_bank(path):
    with open(path, encoding="utf-8") as source:
        text = source.read()
        lines = text.split("\n")
        lines.pop(0)
        if lines and lines[-1] == "":
            lines.pop()
    question_list=[]
    for item in range(len(lines)):
        one_line = lines[item].split(";")

        if one_line[5] == "":
            question_list.append({
                "id": int(one_line[0]),
                "topic": one_line [1],
                "level": int(one_line[2]),
                "type": (one_line[3]),
                "text": one_line[4].replace("\\n", "\n"),
                "options":[],
                "answer": one_line[6]
            })
        else: question_list.append({
                "id": int(one_line[0]),
                "topic": one_line [1],
                "level": int(one_line[2]),
                "type": (one_line[3]),
                "text": one_line[4].replace("\\n", "\n"),
                "options":one_line[5].split("|"),
                "answer": one_line[6]
            })
    return question_list, 0


def find_question(questions, qid):
    """Найти в списке questions вопрос с номером qid (число).

    Возвращает словарь этого вопроса или None, если такого номера нет.
    """
    return None


def question_lines(question):
    """Строки, которые увидит человек на экзамене, — списком.

    Сначала строки текста вопроса, потом варианты: "1) ...", "2) ..." и так далее.
    Тема, уровень и ответ в эти строки не попадают.
    """
    return []


def count_levels(questions):
    """Сколько вопросов на каждом уровне.

    Возвращает словарь {уровень: число}, например {1: 10, 2: 9, ...}.
    """
    return {}


def count_topics(questions):
    """Сколько вопросов в каждой теме.

    Возвращает словарь {тема: число}, например {"строки": 12, ...}.
    """
    return {}


def count_matrix(questions):
    """Задание 8 (дополнительное). Сколько вопросов каждой темы на каждом уровне.

    Возвращает словарь словарей {тема: {уровень: число}},
    например {"строки": {1: 4, 2: 2, ...}, ...}.
    """
    return {}
