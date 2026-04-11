# Visor 99

Dashboard de analisis electoral por mesa de votacion para Senado Colombia 2026.

Arquitectura: **FastAPI (JSON estatico) + React SPA**, desplegado como servicio unico en Railway.

## Estructura

```text
visor99/
  scripts/
    precompute.py          # genera todos los JSONs desde el parquet
  precomputed/             # ~18k archivos JSON (generado, no en git)
    datasets.json
    filters/
    candidate/
    competitive/
    municipal/
    drilldown/
  backend/
    app/
      routers/             # endpoints que leen JSONs precomputados
      services/
        json_reader.py     # utilidad de lectura con proteccion path traversal
      main.py              # FastAPI app + SPA serving
    requirements.txt       # solo fastapi + uvicorn
  frontend/
    src/
      api/                 # cliente HTTP + tipos TypeScript
      components/          # cards, charts, filters, tables, layout
      hooks/               # useCandidateData, useFilters, etc.
      styles/
    package.json
  datos/
    elecciones 2026/
      nacional.parquet     # fuente de datos (no en git)
  app/                     # legado Streamlit (referencia)
  tests/
  Dockerfile
  railway.toml
```

## Decisiones tecnicas

### Precomputed JSONs (v3 — actual)

El backend sirve archivos JSON precomputados. No hace ningun calculo en runtime.

**Por que:** Railway impone un limite de RAM (~512MB). Las iteraciones anteriores excedian ese limite:

| Iteracion | Estrategia | RAM estimada | Resultado |
|-----------|------------|-------------|-----------|
| v1 | pandas carga parquet en memoria | ~800MB | OOM en Railway |
| v2 | DuckDB queries sobre parquet | ~400MB | Aun excedia limite |
| v3 | JSONs precomputados, backend stateless | ~30MB | Deploy exitoso |

El script `scripts/precompute.py` corre localmente, lee el parquet una vez, y genera ~18,478 archivos JSON (~210MB). El backend solo necesita `fastapi` + `uvicorn` y lee JSONs bajo demanda.

### Estructura de JSONs precomputados

```text
precomputed/
  datasets.json                              # lista de datasets disponibles
  filters/
    all.json                                 # filtros globales (contests, departments, etc.)
    {DEPARTAMENTO}.json                      # filtros por departamento
  candidate/
    _national.json                           # resumen nacional del candidato
    {DEPT}/_summary.json                     # resumen por departamento
    {DEPT}/{MUNICIPIO}.json                  # resumen por municipio
  competitive/
    _national.json                           # rivales a nivel nacional
    {DEPT}/_rivals.json                      # rivales por departamento
    {DEPT}/{MUNICIPIO}.json                  # rivales por municipio
  municipal/
    _national.json                           # comparacion municipal nacional
    {DEPT}.json                              # comparacion municipal por departamento
  drilldown/
    {DEPT}/{MUNI}/zones.json                 # zonas del municipio
    {DEPT}/{MUNI}/ZONE_{CODE}/places.json    # puestos de la zona
    {DEPT}/{MUNI}/ZONE_{CODE}/PLACE_{CODE}.json  # mesas del puesto
```

Los nombres de carpeta se sanitizan: mayusculas, espacios → guion bajo, sin caracteres especiales.

### Deploy en Railway

- **Dockerfile multi-stage:** Stage 1 compila frontend (Node 20), Stage 2 copia backend + precomputed + frontend/dist (Python 3.11-slim).
- **Servicio unico:** FastAPI sirve la API bajo `/api/*` y el SPA en `/*`.
- **Healthcheck:** `GET /api/datasets` con timeout de 5 min.
- Los datos fuente (`datos/`) NO se copian a la imagen Docker; solo `precomputed/`.

### Frontend

React 18 + Vite + TypeScript + Tailwind + Recharts.

- URLs relativas en produccion (`VITE_API_BASE_URL` vacio → usa `window.location.origin`).
- En desarrollo apunta a `http://127.0.0.1:8000` via `.env.development`.

## Candidato de referencia

- **GONZALO DIMAS BAUTE GONZALEZ**
- Coalicion: COALICIÓN CAMBIO RADICAL - ALMA
- Concurso: SENADO

## Quickstart

### 1. Generar JSONs precomputados (una sola vez)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pandas pyarrow
python scripts/precompute.py
```

Esto genera `precomputed/` (~210MB, ~18k archivos). Requiere `datos/elecciones 2026/nacional.parquet`.

Para otro candidato:

```bash
python scripts/precompute.py --candidate "NOMBRE DEL CANDIDATO"
```

### 2. Backend

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`

### 3. Frontend

```bash
cd frontend && npm install && npm run dev
```

- `http://127.0.0.1:5173`

## Endpoints

| Endpoint | Descripcion |
|----------|-------------|
| `GET /api/datasets` | Datasets disponibles |
| `GET /api/filters` | Opciones de filtro (cascada por departamento) |
| `GET /api/candidate/summary` | Resumen del candidato (stats, top zonas, mesas) |
| `GET /api/candidate/drilldown` | Navegacion zona → puesto → mesa |
| `GET /api/competitive/rivals` | Top 15 rivales + head-to-head |
| `GET /api/municipal/comparison` | Comparacion municipal |
| `GET /api/health` | Healthcheck |

### Filtros por query params

`department`, `municipality`, `contest`, `candidate`, `party`, `dataset`.

Drilldown adicional: `level` (zone/polling_place/table), `zone_code`, `polling_place_code`.

## Analitica

### Resumen de candidato

Votos totales, cobertura (% mesas con votos), participacion promedio, mesas ganadas, mesas perdidas por poco margen (threshold: 10 votos), top 8 zonas, top 50 mesas, top 50 mesas ganadas, top 50 mesas perdidas por poco.

### Competitivo

Top 15 rivales por votos en mesas compartidas. Por cada rival: mesas donde gana candidato vs rival, participacion promedio. Scatter head-to-head limitado a 500 puntos.

### Municipal

Ranking de municipios por votos, eficiencia (votos/mesa) o cobertura. Incluye rival principal por municipio.

### Drilldown

Navegacion jerarquica: zonas → puestos de votacion → mesas. Cada nivel muestra votos del candidato, votos totales, ranking, ganador de la zona/puesto/mesa.

## Legado

La app Streamlit original en `app/` y los modulos analytics/services originales en `backend/app/analytics/` y `backend/app/routers/` (sin sufijo `_new`) se conservan como referencia. El backend activo usa los routers `*_new.py`.
