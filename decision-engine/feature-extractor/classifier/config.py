# config.py

MODEL_NAME = "distilbert-base-multilingual-cased"

MAX_LENGTH = 512
BATCH_SIZE = 16
LEARNING_RATE = 2e-5
EPOCHS = 3

LABELS = {
    "language": {
        "ru": 0,
        "en": 1,
    },
    "urgency": {
        "low": 0,
        "normal": 1,
        "high": 2,
        "critical": 3,
    },
    "complexity": {
        "simple": 0,
        "medium": 1,
        "complex": 2,
        "very_complex": 3,
    },
    "estimated_effort": {
        "up_to_1h": 0,
        "1_to_4h": 1,
        "4_to_8h": 2,
        "over_8h": 3,
    },
}

NUM_LABELS = {
    name: len(labels)
    for name, labels in LABELS.items()
}