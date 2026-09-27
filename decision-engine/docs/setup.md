# Установка Decision Engine

Команды ниже выполняются в PowerShell из корня репозитория.

## 1. Перейти в проект

```powershell
cd D:\Github\request-ranging\decision-engine
```

## 2. Создать виртуальное окружение

Проект рассчитан на Python 3.11 или новее. Рекомендуемая версия — Python 3.12.

```powershell
py -3.12 -m venv .venv
```

Если папка `.venv` уже существует, повторно создавать окружение не нужно.

## 3. Установить все зависимости

```powershell
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev,feature-extractor]"
```

Эта команда устанавливает:

- Rule Engine и Kafka/Redis-клиенты;
- ML Ranker и CatBoost;
- Balancer;
- библиотеки Feature Extractor: PyTorch, Transformers, Sentence Transformers и KeyBERT;
- pytest и остальные зависимости для тестирования.

## 4. Скачать модель semantic matching

```powershell
.venv\Scripts\python -m decision_engine.feature_extractor.matching.download_model
```

Модель будет сохранена в:

```text
models/feature-extractor/matching/paraphrase-multilingual-MiniLM-L12-v2/
```

## 5. Подготовить classifier

Для запуска classifier необходима обученная модель:

```text
models/feature-extractor/classifier/best/
├── model.pt
├── labels.json
└── файлы токенизатора
```

Если модели ещё нет, её можно обучить:

```powershell
.venv\Scripts\decision-feature-train
```

Обучение использует датасеты из:

```text
data/feature_extractor/classifier/
├── train.csv
├── val.csv
└── test.csv
```

## 6. Проверить установку

```powershell
.venv\Scripts\python -m pytest
```

## 7. Запустить Feature Extractor вручную

Лёгкий режим без transformer-модели:

```powershell
.venv\Scripts\python tests\feature_extractor\manual_run.py
```

Текст можно передать из UTF-8 файла:

```powershell
.venv\Scripts\python tests\feature_extractor\manual_run.py --file my_request.txt
```

Запуск с обученным classifier:

```powershell
.venv\Scripts\python tests\feature_extractor\manual_run.py --classifier
```

Тестовый текст и список исполнителей также можно изменить непосредственно в
`tests/feature_extractor/manual_run.py`.
