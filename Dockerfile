FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs downloads config data && chmod 755 logs downloads config data

ENV PYTHONUNBUFFERED=1
ENV LOG_DIR=/app/logs
ENV DOWNLOAD_PATH=/app/downloads/
ENV DATABASE_PATH=/app/data/history.db

CMD ["python", "run_bot.py"]
