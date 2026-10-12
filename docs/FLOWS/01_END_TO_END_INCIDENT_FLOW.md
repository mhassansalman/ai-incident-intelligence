# End-to-End Incident Flow — V1

> V1 is invoked **manually**. The original monitoring/detection lifecycle belongs to later versions. There is no automatic action or approval-execution workflow in V1.

```text
Manual incident -> Plan -> Collect logs/metrics/health/Git
-> Normalize evidence -> Retrieve knowledge (later RAG)
-> Competing hypotheses -> Verify (maximum 3 cycles)
-> RCA or inconclusive -> Recommend (do not execute) -> Final report
```

## Phase 4 — Investigate

Planner asks only relevant specialists.

Example:

```text
gateway errors
→ logs + health + metrics

failure after deployment
→ logs + Git + deployment evidence
```

## Phase 5 — Explain

Generate multiple hypotheses, not one immediate answer.

## Phase 6 — Verify

Support or reject hypotheses with evidence.

## Phase 7 — Remediate

Propose mitigation and prevention.

## Phase 8 — Human authority

V1 only recommends actions; a human executes separately.

