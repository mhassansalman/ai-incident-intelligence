# Local Environment — Without Docker

## Why this environment exists

The current laptop has limited resources for a large Docker Desktop + multi-container observability stack.

Therefore the first environment is intentionally small and native.

This is not a throwaway architecture.

It is the first provider implementation.

## Suggested local application

Use a small FastAPI microservices demo with three processes:

```text
Client
  │
  ▼
Gateway :8080
  │
  ├───────────────┐
  ▼               ▼
Orders :8001   Catalog :8000
  │               ▲
  └───────────────┘
```

## Run model

Each service runs as a normal Python process in its own terminal.

No Docker required.

## Core evidence sources

### Health

```text
GET /health
```

### Metrics

Add or use:

```text
GET /metrics
```

Initial metrics can be simple JSON:

```json
{
  "request_count": 250,
  "error_count": 17,
  "error_rate": 0.068,
  "avg_latency_ms": 420
}
```

### Logs

Use local files:

```text
logs/gateway.log
logs/orders.log
logs/catalog.log
```

### Git

Use the cloned local repository.

Useful commands later:

```text
git log
git show
git diff
```

## Provider abstraction

```text
Agent
  ↓
Tool Interface
  ↓
Local Provider
```

Examples:

```text
search_logs()
get_metrics()
get_service_health()
get_recent_commits()
```

## First incident scenarios

### INC-001 — Catalog down

Stop Catalog.

Expected symptoms:

```text
catalog health fails
orders dependency calls fail
gateway order flow fails
```

Goal:

> System identifies Catalog as the upstream root cause rather than Gateway as the root cause.

### INC-002 — Catalog slow

Add artificial delay.

Expected symptoms:

```text
catalog latency rises
orders timeouts/retries increase
gateway latency rises
```

### INC-003 — Bad Orders commit

Introduce a code regression and commit it.

Expected symptoms:

```text
errors begin after commit
Git Investigator finds relevant change
```

### INC-004 — Intermittent Catalog errors

Randomly return failures.

Expected symptoms:

```text
partial availability
error-rate spikes
more difficult evidence pattern
```

### INC-005 — Misleading evidence

Create a harmless recent commit while causing an unrelated runtime fault.

Goal:

> Verifier must reject the tempting but incorrect "recent deployment caused it" hypothesis.

## What is intentionally skipped initially

- Docker
- Kubernetes
- full Prometheus stack
- Grafana
- Jaeger
- complex traces
- cloud infrastructure

These are future environment upgrades, not core architecture requirements.
