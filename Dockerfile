FROM python:3.11-slim
WORKDIR /app

# Устанавливаем системные зависимости при необходимости
RUN pip install --no-cache-dir uvicorn[standard]

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
