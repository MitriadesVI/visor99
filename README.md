# Visor 99

Visor 99 es un dashboard local de analisis electoral por mesa de votacion, con foco inicial en Senado Colombia 2026.

La aplicacion principal ahora corre como una arquitectura `FastAPI + React`, mientras que la version anterior en Streamlit se conserva en `app/` como referencia funcional y respaldo de la logica original.

## Estructura actual

La ruta principal de trabajo queda asi:

```text
visor99/
  backend/
    app/
      analytics/
      models/
      routers/
      services/
      main.py
    requirements.txt
  frontend/
    src/
      api/
      components/
      hooks/
      styles/
    package.json
  datos/
    elecciones 2026/
      *.csv
      nacional.csv
      nacional.parquet
  app/                  # legado Streamlit
  tests/
```

## Quickstart

1. Crear y activar entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias del backend:

```bash
pip install -r backend/requirements.txt
```

3. Levantar API:

```bash
uvicorn backend.app.main:app --reload
```

4. En otra terminal, instalar y correr frontend:

```bash
cd frontend
npm install
npm run dev
```

5. Abrir:

- frontend: `http://127.0.0.1:5173`
- backend: `http://127.0.0.1:8000`
- docs OpenAPI: `http://127.0.0.1:8000/docs`

## Backend

El backend usa `FastAPI`, carga el dataset nacional por defecto en memoria al iniciar y mantiene cache para datasets adicionales cuando se solicitan.

### Endpoints

- `GET /api/datasets`
- `GET /api/filters`
- `GET /api/candidate/summary`
- `GET /api/competitive/rivals`
- `GET /api/municipal/comparison`
- `GET /health`

### Filtros soportados

Los endpoints analiticos aceptan filtros por query params:

- `dataset`
- `contest`
- `department`
- `municipality`
- `party`
- `candidate`

Adicionalmente:

- `top_n` en competitivo
- `sort_by` y `limit` en municipal

### Ejecutar backend

```bash
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Backend local:

- `http://127.0.0.1:8000`
- docs OpenAPI: `http://127.0.0.1:8000/docs`

### Ejemplos rapidos

Datasets disponibles:

```bash
curl http://127.0.0.1:8000/api/datasets
```

Resumen del candidato foco:

```bash
curl -G http://127.0.0.1:8000/api/candidate/summary \
  --data-urlencode "dataset=elecciones 2026/nacional.parquet" \
  --data-urlencode "contest=SENADO" \
  --data-urlencode "candidate=GONZALO DIMAS BAUTE GONZALEZ"
```

Rivales en Santander:

```bash
curl -G http://127.0.0.1:8000/api/competitive/rivals \
  --data-urlencode "dataset=elecciones 2026/nacional.parquet" \
  --data-urlencode "contest=SENADO" \
  --data-urlencode "candidate=GONZALO DIMAS BAUTE GONZALEZ" \
  --data-urlencode "department=SANTANDER"
```

Comparacion municipal por eficiencia:

```bash
curl -G http://127.0.0.1:8000/api/municipal/comparison \
  --data-urlencode "dataset=elecciones 2026/nacional.parquet" \
  --data-urlencode "contest=SENADO" \
  --data-urlencode "candidate=GONZALO DIMAS BAUTE GONZALEZ" \
  --data-urlencode "sort_by=efficiency"
```

## Frontend

El frontend es una SPA con `React 18 + Vite + TypeScript + Tailwind + Recharts`.

Incluye:

- sidebar fija con filtros en cascada;
- header del candidato y metricas principales;
- tarjetas de zonas top;
- grafica de barras territorial;
- donut de cobertura;
- detalle de mesas top, ganadas y perdidas por poco;
- bloque competitivo con tabla y scatter;
- bloque municipal con treemap y ranking.

### Estado visual

La UI sigue una linea oscura de tablero politico, con:

- sidebar fija a la izquierda;
- tarjetas sobre `surface` con bordes `border`;
- tipografia `DM Sans` + `JetBrains Mono`;
- charts con tooltips oscuros;
- tablas con valores numericos en `mono`.

### Ejecutar frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend local:

- `http://127.0.0.1:5173`

Si el backend corre en un puerto distinto a `8000`, define `VITE_API_BASE_URL`.

Ejemplo:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8001 npm run dev
```

## Dataset

Los datos fuente siguen viviendo en `datos/elecciones 2026/`.

Por defecto, el backend precalienta:

- `datos/elecciones 2026/nacional.parquet`

La normalizacion canonica conserva estas columnas clave:

- `department_code`
- `department_name`
- `municipality_code`
- `municipality_name`
- `zone_code`
- `polling_place_code`
- `polling_place_name`
- `table_code`
- `party_name`
- `candidate_name`
- `votes`

Durante la carga tambien se enriquecen:

- `table_id`
- `polling_place_id`
- `municipality_id`
- `row_kind`
- `ballot_label`
- `extra__*` para columnas no mapeadas

## Candidato de referencia

El foco inicial del tablero y del dataset por defecto es:

- `GONZALO DIMAS BAUTE GONZALEZ`
- coalicion: `COALICIÓN CAMBIO RADICAL - ALMA`
- concurso por defecto: `SENADO`

## Analitica disponible

### Resumen de candidato

- votos del candidato por mesa;
- total de votos de la mesa;
- participacion relativa;
- ranking de mesas;
- ranking de zonas;
- margen contra mejor competidor;
- mesas ganadas;
- mesas perdidas por poco margen;
- cobertura territorial.

### Bloque competitivo

- top rivales en mesas compartidas;
- votos rival vs. votos del candidato;
- mesas donde gana el rival;
- participacion promedio rival vs. candidato;
- `head_to_head` para scatter mesa a mesa.

### Bloque municipal

- votos por municipio;
- mesas activas vs. mesas disponibles;
- cobertura;
- eficiencia territorial;
- rival principal por municipio;
- ranking dinamico por votos, eficiencia o cobertura.

## Pruebas

Pruebas heredadas y nuevas:

```bash
./.venv/bin/pytest
```

Pruebas puntuales del backend nuevo:

```bash
./.venv/bin/pytest tests/test_backend_analytics.py tests/test_backend_api.py
```

Build del frontend:

```bash
cd frontend
npm run build
```

## Verificacion local realizada

Se valido en este workspace:

- `./.venv/bin/pytest tests/test_backend_analytics.py tests/test_backend_api.py -q`
- `./.venv/bin/pytest tests/test_analytics.py tests/test_normalizer.py -q`
- `./.venv/bin/python -m compileall backend/app`
- `npm run build` en `frontend/`
- `uvicorn backend.app.main:app --reload`
- `npm run dev`

Tambien se comprobaron respuestas reales sobre `datos/elecciones 2026/nacional.parquet` para:

- `/api/datasets`
- `/api/filters`
- `/api/candidate/summary`
- `/api/competitive/rivals`
- `/api/municipal/comparison`

## Streamlit legado

La app original sigue en `app/main.py` por compatibilidad y referencia historica.

Se mantiene para consulta y comparacion de comportamiento, pero el desarrollo nuevo debe hacerse sobre:

- `backend/`
- `frontend/`
