# src/train.py

import json
import random
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer, get_linear_schedule_with_warmup

from .config import (
    MODEL_NAME,
    MAX_LENGTH,
    BATCH_SIZE,
    LEARNING_RATE,
    EPOCHS,
    LABELS,
    DATA_DIR,
    MODEL_DIR,
)
from .dataset import RequestDataset
from .model import RequestClassifier
from .metrics import calculate_metrics


TRAIN_PATH = DATA_DIR / 'train.csv'
VAL_PATH = DATA_DIR / 'val.csv'
OUTPUT_DIR = MODEL_DIR / 'best'

NUM_WORKERS = 0
SEED = 42


def set_seed(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def move_labels_to_device(labels, device):
    return {
        name: value.to(device)
        for name, value in labels.items()
    }


def evaluate(model, loader, device):
    model.eval()

    total_loss = 0.0
    total_samples = 0

    y_true = {name: [] for name in LABELS}
    y_pred = {name: [] for name in LABELS}

    with torch.no_grad():
        for batch in loader:
            labels = move_labels_to_device(
                batch.pop("labels"),
                device,
            )

            batch = {
                key: value.to(device)
                for key, value in batch.items()
            }

            output = model(
                **batch,
                labels=labels,
            )

            batch_size = batch["input_ids"].size(0)

            total_loss += output["loss"].item() * batch_size
            total_samples += batch_size

            for name, logits in output["logits"].items():
                predictions = logits.argmax(dim=-1)

                y_true[name].extend(
                    labels[name].cpu().tolist()
                )
                y_pred[name].extend(
                    predictions.cpu().tolist()
                )

    metrics = {
        name: calculate_metrics(
            y_true[name],
            y_pred[name],
        )
        for name in LABELS
    }

    return total_loss / max(total_samples, 1), metrics


def train():
    set_seed()

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print(f"Устройство: {device}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    train_dataset = RequestDataset(
        TRAIN_PATH,
        tokenizer=tokenizer,
        max_length=MAX_LENGTH,
    )

    val_dataset = RequestDataset(
        VAL_PATH,
        tokenizer=tokenizer,
        max_length=MAX_LENGTH,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
    )

    model = RequestClassifier().to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
    )

    total_steps = len(train_loader) * EPOCHS

    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * 0.1),
        num_training_steps=total_steps,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    best_val_loss = float("inf")

    for epoch in range(EPOCHS):
        model.train()

        total_loss = 0.0
        total_samples = 0

        for step, batch in enumerate(train_loader, start=1):
            labels = move_labels_to_device(
                batch.pop("labels"),
                device,
            )

            batch = {
                key: value.to(device)
                for key, value in batch.items()
            }

            optimizer.zero_grad(set_to_none=True)

            output = model(
                **batch,
                labels=labels,
            )

            loss = output["loss"]
            loss.backward()

            torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                max_norm=1.0,
            )

            optimizer.step()
            scheduler.step()

            batch_size = batch["input_ids"].size(0)

            total_loss += loss.item() * batch_size
            total_samples += batch_size

            if step % 50 == 0:
                print(
                    f"Epoch {epoch + 1}/{EPOCHS} "
                    f"| Step {step}/{len(train_loader)} "
                    f"| Loss: {loss.item():.4f}"
                )

        train_loss = total_loss / max(total_samples, 1)

        val_loss, val_metrics = evaluate(
            model,
            val_loader,
            device,
        )

        print(f"\nЭпоха {epoch + 1}/{EPOCHS}")
        print(f"Train loss: {train_loss:.4f}")
        print(f"Val loss:   {val_loss:.4f}")

        for name, values in val_metrics.items():
            print(
                f"{name}: "
                f"Accuracy={values['accuracy']:.4f}, "
                f"Macro F1={values['macro_f1']:.4f}"
            )

        if val_loss < best_val_loss:
            best_val_loss = val_loss

            torch.save(
                model.state_dict(),
                OUTPUT_DIR / "model.pt",
            )

            model.encoder.save_pretrained(OUTPUT_DIR)
            tokenizer.save_pretrained(OUTPUT_DIR)

            with open(
                OUTPUT_DIR / "labels.json",
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    LABELS,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            print("Сохранена новая лучшая модель.")

    print("\nОбучение завершено.")
    print(f"Лучшая Val loss: {best_val_loss:.4f}")
    print(f"Модель сохранена в: {OUTPUT_DIR}")


if __name__ == "__main__":
    train()
