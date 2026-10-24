import os

# Test environment: defaults are enough for tests that do not hit a real DB/Ollama
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")
