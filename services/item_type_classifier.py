from __future__ import annotations


SUPPORTED_ITEM_TYPES = {"task", "note", "idea"}

TASK_MARKERS = {
    "todo",
    "buy",
    "call",
    "send",
    "finish",
    "plan",
    "pay",
    "book",
    "remember",
    "need to",
    "must",
    "should",
    "купить",
    "сделать",
    "доделать",
    "позвонить",
    "написать",
    "отправить",
    "записаться",
    "оплатить",
    "проверить",
    "подготовить",
    "встретиться",
    "созвониться",
    "не забыть",
    "нужно",
    "надо",
    "задача",
}

IDEA_MARKERS = {
    "idea",
    "maybe",
    "could",
    "might",
    "what if",
    "concept",
    "hypothesis",
    "brainstorm",
    "идея",
    "придумать",
    "можно",
    "возможно",
    "гипотеза",
    "концепция",
    "улучшить",
    "попробовать",
    "хочу сделать",
    "было бы",
}


class ItemTypeClassifier:
    def classify(self, text: str) -> str:
        normalized = " ".join(text.lower().strip().split())
        if not normalized:
            return "note"

        task_score = self._score(normalized, TASK_MARKERS)
        idea_score = self._score(normalized, IDEA_MARKERS)

        if self._looks_like_task(normalized):
            task_score += 2
        if self._looks_like_idea(normalized):
            idea_score += 2

        if task_score > idea_score and task_score > 0:
            return "task"
        if idea_score > task_score and idea_score > 0:
            return "idea"
        return "note"

    def _score(self, text: str, markers: set[str]) -> int:
        return sum(1 for marker in markers if marker in text)

    def _looks_like_task(self, text: str) -> bool:
        task_prefixes = (
            "купить ",
            "сделать ",
            "доделать ",
            "позвонить ",
            "написать ",
            "отправить ",
            "записаться ",
            "оплатить ",
            "проверить ",
            "подготовить ",
            "finish ",
            "buy ",
            "call ",
            "send ",
            "pay ",
            "book ",
            "remember ",
        )
        return text.startswith(task_prefixes)

    def _looks_like_idea(self, text: str) -> bool:
        idea_prefixes = (
            "идея",
            "можно",
            "возможно",
            "хочу сделать",
            "было бы",
            "idea",
            "maybe",
            "what if",
        )
        return text.startswith(idea_prefixes) or text.endswith("?")
