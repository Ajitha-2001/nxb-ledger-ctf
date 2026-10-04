FROM python:3.12-slim

WORKDIR /app
RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

USER appuser
EXPOSE 5000
# ONE worker + threads: the rate limiter keeps its state in process memory, so several worker
# processes would each keep separate counters and multiply the allowed attempts.
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:5000", "--timeout", "30", "app:app"]
