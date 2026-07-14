# eラーニング API（公開ポータル付き）
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    CORS_ORIGINS=* \
    WEB_BASE_URL=

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/ .

# Verify import at build time
RUN python -c "from app.main import app; print('import-ok', app.title)"

# Railway Target Port が 5000 の場合に合わせる（実際の待受は $PORT）
EXPOSE 5000

CMD ["sh", "-c", "echo \"[elearning] binding 0.0.0.0:${PORT:-5000}\" && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-5000}"]
