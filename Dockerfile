FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIST=/app/frontend/dist

WORKDIR /app
RUN useradd --create-home --uid 10001 appuser

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

COPY --from=frontend-build /app/frontend/dist ./frontend/dist

USER appuser
EXPOSE 8000

CMD ["uvicorn", "collab.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
