# AI Incident Intelligence

**An evolving, evidence-first AI incident investigation system for microservices.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Microservices-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2.15-4338CA)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

AI Incident Intelligence is a progressive engineering project exploring how an AI-assisted SRE system can investigate service incidents using **logs, metrics, health checks, and Git history**, build verifiable evidence, and ultimately recommend evidence-backed root causes and recovery actions.

The development environment is deliberately **local-first and Docker-optional**. A working FastAPI microservices playground (V0) provides incidents and operational context; V1 introduces the investigation workflow in small, testable increments.

> **Current status — October 2026:** V0 microservices simulator and the initial V1 investigation foundation are implemented. The V1 Stage 2 CLI runs a compiled, deterministic LangGraph over a recorded incident fixture. **Automated RCA, LLM reasoning, RAG, MCP, and remediation are not implemented in this stage.**

## Contents

- [What this project solves](#what-this-project-solves)
- [Current capabilities](#current-capabilities)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Run the V1 investigation](#run-the-v1-investigation)
- [Run the V0 microservices](#run-the-v0-microservices)
- [Testing](#testing)
- [Repository structure](#repository-structure)
- [Roadmap](#roadmap)
- [Design principles and limitations](#design-principles-and-limitations)
- [Documentation](#documentation)
- [License](#license)

## What this project solves

When a service breaks, engineers typically inspect scattered sources—service health, request failures, metrics, and recent changes—before forming and verifying a hypothesis. This project aims to bring those signals into a single, **traceable incident investigation**.

The intended full V1 flow is:

```text
Human supplies incident
          |
          v
     Incident intake
          |
          v
    Investigation plan
          |
          v
 Health / Logs / Metrics / Git
          |
          v
  Normalized evidence (IDs + provenance)
          |
          v
 Competing hypotheses + verification   [planned]
          |
          v
 Evidence-cited RCA or "inconclusive"   [planned]
          |
          v
 Human-reviewed remediation/report      [planned]
```

**In the current CLI, execution stops after evidence aggregation.** The later steps above describe the V1 goal, not shipping functionality.

## Current capabilities

| Component | Status | What exists |
| --- | --- | --- |
| **V0: Local microservices simulator** | ✅ Implemented | FastAPI Gateway, Orders, and Catalog services; HTTP communication, health endpoints, and basic metrics/logging for incident exercises. |
| **V0: Recorded incident scenario** | ✅ Implemented | `incidents/INC-001.json`, with health, logs, metrics, and recent-commit evidence. |
| **V1: Evidence and state contracts** | ✅ Implemented | Pydantic evidence/hypothesis models and typed `IncidentState` in `common/incident_models.py`. |
| **V1: Fixture-to-state mapping** | ✅ Implemented | Maps recorded V0 incident evidence into normalized entries with stable IDs and source references. |
| **V1: Basic LangGraph execution** | ✅ Implemented | Compiled `Intake → Planner → Evidence` graph and command-line entry point. |
| **V1: Input errors and regression tests** | ✅ Implemented | CLI reports missing/malformed incident files; Stage 1 and 2 tests cover the initial foundation. |
| **Live autonomous investigation / RCA** | 🚧 Planned | Live evidence acquisition, hypothesis verification, evidence-grounded RCA, and reporting. |
| **RAG / MCP** | 🚧 Planned | Context retrieval and protocol adapters after the investigation baseline works. |
| **Automatic detection / remediation** | 🔒 Out of V1 scope | Reserved for later versions; no autonomous production changes. |

## Architecture

### V0 — Local microservices playground

```text
                         Client
                            |
                            v
                 Gateway :8080 (FastAPI)
                    /               \
                   v                 v
          Orders :8001           Catalog :8000
               |                      ^
               +---- HTTP lookup -----+

   Service health, logs, and metrics support local failure scenarios.
```

- **Gateway:** Entry-point HTTP API that proxies and aggregates requests.
- **Orders:** Order creation and Catalog lookups.
- **Catalog:** Item catalog and item lookup.
- **Common:** Shared schemas and incident contracts.

### V1 — Current investigation foundation

```text
  incidents/INC-001.json (recorded V0 evidence)
                         |
                         v
           V0 -> IncidentState mapper
                         |
                         v
                LangGraph START
                         |
                         v
                      Intake
                         |
                         v
                      Planner
                         |
                         v
                     Evidence
                         |
                         v
                LangGraph END
                         |
                         v
            CLI investigation summary
```

The current graph is deterministic and uses the incident JSON fixture; it **does not call an LLM, a RAG index, an MCP server, or the live microservices during CLI execution**. `root_cause` remains `None` until a future RCA stage is built.

## Quick start

**Requirements:** Python 3.11+ and Git. Docker is **not required** for the supported local workflow.

Clone the repository and create an environment:

```powershell
git clone https://github.com/mhassansalman/ai-incident-intelligence.git
cd ai-incident-intelligence
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install all currently needed dependencies (the root requirements file pins LangGraph; service and testing dependencies are separate):

```powershell
python -m pip install -r requirements.txt -r services/catalog/requirements.txt -r services/orders/requirements.txt -r services/gateway/requirements.txt -r tests/requirements-dev.txt
```

On **Git Bash / Linux / macOS**, activate with `source .venv/bin/activate` (Git Bash on Windows normally uses `source .venv/Scripts/activate`). Use `python -m venv .venv` instead of `py -m venv .venv` where the Windows launcher is unavailable.

## Run the V1 investigation

From the repository root, with the virtual environment activated:

```bash
python -m investigation.cli --incident incidents/INC-001.json
```

The command loads the incident, maps its recorded evidence, executes the LangGraph, and prints the investigation status, evidence count, missing-evidence notes, errors, and RCA placeholder.

**Expected behavior:** The graph reaches evidence aggregation and clearly states that RCA is not implemented in Stage 2. It does **not** generate a root cause or remediation plan. For this fixture-backed CLI path, the three FastAPI services do not need to be running.

Try failure handling:

```bash
python -m investigation.cli --incident incidents/does-not-exist.json
```

A missing file should produce a useful error and nonzero exit status. Avoid placing evaluation answer keys or private incident secrets in CLI inputs.

## Run the V0 microservices

Start each service in its **own terminal**, from the repository root. Activate the same `.venv` in each terminal.

**Terminal 1 — Catalog**

```powershell
python -m uvicorn services.catalog.app:app --port 8000
```

**Terminal 2 — Orders**

```powershell
$env:CATALOG_URL = "http://127.0.0.1:8000"
python -m uvicorn services.orders.app:app --port 8001
```

**Terminal 3 — Gateway**

```powershell
$env:CATALOG_URL = "http://127.0.0.1:8000"
$env:ORDERS_URL = "http://127.0.0.1:8001"
python -m uvicorn services.gateway.app:app --port 8080
```

Verify the services in a fourth PowerShell terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8001/health
Invoke-RestMethod http://127.0.0.1:8080/health
Invoke-RestMethod http://127.0.0.1:8080/api/items
```

Example order through Gateway:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8080/api/orders `
  -ContentType "application/json" `
  -Body '{"item_id":1,"qty":3}'
```

For **Git Bash**, substitute shell environment assignments:

```bash
export CATALOG_URL=http://127.0.0.1:8000
export ORDERS_URL=http://127.0.0.1:8001
```

Run each service in the appropriate shell after setting its variables. Ports are `8000` (Catalog), `8001` (Orders), and `8080` (Gateway).

### Useful V0 endpoints

| Service | Route | Purpose |
| --- | --- | --- |
| Gateway | `GET /health` | Health |
| Gateway | `GET /api/items` | Read catalog through gateway |
| Gateway | `POST /api/orders` | Submit an order |
| Orders | `GET /health` | Health |
| Orders | `POST /orders` | Create an order |
| Orders | `GET /orders/{id}` | Fetch order |
| Catalog | `GET /health` | Health |
| Catalog | `GET /items` | List items |
| Catalog | `GET /items/{id}` | Fetch item |
| Catalog | `POST /items` | Create item |

## Testing

Run the automated suite from the project root:

```bash
python -m pytest -q
```

**Note:** The V0 HTTP integration test expects a live Gateway at `http://127.0.0.1:8080`. Launch all three services first for the full suite, or configure `TEST_GATEWAY_URL` to target a different running gateway.

The most recent local Stage 2 acceptance audit reported **47 passing tests (35 Stage 1 + 12 Stage 2)**. This is a reported result, **not a CI badge or an independently rerun test result**; always run the suite again after changes.

## Repository structure

```text
ai-incident-intelligence/
├── common/
│   ├── schemas.py                 # V0 shared API contracts
│   └── incident_models.py         # V1 evidence and state contracts
├── docs/
│   ├── 00_DOCS_INDEX.md           # Recommended V1 reading order
│   ├── 02_V1_REACTIVE_INCIDENT_COMMANDER.md
│   ├── ARCHITECTURE/              # Architecture and state design
│   ├── DEVELOPMENT/               # Implementation plan and evaluation
│   ├── ENVIRONMENTS/              # Local environment guidance
│   └── FLOWS/                     # Investigation and RCA designs
├── incidents/
│   └── INC-001.json               # Recorded incident fixture
├── investigation/
│   ├── cli.py                     # V1 CLI and compiled graph
│   ├── nodes.py                   # Intake, planner, evidence nodes
│   └── state.py                   # State/model reuse
├── services/
│   ├── catalog/                   # Catalog API
│   ├── orders/                    # Orders API
│   └── gateway/                   # Gateway API
├── tests/                         # V0 and V1 regression tests
├── requirements.txt               # LangGraph pin
├── docker-compose.yml             # Optional/later environment
├── AGENTS.md                      # Implementation constraints
└── README.md
```

## Roadmap

The long-term project is intentionally versioned. **Only completed work is listed as implemented.**

| Version | Scope | Status |
| --- | --- | --- |
| **V0 — Problem Simulator** | Local microservices, failure scenarios, and operational evidence | ✅ Working foundation |
| **V1 — Reactive Incident Commander** | Human-triggered, evidence-based investigation and recommendations | 🚧 In progress |
| **V2 — Alert-Triggered Incident Commander** | Trigger investigations from alerts | Planned |
| **V3 — Always-On Incident Intelligence** | Continuous monitoring and proactive investigation | Planned |
| **V4 — Incident Intelligence as a Service** | Reusable, integration-ready service | Planned |
| **V5 — Advanced Enterprise AI SRE** | Enterprise-oriented intelligence and governance | Planned |

**V1 delivery progression:**

1. **Foundation complete:** incident/evidence models, canonical state mapping, deterministic initial graph, and CLI tests.
2. **Next:** deepen investigation and connect read-only evidence providers without breaking the V0 playground.
3. **Then:** competing hypotheses, contradiction checks, bounded verification (maximum three cycles), evidence-linked RCA, and an explicit inconclusive outcome.
4. **After the evidence-to-RCA baseline:** evaluate RAG over runbooks, architecture notes, and historical incidents; expose stable tools through MCP where useful.
5. **Finish V1:** human-reviewed recommendations and an evidence-cited report. No autonomous remediation.

The numbered *stages* in [`docs/DEVELOPMENT/01_IMPLEMENTATION_PLAN.md`](docs/DEVELOPMENT/01_IMPLEMENTATION_PLAN.md) describe a broader capability sequence; they should not be confused with the repository's Stage 1/Stage 2 acceptance-test labels. Follow the active V1 scope and current code as the source of truth.

## Design principles and limitations

- **Evidence over guesses:** Ground findings in actual source references; never fabricate logs, metrics, commits, or root causes.
- **Show uncertainty:** Conflicting or insufficient evidence must lead to an explicit inconclusive result, not forced certainty.
- **Read-only V1:** Investigations can recommend actions; they must not restart services, deploy changes, or mutate production systems.
- **Bounded reasoning:** The intended verifier stops after at most three cycles.
- **Ground-truth isolation:** Hidden evaluation answer keys must not be accessible to an investigating agent, its tools, prompts, or RAG corpus.
- **Local-first development:** The repository supports running without Docker; Docker and full OpenTelemetry integrations are not prerequisites for V1.
- **Educational prototype:** In-memory V0 stores, fixture-backed investigation, and local service setup are not a production incident-management deployment.

## Documentation

Start with [`docs/00_DOCS_INDEX.md`](docs/00_DOCS_INDEX.md), then read:

- [V1 scope and definition of done](docs/02_V1_REACTIVE_INCIDENT_COMMANDER.md)
- [Implementation plan](docs/DEVELOPMENT/01_IMPLEMENTATION_PLAN.md)
- [Agent/development rules](AGENTS.md)

Architecture, flow, RAG, MCP, and evaluation design documents live under [`docs/`](docs/). **A document describing a component does not imply that component is already implemented.**

## License

Distributed under the [MIT License](LICENSE).
