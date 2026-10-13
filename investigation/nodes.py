""" Investigation nodes for the LangGraph StateGraph.

Nodes are pure functions compatible with LangGraph's edge semantics:
  ``state = node(state)`` -> updated state dict.

All evidence is drawn from the existing V0 fixture (incidents/INC-001.json).
No LLM, RAG, or MCP calls are made. Never invents findings."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from common.incident_models import Evidence, map_v0_json_to_incident_state


def intake_node(state: dict[str, Any]) -> dict[str, Any]:
    """Validate incident and initialize V1 state from V0 JSON.

    On first call (no ``incident_id`` in state), loads and maps the
    incident from ``incidents/INC-001.json`` via the canonical mapper.
    """
    if not state.get("incident_id"):
        v0_path = Path("incidents/INC-001.json")
        with open(v0_path, "r", encoding="utf-8") as f:
            v0_incident = json.load(f)
        state = map_v0_json_to_incident_state(v0_incident)
    state.setdefault("status", "investigating")
    state.setdefault("iteration", 0)
    state.setdefault("max_iterations", 3)
    state.setdefault("root_cause", None)
    state.setdefault("evidence", [])
    state.setdefault("missing_evidence", [])
    state.setdefault("errors", [])
    state.setdefault("selected_hypothesis", None)
    return state


def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic investigation plan grounded in actual incident context.

    The planner looks at which services are affected and which evidence types
    are already available, then generates a prioritized list of evidence domains
    to investigate. No LLM is used - the logic is deterministic based on the
    incident description and affected services.
    """
    affected = state.get("affected_services", [])
    evidence = state.get("evidence", [])
    missing = state.get("missing_evidence", [])
    errors = state.get("errors", [])

    plan_steps: list[dict[str, Any]] = []

    if "catalog" in affected:
        plan_steps.append(
            {"domain": "logs", "reason": "CATALOG_REQUEST_FAILED errors in orders logs"}
        )
        plan_steps.append(
            {"domain": "metrics", "reason": "catalog_requests/catalog_failures metrics"}
        )
        has_commits = any(e.source_type == "commits" for e in evidence)
        if not has_commits:
            plan_steps.append({"domain": "commits", "reason": "recent git commits for catalog deployment"})

    if "orders" in affected:
        plan_steps.append(
            {"domain": "logs", "reason": "orders catalog failure logs"}
        )

    if not plan_steps:
        plan_steps.append({"domain": "none", "reason": "no additional evidence domains identified"})

    return {
        **state,
        "errors": errors + [f"planner_ran_services={affected}"],
    }


def evidence_node(state: dict[str, Any]) -> dict[str, Any]:
    """Populate evidence from existing V0 fixture.

    Uses incidents/INC-001.json. Preserves IDs, provenance, raw references,
    and explicitly marks unavailable data. Never invents findings.

    Returns state with evidence added/updated and missing_evidence adjusted.
    """
    v0_path = Path("incidents/INC-001.json")
    with open(v0_path, "r", encoding="utf-8") as f:
        v0_incident = json.load(f)

    v0_state = map_v0_json_to_incident_state(v0_incident)

    new_evidence: list[Evidence] = []

    for he in v0_state.get("evidence", []):
        if he.source_type == "health" and not any(e.id == he.id for e in state.get("evidence", [])):
            new_evidence.append(he)

    for le in v0_state.get("evidence", []):
        if le.source_type == "logs" and not any(e.id == le.id for e in state.get("evidence", [])):
            new_evidence.append(le)

    for me in v0_state.get("evidence", []):
        if me.source_type == "metrics" and not any(e.id == me.id for e in state.get("evidence", [])):
            new_evidence.append(me)

    for ce in v0_state.get("evidence", []):
        if ce.source_type == "commits" and not any(e.id == ce.id for e in state.get("evidence", [])):
            new_evidence.append(ce)

    new = state.get("missing_evidence", []) + (["no additional evidence domains in fixture"] if not new_evidence else [])

    return {
        **state,
        "evidence": state.get("evidence", []) + new_evidence,
        "missing_evidence": new,
        "errors": state.get("errors", []) + ["evidence_node_ran"],
    }