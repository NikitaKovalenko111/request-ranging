# src/test.py
# Запуск из корня classifier: python -m src.test

import torch
from torch.utils.data import DataLoader

from config import MODEL_NAME, MAX_LENGTH, BATCH_SIZE, LABELS
from src.dataset import RequestDataset
from src.model import RequestClassifier
from src.metrics import calculate_metrics

TEST_PATH = "data/test.csv"
MODEL_PATH = "models/best/model.pt"
NUM_WORKERS = 0


def move_labels_to_device(labels, device):
    return {name: value.to(device) for name, value in labels.items()}


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Устройство: {device}", flush=True)

    print(f"Загрузка тестового датасета: {TEST_PATH}", flush=True)
    dataset = RequestDataset(TEST_PATH, max_length=MAX_LENGTH)
    loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
    )
    print(f"Тестовых заявок: {len(dataset)}", flush=True)

    print("Загрузка модели...", flush=True)
    model = RequestClassifier(model_name=MODEL_NAME)
    state_dict = torch.load(MODEL_PATH, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    print("Модель загружена.", flush=True)

    y_true = {name: [] for name in LABELS}
    y_pred = {name: [] for name in LABELS}
    total_loss = 0.0
    total_samples = 0

    print("Запуск тестирования...", flush=True)
    with torch.no_grad():
        for step, batch in enumerate(loader, start=1):
            labels = move_labels_to_device(batch.pop("labels"), device)
            batch = {key: value.to(device) for key, value in batch.items()}
            output = model(**batch, labels=labels)

            batch_size = batch["input_ids"].size(0)
            total_loss += output["loss"].item() * batch_size
            total_samples += batch_size

            for name, logits in output["logits"].items():
                y_true[name].extend(labels[name].cpu().tolist())
                y_pred[name].extend(logits.argmax(dim=-1).cpu().tolist())

            print(f"Тестирование: batch {step}/{len(loader)}", flush=True)

    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ НА TEST.CSV")
    print("=" * 60)
    print(f"Test loss: {total_loss / max(total_samples, 1):.4f}\n")

    for name in LABELS:
        metrics = calculate_metrics(y_true[name], y_pred[name])
        print(
            f"{name}: Accuracy={metrics['accuracy']:.4f}, "
            f"Macro F1={metrics['macro_f1']:.4f}"
        )

        id_to_label = {idx: label for label, idx in LABELS[name].items()}
        print("Матрица ошибок (строки — истинный класс, столбцы — предсказанный):")
        print("true/pred | " + " | ".join(id_to_label[i] for i in range(len(id_to_label))))

        matrix = [[0 for _ in range(len(id_to_label))] for _ in range(len(id_to_label))]
        for true_label, pred_label in zip(y_true[name], y_pred[name]):
            matrix[true_label][pred_label] += 1

        for i, row in enumerate(matrix):
            print(f"{id_to_label[i]:<12} | " + " | ".join(str(v) for v in row))
        print()

    print("Тестирование завершено.", flush=True)


if __name__ == "__main__":
    main()
