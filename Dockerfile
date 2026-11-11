# One container: builds the React frontend, then serves it and the API from FastAPI.

FROM node:22-alpine AS web
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY shared/ /src/shared/
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY shared ./shared
COPY --from=web /src/frontend/dist ./frontend/dist

ENV FRONTEND_DIST=/app/frontend/dist \
    SHARED_CONSTANTS=/app/shared/constants.json \
    DATABASE_URL=sqlite:////data/elevator.db \
    TRUST_PROXY=true \
    PYTHONUNBUFFERED=1
RUN mkdir -p /data
EXPOSE 8080
# Render and other hosts pass PORT; Fly uses 8080.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips '*'"]
