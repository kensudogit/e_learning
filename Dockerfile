# eラーニング（API + 公開ポータル）
# Railway: 必ず 0.0.0.0:$PORT で待受。PORT をイメージに焼き込まない。
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

EXPOSE 5000

# Railway が注入する PORT（画面上の Target Port と一致させる）
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-5000}"]
