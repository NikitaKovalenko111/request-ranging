
from pathlib import Path

from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
MODEL_PATH = (
    PROJECT_ROOT
    / 'models'
    / 'feature-extractor'
    / 'matching'
    / 'paraphrase-multilingual-MiniLM-L12-v2'
)

print("Скачиваем модель...")

model = SentenceTransformer(MODEL_NAME)
model.save(MODEL_PATH)

print(f"Модель сохранена локально: {MODEL_PATH}")
