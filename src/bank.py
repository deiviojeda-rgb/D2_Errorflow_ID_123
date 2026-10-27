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

    count = 0
    question_list=[]
    for i in range(len(lines)):
        one_line = lines[i].split(";")

        if len(one_line) != 7 or  not one_line[2].isdigit() or int(one_line[2])>5 or int(one_line[2])<1:
            count+=1
        elif one_line[5]=="":
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

    for question in questions:
        if question["id"] == qid:
            return question

    return None


def question_lines(question):
    """Строки, которые увидит человек на экзамене, — списком.

    Сначала строки текста вопроса, потом варианты: "1) ...", "2) ..." и так далее.
    Тема, уровень и ответ в эти строки не попадают.
    """

    result = []
    for line in question["text"].split("\n"):
        result.append(line)
    counter = 1
    for option in question["options"]:
        result.append(str(counter) + ") " + option)
        counter += 1
    return result


def count_levels(questions):
    """Сколько вопросов на каждом уровне.

    Возвращает словарь {уровень: число}, например {1: 10, 2: 9, ...}.
    """
    levels = {}
    for question in questions:
        level = question["level"]
        levels[level] = levels.get(level, 0)+1
    return levels


def count_topics(questions):
    """Сколько вопросов в каждой теме.

    Возвращает словарь {тема: число}, например {"строки": 12, ...}.
    """
    topics = {}
    for question in questions:
        topic = question["topic"]
        topics[topic] = topics.get(topic, 0)+1
    return topics


def count_matrix(questions):
    """Задание 8 (дополнительное). Сколько вопросов каждой темы на каждом уровне.

    Возвращает словарь словарей {тема: {уровень: число}},
    например {"строки": {1: 4, 2: 2, ...}, ...}.
    """
    return {}
