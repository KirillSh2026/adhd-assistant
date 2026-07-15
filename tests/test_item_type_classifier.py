from services.item_type_classifier import ItemTypeClassifier


def test_classifies_action_text_as_task():
    classifier = ItemTypeClassifier()

    assert classifier.classify("Купить молоко и хлеб") == "task"


def test_classifies_idea_text_as_idea():
    classifier = ItemTypeClassifier()

    assert classifier.classify("Идея: можно сделать отдельный экран фокуса") == "idea"


def test_classifies_neutral_text_as_note():
    classifier = ItemTypeClassifier()

    assert classifier.classify("Сегодня был сложный день, много отвлекался") == "note"
