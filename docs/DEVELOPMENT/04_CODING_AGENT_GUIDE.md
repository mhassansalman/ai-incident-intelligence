# Coding Agent Guide

## Role

Coding agents are implementation assistants.

They are not the architecture owner.

## Mandatory reading before implementation

1. `../ARCHITECTURE/01_SYSTEM_ARCHITECTURE.md`
2. `../ARCHITECTURE/02_LANGGRAPH_ARCHITECTURE.md`
3. `../ARCHITECTURE/04_INCIDENT_STATE_AND_EVIDENCE.md`
4. `01_IMPLEMENTATION_PLAN.md`
5. the relevant progression/version document.

## Rules

1. Do not introduce future-version features unless requested.
2. Keep changes limited to the requested task.
3. Do not silently change architectural boundaries.
4. Agents must consume stable tool interfaces.
5. Environment-specific code belongs in providers/adapters.
6. Investigators return structured evidence.
7. Root-cause conclusions must cite evidence IDs.
8. Add or update tests for every implementation.
9. Prefer the simplest implementation that satisfies the current version.
10. Explain any necessary architecture deviation before making it.

## Recommended task format

```text
Task:
Implement the Log Investigator.

Read first:
- SYSTEM_ARCHITECTURE.md
- LANGGRAPH_ARCHITECTURE.md
- INCIDENT_STATE_AND_EVIDENCE.md

Allowed files:
- app/agents/log_investigator.py
- app/tools/logs.py
- tests/test_log_investigator.py

Requirements:
- use search_logs()
- return structured Evidence objects
- support service + time window filtering
- preserve raw references
- include tests

Do not:
- add MCP
- change the graph
- modify unrelated agents
```

## Branching strategy

Prefer:

```text
main
  ↓
feature/log-investigator
feature/metrics-provider
feature/incident-state
```

Review before merge.

## Agent review checklist

Before accepting generated code:

- Does it match the architecture?
- Does it solve only the requested problem?
- Are inputs/outputs structured?
- Are environment details properly isolated?
- Are tests meaningful?
- Did it introduce unnecessary dependencies?
- Could you explain the code yourself?

## Two-agent workflow

Useful pattern:

```text
Agent A → implement
Agent B → review against architecture + tests
Human  → final decision
```

The user remains the system architect.
