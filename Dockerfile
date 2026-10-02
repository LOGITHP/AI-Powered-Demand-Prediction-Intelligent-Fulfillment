FROM node:20-alpine AS frontend-build

WORKDIR /frontend
COPY fulfilliq/frontend/package*.json ./
RUN npm ci
COPY fulfilliq/frontend/ ./
# An empty API base URL makes browser requests resolve against this same host.
ENV VITE_API_URL=
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

WORKDIR /app
COPY fulfilliq/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY fulfilliq/backend/ ./
COPY --from=frontend-build /frontend/dist ./static

EXPOSE 10000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
