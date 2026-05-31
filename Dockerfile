FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY examples/ ./examples/
COPY .env.example ./env.example

RUN chmod +x scripts/*.sh
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "signal_watcher", "--config", "config.yaml", "--watch"]
