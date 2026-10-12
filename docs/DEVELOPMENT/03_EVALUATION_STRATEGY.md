# Evaluation Strategy

## Evaluation starts early

Do not wait until the enterprise version.

Evaluation begins with the first controlled incidents.

## Ground truth

Each scenario has a hidden answer key.

The investigating system should not have direct access to it.

## Core metrics

### Detection

```text
incident detection accuracy
false-positive rate
false-negative rate
time-to-detection
```

### Investigation

```text
root-cause accuracy
evidence precision
evidence recall
hypothesis quality
number of investigation loops
tool-call count
time-to-RCA
```

### Reasoning

Check whether the final RCA:

- cites valid evidence IDs,
- considers competing hypotheses,
- acknowledges contradictions,
- avoids unsupported claims,
- returns inconclusive when evidence is insufficient.

### Cost / efficiency

Later track:

```text
tokens
LLM calls
tool calls
latency
estimated cost
```

## Simple RCA scoring

Example rubric:

```text
0 = wrong / unsupported
1 = correct affected service only
2 = correct failure category
3 = correct root cause
4 = correct root cause + valid evidence
5 = correct root cause + evidence + causal explanation + proper uncertainty
```

## Layer-by-layer comparison

Measure:

```text
plain Python tools
        ↓
+ LangGraph
        ↓
+ RAG
        ↓
+ MCP
        ↓
+ Jev / bounded decisions
```

This shows which architectural additions actually improve results.

## RAG contamination rule

Do not include the exact evaluation answer in the knowledge base.

## Verifier rule

The verifier must cite evidence IDs.

A second model agreeing with the first is not sufficient verification.

## Inconclusive scenario

At least one evaluation incident must genuinely lack enough evidence.

Expected result:

```text
cannot determine reliably from available evidence
```
