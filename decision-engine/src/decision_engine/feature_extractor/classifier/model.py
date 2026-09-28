# src/model.py

import torch
import torch.nn as nn

from transformers import AutoConfig, AutoModel

from .config import MODEL_NAME, NUM_LABELS


class RequestClassifier(nn.Module):
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        num_labels: dict = NUM_LABELS,
        dropout: float = 0.2,
        load_pretrained: bool = True,
    ):
        super().__init__()

        if load_pretrained:
            self.encoder = AutoModel.from_pretrained(model_name)
        else:
            self.encoder = AutoModel.from_config(
                AutoConfig.from_pretrained(model_name)
            )

        hidden_size = self.encoder.config.hidden_size

        self.dropout = nn.Dropout(dropout)

        self.heads = nn.ModuleDict({
            name: nn.Linear(hidden_size, count)
            for name, count in num_labels.items()
        })

    def forward(
        self,
        input_ids,
        attention_mask,
        token_type_ids=None,
        labels=None,
    ):
        encoder_inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }

        if (
            token_type_ids is not None
            and "token_type_ids" in self.encoder.forward.__code__.co_varnames
        ):
            encoder_inputs["token_type_ids"] = token_type_ids

        outputs = self.encoder(**encoder_inputs)

        # Вектор первого токена [CLS] / первого токена модели
        pooled = outputs.last_hidden_state[:, 0]

        pooled = self.dropout(pooled)

        logits = {
            name: head(pooled)
            for name, head in self.heads.items()
        }

        loss = None

        if labels is not None:
            losses = []

            for name, head_logits in logits.items():
                target = labels[name]

                losses.append(
                    nn.functional.cross_entropy(
                        head_logits,
                        target,
                    )
                )

            loss = torch.stack(losses).mean()

        return {
            "loss": loss,
            "logits": logits,
        }
