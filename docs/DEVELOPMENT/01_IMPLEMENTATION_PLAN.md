# Implementation Plan

## Goal

Build the system in layers so every new technology has a measurable purpose.

## Stage 0 — Local production playground

Set up:

```text
Gateway
Orders
Catalog
```

Verify:

- service communication,
- health endpoints,
- local logs,
- basic metrics,
- Git history.

## Stage 1 — Incident scenarios + ground truth

Create controlled failures.

For each incident store a hidden answer key:

```text
incident_id
root_cause
required_evidence
red_herrings
expected_remediation
```

## Stage 2 — Plain Python tools

Implement and test:

```text
search_logs()
get_metrics()
get_service_health()
get_recent_commits()
```

No agents yet.

No MCP yet.

## Stage 3 — Evidence models

Create:

```text
Evidence
Hypothesis
RootCause
Remediation
```

## Stage 4 — IncidentState

Create the shared graph state.

## Stage 5 — Basic LangGraph

Initial graph:

```text
START
 ↓
Intake
 ↓
Planner
 ↓
Investigate
 ↓
Evidence
 ↓
END
```

## Stage 6 — Investigator nodes

Add:

- Log Investigator
- Metrics Investigator
- Health Investigator
- Git Investigator

## Stage 7 — Hypothesis + verification

Add:

```text
Hypothesis Generator
Verifier
Gap Analyzer
Root Cause
```

Include a hard iteration cap.

## Stage 8 — RAG

Add:

- runbooks,
- small architecture doc,
- previous incident docs.

Measure whether RAG helps.

## Stage 9 — MCP

Wrap stable tools through MCP.

Do not change the agent contract.

## Future versions only (not V1)

Stages 10–15 below are reference material, **not tasks for the current OpenCode V1 implementation**. Stage 12 minimal CLI/API/reporting may be brought forward after the V1 core is working; monitoring and automatic action remain out of scope.

## Stage 10 — Monitoring + detection

Build:

```text
Monitoring Worker
Detection Engine
Incident Trigger
```

Now the system becomes alert-triggered / always-on.

## Stage 11 — Remediation + approval

Initially:

```text
AI recommends
human executes
```

Later:

- risk gate,
- approval workflow,
- controlled write tools.

## Stage 12 — API / UI / observability

Add only after the core incident loop works.

## Stage 13 — Docker

Replace local providers with Docker-aware providers.

## Stage 14 — OpenTelemetry Demo

Add real:

- metrics,
- traces,
- richer logs,
- service topology.

## Stage 15 — Production integrations

Connect real systems.

## Golden rule

At each stage ask:

> What capability did this layer add, and can I measure the improvement?

Do not add LangGraph, RAG, MCP, Jev, or multi-agent complexity only because they are fashionable.
