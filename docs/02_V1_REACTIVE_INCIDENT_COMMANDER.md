# V1 — Reactive AI Incident Commander

> **V1 implementation scope:** Manually triggered, local without Docker, read-only investigation and recommendations. Detection/always-on monitoring, automatic remediation, and production integrations are later versions. RAG and MCP are added after the working evidence-to-RCA baseline. Existing code must be inspected before assuming interfaces exist.


## Goal

Build the **investigation brain**.

The system does **not detect incidents yet**.

A user gives it an incident and asks it to investigate.

## User Flow

```text
User enters incident
        ↓
[ INVESTIGATE ]
        ↓
Planner
        ↓
Logs + Git + Metrics
        ↓
Evidence
        ↓
RAG
        ↓
Hypotheses
        ↓
Verification
        ↓
Root Cause
        ↓
Remediation
        ↓
Final Report
```

## V1 Stack (add progressively)

- Python
- FastAPI
- LangGraph
- LangChain only where useful
- Python MCP SDK (after working Python tool interfaces)
- FAISS or Chroma (after evidence-to-RCA baseline)
- CLI or minimal API first; React/Gradio UI optional
- JSON/files for synthetic data

## Core LangGraph State (illustrative; authoritative fields in ARCHITECTURE/04)

```python
class IncidentState(TypedDict):
    incident_id: str
    description: str
    affected_services: list[str]
    logs: list
    metrics: dict
    commits: list
    deployments: list
    retrieved_documents: list
    hypotheses: list
    verified_hypotheses: list
    root_cause: dict
    remediation_plan: list
    final_report: str
```

## Graph

```text
START
  ↓
Incident Intake
  ↓
Planner
  ↓
┌─────────┬─────────┬─────────┐
│ Logs    │ Git     │ Metrics │
└────┬────┴────┬────┴────┬────┘
     └─────────┴──────────┘
              ↓
       Evidence Aggregator
              ↓
             RAG
              ↓
    Hypothesis Generator
              ↓
          Verifier
          ↙      ↘
 more evidence   enough
      ↓            ↓
 investigation  Root Cause
                    ↓
               Remediation
                    ↓
                Report
```

## MCP

Use only **2 MCP servers** initially.

### Observability MCP

Tools:

```text
search_logs()
get_error_rate()
get_latency()
get_db_connections()
get_service_health()
```

### Engineering MCP

Tools:

```text
get_recent_commits()
get_diff()
get_deployments()
```

## RAG

Store:

```text
knowledge/
├── runbooks/
├── historical_incidents/
├── architecture/
└── troubleshooting/
```

RAG should provide **context/evidence**, not directly decide the root cause.

## UI

Minimum:

```text
Incident Description
[____________________________]

[ INVESTIGATE ]

Investigation Status
✓ Logs
✓ Metrics
✓ Git
◉ Hypothesis Verification

Root Cause
...

Evidence
...

Recommended Action
...
```

## Definition of Done

Given:

> Payment API errors increased after deployment.

The system can:

- inspect logs
- inspect metrics
- inspect Git/deployment evidence
- retrieve relevant runbooks/incidents
- create competing hypotheses
- reject unsupported hypotheses
- produce an evidence-backed root cause
- recommend remediation

## Important

This version proves the hardest part:

> **Can the AI investigate well?**

Do not add continuous monitoring until this works.
