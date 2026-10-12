# LLM and Jev Placement

> **V1 implementation scope:** Manually triggered, local without Docker, read-only investigation and recommendations. Detection/always-on monitoring, automatic remediation, and production integrations are later versions. RAG and MCP are added after the working evidence-to-RCA baseline. Existing code must be inspected before assuming interfaces exist.


## Mental model

```text
LLM       = think, explain, generate
Jev       = classify, choose, score, gate
MCP       = access live systems
RAG       = retrieve organizational knowledge
LangGraph = connect nodes and edges
Code      = deterministic operations
```

## Use normal code for

- threshold checks,
- health polling,
- parsing,
- timestamps,
- retries,
- deterministic transformations,
- calculations,
- tool execution.

## Use LLMs for

- investigation planning,
- summarizing messy operational evidence,
- proposing competing hypotheses,
- identifying missing evidence,
- explaining causal chains,
- writing root-cause analysis,
- proposing remediation,
- generating the final incident report.

## Possible Jev usage

Jev is useful where the output is a bounded decision.

Examples:

```text
Is this alert incident-worthy?
Which service should be investigated next?
Which hypothesis has strongest evidence?
Is evidence sufficient?
Severity = low / medium / high?
Action risk = low / medium / high?
Auto-act or require human approval?
```

## Example architecture

```text
Monitoring
   ↓
normal anomaly detector
   ↓
Jev: incident-worthy?
   ↓
IncidentGraph
   ↓
LLM Planner
   ↓
Tools / MCP
   ↓
Evidence
   ↓
LLM Hypotheses
   ↓
Jev: score / choose / verify
   ↓
LLM RCA Explanation
   ↓
LLM Remediation
   ↓
Jev + hard rules: risk gate
```

## Initial implementation recommendation

First build with:

```text
normal code
+
LLM structured outputs
```

After the graph works, replace appropriate bounded decisions with Jev.

This allows measurement of what Jev actually improves.
