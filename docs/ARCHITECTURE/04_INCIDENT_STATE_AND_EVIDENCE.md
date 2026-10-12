# Incident State and Evidence

## Core principle

The graph should pass structured state, not giant unstructured log dumps.

## Suggested IncidentState

```python
class IncidentState:
    incident_id: str
    title: str
    description: str
    affected_services: list[str]
    incident_start: str
    severity: str

    investigation_plan: dict

    evidence: list
    retrieved_knowledge: list
    hypotheses: list
    selected_hypothesis: dict | None
    missing_evidence: list

    iteration: int
    max_iterations: int

    root_cause: dict | None
    remediation: dict | None

    action_risk: str | None
    approval_required: bool
    human_decision: str | None

    final_report: str | None
    errors: list
    status: str
```

## Evidence model

```python
class Evidence:
    id: str
    source_type: str
    source: str
    timestamp: str | None
    summary: str
    raw_reference: str | None
    relevance: float | None
    collected_by: str
```

Example:

```json
{
  "id": "E-104",
  "source_type": "health",
  "source": "catalog-service",
  "timestamp": "2026-10-06T10:22:10+05:00",
  "summary": "Catalog health endpoint became unavailable.",
  "raw_reference": "health://catalog/2026-10-06T10:22:10",
  "relevance": 0.95,
  "collected_by": "health_investigator"
}
```

## Hypothesis model

```python
class Hypothesis:
    id: str
    claim: str
    supporting_evidence_ids: list[str]
    contradicting_evidence_ids: list[str]
    missing_evidence: list[str]
    confidence: float | None
    status: str
```

Example:

```json
{
  "id": "H-2",
  "claim": "Catalog service failure caused Orders timeouts.",
  "supporting_evidence_ids": ["E-104", "E-108", "E-111"],
  "contradicting_evidence_ids": [],
  "missing_evidence": ["confirm catalog failure preceded order errors"],
  "confidence": 0.82,
  "status": "under_review"
}
```

## Root-cause object

Suggested fields:

```text
summary
mechanism
affected_services
supporting_evidence_ids
contradicting_evidence_considered
confidence
limitations
```

## Important rules

### Evidence is not conclusion

Bad:

```text
Evidence:
"The recent deployment broke the application."
```

Better:

```text
Evidence:
"Deployment version 1.4.2 completed at 10:02."
```

Then reasoning can decide whether that deployment caused the incident.

### Preserve raw references

Never force the model to carry full logs forever.

Store:

```text
summary + reference
```

and fetch raw material only when needed.

### Every root cause should cite evidence

Example:

```text
Root cause:
Catalog service became unavailable, causing Orders dependency requests to time out.

Evidence:
E-104, E-108, E-111
```

### Allow uncertainty

The state must support:

```text
status = inconclusive
```

That is better than fabricated certainty.
