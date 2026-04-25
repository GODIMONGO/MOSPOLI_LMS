FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-semantic.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip==26.0.1 \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-semantic.txt

COPY . .

EXPOSE 5000

CMD ["sh", "-c", "gunicorn --worker-class gthread --threads ${GUNICORN_THREADS:-8} -w ${WEB_CONCURRENCY:-2} --bind 0.0.0.0:${PORT:-5000} main:app"]
