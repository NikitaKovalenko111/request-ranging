# src/predict.py
# Запуск из корня classifier:
#   python -m decision_engine.feature_extractor.classifier.predict
#
# Использование из другого Python-кода:
#   from decision_engine.feature_extractor.classifier.predict import RequestPredictor
#   predictor = RequestPredictor()
#   result = predictor.predict("Не работает авторизация...")
#   print(result)

import json
from pathlib import Path
from typing import Dict

import torch
from transformers import AutoTokenizer

from .config import MAX_LENGTH, MODEL_DIR, MODEL_NAME
from .model import RequestClassifier


DEFAULT_MODEL_DIR = MODEL_DIR / 'best'


class RequestPredictor:
    def __init__(self, model_dir: Path = DEFAULT_MODEL_DIR, device=None):
        self.model_dir = Path(model_dir)
        weights_path = self.model_dir / "model.pt"
        labels_path = self.model_dir / "labels.json"

        if not weights_path.exists():
            raise FileNotFoundError(
                f"Не найдены веса модели: {weights_path}. "
                "Сначала обучи модель командой decision-feature-train."
            )

        if not labels_path.exists():
            raise FileNotFoundError(
                f"Не найден файл меток: {labels_path}"
            )

        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        with labels_path.open("r", encoding="utf-8") as f:
            self.labels = json.load(f)

        print(f"Устройство инференса: {self.device}", flush=True)
        print("Загрузка токенизатора...", flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)

        print("Загрузка модели...", flush=True)
        self.model = RequestClassifier(
            model_name=str(self.model_dir),
            load_pretrained=False,
        )
        state_dict = torch.load(
            weights_path,
            map_location=self.device,
        )
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()
        print("Модель готова к предсказаниям.", flush=True)

        self.max_length = MAX_LENGTH

    @torch.no_grad()
    def predict(self, text: str) -> Dict[str, str]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Текст заявки не должен быть пустым.")

        encoded = self.tokenizer(
            text.strip(),
            max_length=self.max_length,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )

        encoded = {
            key: value.to(self.device)
            for key, value in encoded.items()
        }

        output = self.model(**encoded)

        result = {}
        for task_name, logits in output["logits"].items():
            class_id = int(logits.argmax(dim=-1).item())
            id_to_label = {
                int(index): label
                for label, index in self.labels[task_name].items()
            }
            result[task_name] = id_to_label[class_id]

        return result


def main():
    predictor = RequestPredictor()

    examples = [
        '''Тема: Добавление возможности изменять подпись кнопки в личном кабинете

Описание заявки:

Необходимо внести небольшое изменение в существующий внутренний веб-интерфейс компании. Сейчас в личном кабинете пользователя есть кнопка с текстом «Отправить заявку». Требуется добавить возможность изменять текст этой кнопки через настройки интерфейса, чтобы администратор мог самостоятельно выбирать подходящую подпись без обращения к разработчикам.

На текущий момент кнопка отображается на странице создания новой заявки. Она имеет стандартный синий цвет, расположена в нижней части формы и используется для отправки заполненных данных на сервер. Логика отправки заявки уже реализована и работает корректно. Изменять обработку данных, структуру формы или серверную часть не требуется.

Нужно добавить в административный раздел небольшое поле настроек, в котором можно указать новый текст кнопки. Например, вместо «Отправить заявку» администратор сможет установить подпись «Создать обращение», «Сохранить заявку» или «Передать на обработку». После сохранения настроек новый текст должен отображаться на кнопке в пользовательском интерфейсе.

Если поле настроек оставлено пустым, необходимо использовать стандартное значение «Отправить заявку». Также следует предусмотреть ограничение длины текста, чтобы слишком длинная подпись не нарушала отображение кнопки на странице. Дополнительно нужно проверить, что текст корректно отображается на компьютерах и мобильных устройствах.

Технические требования:

Добавить поле для редактирования текста кнопки в существующий административный интерфейс.

Реализовать сохранение нового значения в уже используемом механизме настроек.

Обеспечить отображение сохранённого текста на кнопке отправки заявки.

Установить ограничение длины подписи до 40 символов.

Использовать стандартный текст, если настройка не заполнена.

Проверить корректность отображения текста на разных размерах экрана.

Не изменять существующую логику отправки заявок.

Сохранить текущие стили кнопки, включая цвет, размер и расположение.

Добавить простую проверку корректности введённого значения.

Проверить работу изменения текста после обновления страницы.

Ожидаемый результат:

Администратор может самостоятельно изменить подпись кнопки в настройках личного кабинета. Новое значение сохраняется и отображается пользователям. Если значение не задано, интерфейс продолжает использовать стандартную подпись. Все остальные функции формы работают без изменений.

Дополнительная информация:

Заявка не предполагает разработки нового модуля, изменения архитектуры приложения или интеграции со сторонними сервисами. Необходимо использовать существующие компоненты интерфейса и текущую систему хранения настроек. Работу можно выполнить в рамках небольшой доработки существующего функционала.'''
    ]

    for i, text in enumerate(examples, start=1):
        print(f"\n{'=' * 70}")

        prediction = predictor.predict(text)
        print("Предсказание:")
        print(json.dumps(prediction, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
