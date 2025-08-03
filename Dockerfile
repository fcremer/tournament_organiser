FROM python:3.12-slim

# System-Pakete minimal halten
RUN pip install --no-cache-dir flask pyyaml

WORKDIR /app
COPY app.py .

ENV FLASK_RUN_PORT=5000 \
    FLASK_APP=app:app \
    FLASK_RUN_HOST=0.0.0.0

EXPOSE 5000
CMD ["python", "app.py"]