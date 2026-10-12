# Subgraphs and Agents

> **V1 implementation scope:** Manually triggered, local without Docker, read-only investigation and recommendations. Detection/always-on monitoring, automatic remediation, and production integrations are later versions. RAG and MCP are added after the working evidence-to-RCA baseline. Existing code must be inspected before assuming interfaces exist.


## Why subgraphs?

The main incident graph should stay readable.

Instead of one giant flat graph:

```text
Main IncidentGraph
    │
    ├── InvestigationSubgraph
    ├── KnowledgeSubgraph
    └── RemediationSubgraph
```

## 1. Investigation Subgraph

```mermaid
flowchart TD
    I[Investigation Request]
    I --> O[Observability Subgraph]
    I --> E[Engineering Subgraph]
    I --> D[Data / Infra Subgraph]
    O --> X[Evidence]
    E --> X
    D --> X
```

### Observability Subgraph

```text
Log Investigator
Metrics Investigator
Trace Investigator [later]
```

#### Log Investigator

Purpose:

- search errors,
- search by service/time window,
- identify repeated exceptions,
- detect correlated error patterns.

Should return structured evidence.

#### Metrics Investigator

Purpose:

- latency,
- error rate,
- request rate,
- CPU,
- memory,
- connection counts,
- service-specific metrics.

#### Trace Investigator

Later:

- identify slow spans,
- failing downstream services,
- request propagation,
- cross-service causal paths.

## 2. Engineering Subgraph

```text
Git Investigator
Deployment Investigator
```

### Git Investigator

Looks for:

- recent commits,
- changed files,
- diffs,
- relevant code changes,
- timing correlation.

### Deployment Investigator

Looks for:

- recent releases,
- deployment timestamps,
- version changes,
- rollback history,
- failed deployment signals.

## 3. Data / Infrastructure Subgraph

Future:

```text
Database Investigator
Docker Investigator
Kubernetes Investigator
Cloud Investigator
Network Investigator
```

These should be added only when the environment supports them.

## 4. Knowledge Subgraph

```mermaid
flowchart LR
    Q[Incident Context] --> QB[Query Builder]
    QB --> R[Retriever]
    R --> MF[Metadata Filter]
    MF --> RR[Reranker]
    RR --> K[Knowledge Evidence]
```

Purpose:

- find related incidents,
- fetch runbook steps,
- retrieve architecture knowledge,
- retrieve service ownership/dependency context.

## 5. Remediation Subgraph

```mermaid
flowchart TD
    RCA[Root Cause] --> GEN[Generate Actions]
    GEN --> RISK[Risk Assessment]
    RISK -->|safe recommendation| OUT[Report]
    RISK -->|risky write| HUMAN[Human Approval]
    HUMAN --> OUT
```

## Agent design rule

Do not create agents just because multiple agents look impressive.

Create a separate agent when at least one is true:

1. it owns a distinct toolset,
2. it reasons over a distinct evidence domain,
3. it needs a separate prompt/policy,
4. it benefits from independent parallel execution.

Otherwise use a normal function/node.
