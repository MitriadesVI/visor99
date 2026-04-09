# ── Stage 1: Build frontend ──
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend + frontend estático ──
FROM python:3.11-slim
WORKDIR /app

# Instalar dependencias Python
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar backend
COPY backend/ ./backend/

# Copiar datos
COPY datos/ ./datos/

# Copiar frontend compilado
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Puerto (Railway asigna $PORT)
ENV PORT=8000
ENV MALLOC_ARENA_MAX=2
EXPOSE 8000

# Arrancar FastAPI
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
