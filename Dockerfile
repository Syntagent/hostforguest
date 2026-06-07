FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements-prod.txt .
RUN pip install --no-cache-dir --no-compile -r requirements-prod.txt

COPY app ./app
COPY infra ./infra
COPY scripts ./scripts

RUN python -m compileall -q app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD awk '$2 ~ /:1F40$/ && $4 == "0A" { found=1 } END { exit found ? 0 : 1 }' /proc/net/tcp /proc/net/tcp6

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
