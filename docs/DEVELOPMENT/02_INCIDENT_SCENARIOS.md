# Incident Scenarios

## Purpose

Incidents are both:

1. the development playground,
2. the evaluation dataset.

## Scenario schema

Each incident should have a hidden answer key.

```json
{
  "incident_id": "INC-001",
  "root_cause": "...",
  "affected_services": ["..."],
  "required_evidence": ["..."],
  "red_herrings": ["..."],
  "expected_remediation": ["..."]
}
```

## INC-001 — Catalog Down

### Fault

Catalog process is stopped.

### Observable symptoms

- Catalog `/health` fails.
- Orders cannot reach Catalog.
- Gateway order-related requests fail.

### Correct RCA

Catalog service outage caused downstream Orders failures.

### Red herring

Gateway is where the user sees the failure, but Gateway is not the root cause.

## INC-002 — Catalog Slow

### Fault

Artificial delay is added to Catalog.

### Symptoms

- Catalog latency rises first.
- Orders calls time out.
- Gateway latency rises afterward.

### Correct RCA

Slow Catalog dependency creates cascading latency.

## INC-003 — Bad Orders Commit

### Fault

Introduce a real local Git commit that breaks Orders behavior.

### Symptoms

- deployment/start marker,
- errors begin shortly afterward,
- Git diff contains relevant change.

### Correct RCA

Specific code regression.

## INC-004 — Intermittent Failures

### Fault

Catalog fails only a percentage of requests.

### Goal

Test whether the system can reason from noisy evidence rather than a complete outage.

## INC-005 — Red Herring Commit

### Fault

Create a harmless recent commit.

Separately introduce an unrelated runtime failure.

### Goal

Test whether the system incorrectly blames the most recent code change.

## INC-006 — Overlapping Causes

Introduce two faults at once.

Example:

```text
catalog latency
+
small unrelated gateway error spike
```

Goal:

- separate primary and secondary problems,
- identify blast radius.

## INC-007 — Insufficient Evidence

Hide or remove a critical signal.

Expected correct behavior:

```text
inconclusive
```

not fabricated certainty.

## Later randomized scenarios

Use seeded generation so experiments remain reproducible.

Example:

```text
seed = 42
```

The same seed should produce the same incident.
