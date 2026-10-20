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

## Stage 3 — Live Evidence Collection

Collect structured evidence from the existing incident fixture and, when
requested, from live local services and repository history. Preserve fixture
mode as the deterministic default and keep live collection read-only.

The evidence model and shared incident state support this collection. Where a
live source is unavailable, record that limitation rather than inventing
evidence.

## Stage 4 — AI investigation, hypothesis verification, and RootCause

Build the investigation loop on the shared incident state and collected
evidence:

- Compile the LangGraph flow for intake, planning, investigation, and evidence
  aggregation.
- Add log, metrics, health, and Git investigator nodes.
- Generate competing hypotheses and verify them against evidence; analyze
  evidence gaps and contradictions.
- Bound verification to at most three cycles and allow an inconclusive result.
- Add the `RootCause` model when needed by the evidence-to-RCA implementation.
  Conclusions must cite genuine evidence IDs and account for contradictions.

## Stage 8 — RAG

Add:

- runbooks,
- small architecture doc,
- previous incident docs.

Measure whether RAG helps.

## Stage 9 — MCP

Wrap stable tools through MCP.

Do not change the agent contract.

## Later V1 — Remediation model

Add the `Remediation` model after the investigation and RCA baseline. It
supports recommendations only; execution and automatic remediation remain out
of scope.

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

## Forward plan — V3 dual-workflow multi-agent upgrade (no current implementation changes)

This section is **future-only** and does not alter the V1 stages above. V1 remains manually triggered with advisory recommendations and at most three verification cycles. V2 introduces alert-triggered invocation of the existing investigator. **V3** adds:

1. **V3-A:** cheap monitoring ON/OFF, anomaly rules, deduplication and checkpoints outside the LLM graphs.
2. **V3-B:** Investigation LangGraph Coordinator with specialized Observability/Engineering agents, optional Infrastructure agent, deterministic Evidence Aggregator, RAG context, Hypothesis Agent and independent Verification Agent.
3. **V3-C:** at least two tested **read-only MCP servers** (Observability + Engineering); conditional Infrastructure/Knowledge integrations; optional Jev for bounded advisory routing.
4. **V3-D:** independently invokable **Resolution LangGraph** with Resolution Coordinator, RCA Validation and Remediation Planning agents consuming versioned IncidentState/RCA handoff.
5. **V3-E:** hard risk and **human approval gate**, optional guarded sandbox Remediation MCP, Execution Agent, independent Recovery Verification Agent and bounded escalation/rollback decisions.
6. **V3-F:** incident history/UI/audit and end-to-end tests for delegations, evidence provenance, inconclusive results, approval denials, MCP failures and recovery.

**Exit condition:** demonstrably two coordinated agent workflows, with actual agent reasoning/tool boundaries, persisted shared state and scoped MCP. The original V0–V1 code and tests must continue to pass. Full target architecture: `ARCHITECTURE/08_V3_DUAL_ORCHESTRATION_MULTI_AGENT.md`.
