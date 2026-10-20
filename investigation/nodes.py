""" Investigation nodes for the LangGraph StateGraph.

Nodes are pure functions compatible with LangGraph's edge semantics:
  ``state = node(state)`` -> updated state dict.

All evidence is drawn from the V0 fixture (incidents/INC-001.json) by default,
with optional live collection via the investigation.collectors adapters.
No LLM, RAG, or MCP calls are made. Never invents findings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from common.incident_models import Evidence, IncidentState, map_v0_json_to_incident_state

from investigation.collectors import collect_evidence


def intake_node(state: dict[str, Any]) -> dict[str, Any]:
    """Validate incident and initialize V1 state from V0 JSON.

    On first call (no ``incident_id`` in state), loads and maps the
    incident from ``incidents/INC-001.json`` via the canonical mapper.
    Sets default ``evidence_mode`` to ``"fixture"``.
    """
    if not state.get("incident_id"):
        v0_path = Path("incidents/INC-001.json")
        with open(v0_path, "r", encoding="utf-8") as f:
            v0_incident = json.load(f)
        state = map_v0_json_to_incident_state(v0_incident)

    # Set defaults
    state.setdefault("status", "investigating")
    state.setdefault("iteration", 0)
    state.setdefault("max_iterations", 3)
    state.setdefault("root_cause", None)
    state.setdefault("evidence", [])
    state.setdefault("missing_evidence", [])
    state.setdefault("errors", [])
    state.setdefault("selected_hypothesis", None)
    # Evidence mode: "fixture" (default, deterministic) or "live" (optional real collectors)
    state.setdefault("evidence_mode", "fixture")
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
        # Check if we have commits evidence already
        has_commits = any(e.source_type == "commits" for e in evidence)
        if not has_commits:
            plan_steps.append({"domain": "commits", "reason": "recent git commits for catalog deployment"})

    if "orders" in affected:
        plan_steps.append(
            {"domain": "logs", "reason": "orders catalog failure logs"}
        )

    if not plan_steps:
        plan_steps.append({"domain": "none", "reason": "no additional evidence domains identified"})

    # If in live mode and we don't have commits evidence, planner may note it
    if state.get("evidence_mode") == "live":
        plan_steps.append(
            {"domain": "commits", "reason": "live git commits collection (may be unavailable)"}
        )

    # Preserve existing errors; do not inject planner diagnostic marker.
    # Genuine collection errors (e.g. from evidence_node) are already in state.
    return {
        **state,
    }


def evidence_node(state: dict[str, Any]) -> dict[str, Any]:
    """Populate evidence from V0 fixture and/or live collectors.

    Behavior depends on ``state.evidence_mode``:

    - ``"fixture"`` (default): loads deterministic evidence from
      ``incidents/INC-001.json`` via the canonical mapper. This is the
      V0-represerving mode; all tests pass without any live services.

    - ``"live"``: attempts to invoke V0 collectors (health, logs, commits)
      through thin adapters in ``investigation.collectors``. Each collector
      independently handles failures; unavailable sources produce Evidence
      with error summaries, never exceptions. Metrics are always marked
      unavailable since no live V0 metrics collector exists.

    The aggregation strategy:
      1. Fixture evidence provides deterministic baseline (always included).
      2. Live evidence overlays on top, keyed by source_type.
      3. If a live collector fails, an Evidence entry with an error
         summary is added so the graph knows the domain was checked.
      4. ``missing_evidence`` is adjusted to reflect what was/wasn't found.

    Returns state with ``evidence``, ``missing_evidence``, and ``errors``
    updated.
    """
    mode = state.get("evidence_mode", "fixture")

    # --- Fixture mode: deterministic load from V0 INC-001.json ---
    if mode == "fixture":
        fixture_path = Path("incidents/INC-001.json")
        with open(fixture_path, "r", encoding="utf-8") as f:
            v0_incident = json.load(f)

        v0_state = map_v0_json_to_incident_state(v0_incident)
        fixture_evidence = [
            ev.model_copy(update={"collected_by": "fixture"})
            for ev in v0_state.get("evidence", [])
        ]

        # Fixture mode: replace evidence with the deterministic fixture set,
        # preserving the Stage 2 contract marker for missing_evidence.
        # The fixture evidence already contains all domains present in INC-001.
        return {
            **state,
            "evidence": list(fixture_evidence),  # replace, not append
            "missing_evidence": ["no additional evidence domains in fixture"],
            "errors": [
                error
                for error in state.get("errors", [])
                if error
                not in {
                    "evidence_node_fixture_mode",
                    "evidence_node_live_mode_attempted",
                }
            ],
        }

    # --- Live mode: attempt collectors via adapters ---
    from investigation.collectors import collect_evidence as _collect

    # Collect fixture baseline first (always succeeds)
    fixture_evidence_by_type: dict[str, list] = {"health": [], "logs": [], "metrics": [], "commits": []}
    for ev in state.get("evidence", []):
        st = ev.source_type
        if st in fixture_evidence_by_type:
            fixture_evidence_by_type[st].append(
                ev.model_copy(update={"collected_by": "fixture"})
            )

    # Collect live evidence
    live_evidence_by_type = _collect(mode="live", incident_id=state.get("incident_id", "INC-001"))

    # Merge: fixture first, keeping colliding live evidence under distinct IDs.
    merged: dict[str, list] = {}
    for key in fixture_evidence_by_type:
        merged[key] = list(fixture_evidence_by_type[key])  # start with fixture

    for domain, entries in live_evidence_by_type.items():
        existing_ids = {e.id for e in merged.get(domain, [])}
        for ev in entries:
            base_id = ev.id
            candidate_id = base_id
            if candidate_id in existing_ids:
                candidate_id = f"{base_id}_live"
                suffix = 2
                while candidate_id in existing_ids:
                    candidate_id = f"{base_id}_live_{suffix}"
                    suffix += 1
            ev.id = candidate_id
            ev.collected_by = "live"
            merged.setdefault(domain, []).append(ev)
            existing_ids.add(candidate_id)

    # Compute missing live evidence independently from the fixture baseline.
    all_evidence = merged["health"] + merged["logs"] + merged["metrics"] + merged["commits"]
    missing: list[str] = []
    operational_errors: list[str] = []
    for domain in ("health", "logs", "metrics", "commits"):
        live_entries = live_evidence_by_type.get(domain, [])
        if not live_entries:
            missing.append(f"{domain} evidence not collected")
            continue

        for ev in live_entries:
            summary = ev.summary or ""
            unavailable_reason = None
            if domain == "health" and summary.startswith("Health collection unavailable"):
                unavailable_reason = summary
            elif domain == "logs" and summary.startswith("Log search failed"):
                unavailable_reason = summary
            elif domain == "commits" and summary.startswith("Git commits collection unavailable"):
                unavailable_reason = summary
            elif domain == "metrics" and "unavailable" in summary.lower():
                missing.append("metrics evidence not collected (no live V0 collector)")

            if unavailable_reason:
                missing.append(f"{domain} evidence unavailable for {ev.source}")
                operational_errors.append(unavailable_reason)

    # Discard the old diagnostic marker if present in resumed state; only
    # operational failures belong in errors.
    new_errors = [
        error
        for error in state.get("errors", [])
        if error not in {
            "evidence_node_fixture_mode",
            "evidence_node_live_mode_attempted",
        }
    ]
    new_errors.extend(operational_errors)
    new_errors = list(dict.fromkeys(new_errors))
    missing = list(dict.fromkeys(missing))

    return {
        **state,
        "evidence": all_evidence,
        "missing_evidence": missing if missing else [],
        "errors": new_errors,
    }