# src/dataset.py

import pandas as pd
import torch

from torch.utils.data import Dataset
from transformers import AutoTokenizer

from config import MODEL_NAME, MAX_LENGTH, LABELS


class RequestDataset(Dataset):
    def __init__(
        self,
        csv_path: str,
        tokenizer=None,
        max_length: int = MAX_LENGTH,
    ):
        self.data = pd.read_csv(csv_path)

        self.tokenizer = tokenizer or AutoTokenizer.from_pretrained(
            MODEL_NAME
        )

        self.max_length = max_length

        self.label_columns = [
            "language",
            "urgency",
            "complexity",
            "estimated_effort",
        ]

        required_columns = ["text"] + self.label_columns

        missing = set(required_columns) - set(self.data.columns)

        if missing:
            raise ValueError(
                f"В CSV отсутствуют колонки: {sorted(missing)}"
            )

        self.data = self.data.dropna(
            subset=required_columns
        ).reset_index(drop=True)

        if self.data.empty:
            raise ValueError("В датасете нет размеченных заявок")

        self._encode_labels()

    def _encode_labels(self):
        for column in self.label_columns:
            mapping = LABELS[column]

            unknown = set(self.data[column].unique()) - set(mapping)

            if unknown:
                raise ValueError(
                    f"Неизвестные метки в {column}: {unknown}"
                )

            self.data[column] = self.data[column].map(mapping)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        row = self.data.iloc[index]

        text = str(row["text"])

        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )

        item = {
            key: value.squeeze(0)
            for key, value in encoding.items()
        }

        item["labels"] = {
            column: torch.tensor(
                int(row[column]),
                dtype=torch.long,
            )
            for column in self.label_columns
        }

        return item