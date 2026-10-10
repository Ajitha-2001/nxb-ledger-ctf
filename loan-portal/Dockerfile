FROM python:3.12-slim

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py seed_db.py ./
COPY templates ./templates
COPY static ./static

# Seed the read-only demo database at build time (fixed synthetic dataset)
RUN python3 seed_db.py

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "30", "app:app"]
