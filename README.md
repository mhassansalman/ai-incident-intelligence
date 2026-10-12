# AI Incident Intelligence — Local Microservices Simulator

This repository contains the **V0 FastAPI simulator** and the **V1 Reactive Incident Commander specification**. V1 is planned, not yet implemented. The simulator runs locally **without Docker**; `docker-compose.yml` is retained for later use.

## Quick start (Windows PowerShell)

From the repository root, activate the existing `.venv` or create one (`py -m venv .venv`, then `.\.venv\Scripts\Activate.ps1`). Install dependencies using:

```powershell
python -m pip install -r services/catalog/requirements.txt -r services/orders/requirements.txt -r services/gateway/requirements.txt -r tests/requirements-dev.txt
```

Run the following in **three separate PowerShell terminals**, with the virtual environment active and the current directory set to this repository root:

```powershell
# Terminal 1 — Catalog
python -m uvicorn services.catalog.app:app --port 8000
```

```powershell
# Terminal 2 — Orders
$env:CATALOG_URL="http://127.0.0.1:8000"
python -m uvicorn services.orders.app:app --port 8001
```

```powershell
# Terminal 3 — Gateway
$env:CATALOG_URL="http://127.0.0.1:8000"
$env:ORDERS_URL="http://127.0.0.1:8001"
python -m uvicorn services.gateway.app:app --port 8080
```

In a fourth terminal, run `python -m pytest -q` after the three services are ready. The integration test expects a running gateway on port 8080 (override with `TEST_GATEWAY_URL` if necessary).

For Git Bash, use `export CATALOG_URL=http://127.0.0.1:8000` / `export ORDERS_URL=http://127.0.0.1:8001` instead of `$env:`.

Documentation entry point: [`docs/00_DOCS_INDEX.md`](docs/00_DOCS_INDEX.md). Keep V0 behavior working while implementing V1 incrementally. No automatic remediation in V1.

---

## Original microservices demo reference

# Python Microservices Demo (FastAPI + Docker Compose)

A tiny, production-flavored but classroom-simple microservices example using **FastAPI**, **httpx**, and **Docker Compose**.  

It demonstrates:
- Service boundaries (**Gateway → Orders ↔ Catalog**)
- Contract-first schemas with **Pydantic**
- Simple intra-service calls with **timeouts** and **retries**
- 12-factor-ish config via **environment variables**
- Clean, type-hinted Python with a minimal, **thread-safe in-memory** store (for demo only)

> ⚠️ This is for demonstration. For real systems, add a database, auth (JWT/OIDC), observability (OpenTelemetry), service discovery, circuit breakers, and proper persistence.

---

## Architecture

```

Client → Gateway (:8080) → Orders (:8001) → Catalog (:8000)
└───────────────GET /items/{id}──────────────▶

```

- **Gateway**: Public edge API. Proxies/aggregates to internal services.
- **Orders**: Accepts orders, validates item in Catalog, computes totals.
- **Catalog**: Owns the product catalog; provides list/get/create.
- **Common**: Shared Pydantic models used as contracts between services.

---

## Project Layout

```

microdemo/
├─ docker-compose.yml
├─ .env.example
├─ README.md
├─ common/
│  ├─ common/**init**.py
│  └─ common/schemas.py
└─ services/
├─ catalog/ (items)
├─ orders/  (orders)
└─ gateway/ (public API)

````

---

## Prerequisites
- **Docker** and **Docker Compose** (or Docker Desktop)
- Alternatively for local dev (no Docker): Python 3.11 + `pip`

---

## Configuration via `.env`

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
````

Default `.env.example`:

```dotenv
APP_VERSION=0.1.0

# Internal service URLs (used inside Compose network)
CATALOG_URL=http://catalog:8000
ORDERS_URL=http://orders:8001

# Networking
HTTP_TIMEOUT=2.5
RETRY_ATTEMPTS=2
```

* Override values in `.env` as needed.
* Compose loads `.env` automatically.
* If running locally without Docker, export these vars in your shell.

---

## Getting Started (Docker)

```bash
# from project root
docker compose up --build
```

Health checks:

```bash
curl -s http://localhost:8080/health
curl -s http://localhost:8001/health
curl -s http://localhost:8000/health
```

Happy path:

```bash
# list items via gateway
curl -s http://localhost:8080/api/items

# place an order for 3 qty of item 1
curl -s -X POST http://localhost:8080/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"item_id": 1, "qty": 3}'
```

Expected order response:

```json
{ "id": 1, "item_id": 1, "qty": 3, "total": "597.00" }
```

---

## Running Locally (No Docker)

Open 3 terminals:

**Terminal 1 – Catalog**

```bash
uvicorn services.catalog.app:app --reload --port 8000
```

**Terminal 2 – Orders**

```bash
export CATALOG_URL=http://127.0.0.1:8000
uvicorn services.orders.app:app --reload --port 8001
```

**Terminal 3 – Gateway**

```bash
export CATALOG_URL=http://127.0.0.1:8000
export ORDERS_URL=http://127.0.0.1:8001
uvicorn services.gateway.app:app --reload --port 8080
```

> Ensure `PYTHONPATH=.` so `common` is importable.

---

## API Reference

### Gateway (public, `:8080`)

* `GET /health` → `{ status, service, version }`
* `GET /api/items` → list of items
* `POST /api/orders` `{ item_id, qty }` → created order

### Orders (internal, `:8001`)

* `GET /health`
* `POST /orders` `{ item_id, qty }` → created order
* `GET /orders/{id}` → order by id

### Catalog (internal, `:8000`)

* `GET /health`
* `GET /items` → list
* `GET /items/{id}` → item by id
* `POST /items` `{ name, price }` → create

---

## Testing (Optional)

```bash
pip install -r tests/requirements-dev.txt
pytest -q
```

---

## Security & Good Coding Notes

* Validate inputs/outputs with Pydantic models at service boundaries.
* Timeouts and small retries on outbound calls.
* Only expose **Gateway** publicly.
* In-memory stores use locks (replace with a DB in real apps).
* Config via env vars only.
* Add observability (logs, tracing, metrics) in real apps.
* Add JWT auth and mTLS between services in production.

---

## Troubleshooting

* **Port already in use**: change host ports in `docker-compose.yml`.
* **Cannot import `common`**: set `PYTHONPATH=.`.
* **Service communication fails**: check `.env` values and container names.
* **Windows quoting issues**: use Postman/Insomnia instead of `curl`.

---

## Roadmap

* Replace in-memory with **Postgres** per service.
* Add **Users** service with JWT auth.
* Add **OpenTelemetry** and Prometheus.
* Add **message broker** (RabbitMQ/Kafka) for async order events.
* Add **rate limiting** and **circuit breaker** at Gateway.

---

## License

MIT License.
