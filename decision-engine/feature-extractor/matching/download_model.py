
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_PATH = "models/paraphrase-multilingual-MiniLM-L12-v2"

print("Скачиваем модель...")

model = SentenceTransformer(MODEL_NAME)
model.save(MODEL_PATH)

print(f"Модель сохранена локально: {MODEL_PATH}")