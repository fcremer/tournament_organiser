FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_RUN_PORT=5000 \
    FLASK_APP=app:app \
    FLASK_RUN_HOST=0.0.0.0

WORKDIR /app

RUN groupadd --system appuser \
    && useradd --system --gid appuser --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir --requirement requirements.txt \
    && rm requirements.txt

COPY --chown=appuser:appuser app.py data.yaml ./

USER appuser

EXPOSE 5000

CMD ["python", "app.py"]
