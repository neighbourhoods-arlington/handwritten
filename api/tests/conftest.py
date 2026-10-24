import os

# Тест орчин: DB/Ollama-д бодитоор холбогдохгүй тестүүдэд default тохиргоо хангалттай
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")
