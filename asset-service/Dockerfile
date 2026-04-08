FROM python:3.11-slim

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --create-home appuser

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

COPY app ./app

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8020

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]
