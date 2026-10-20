"""Thin adapters for V0 evidence collectors.

Wraps services/tools collectors with:
- Graceful failure handling (never raises)
- Live/fixture mode selection
- Canonical Evidence dict output compatible with IncidentState.Evidence
- Provenance tracking (collected_by: 'fixture' or 'live')
- Deterministic IDs from V0 fixture; live evidence gets service-scoped IDs

Never fabricates data. Unavailable sources are marked with error summary.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.incident_models import Evidence

from services.tools.health import get_service_health
from services.tools.logs import search_logs
from services.tools.commits import get_recent_commits

# ---------------------------------------------------------------------------
# Fixture mode: deterministic load from V0 incident JSON
# ---------------------------------------------------------------------------


def _load_fixture_evidence(incident_id: str) -> list[Evidence]:
    """Load evidence from the V0 INC-001.json fixture via the canonical mapper.

    Returns Evidence dicts with 'fixture' provenance. IDs are deterministic
    from the fixture (e.g., 'health:gateway', 'logs:orders_catalog_failures').
    """
    fixture_path = Path("incidents/INC-001.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        v0 = json.load(f)

    # Use the canonical mapper from common/incident_models
    from common.incident_models import map_v0_json_to_incident_state

    v0_state = map_v0_json_to_incident_state(v0)

    evidence: list[Evidence] = []
    for ev in v0_state.get("evidence", []):
        # Ensure collected_by is 'fixture'
        ev_evidence = Evidence(
            id=ev.id,
            source_type=ev.source_type,
            source=ev.source,
            timestamp=ev.timestamp,
            summary=ev.summary,
            raw_reference=ev.raw_reference,
            relevance=None,  # V1: null until RAG baseline
            collected_by="fixture",
        )
        evidence.append(ev_evidence)

    return evidence


# ---------------------------------------------------------------------------
# Live mode: invoke V0 collectors with graceful error handling
# ---------------------------------------------------------------------------


def _live_health(service_name: str) -> dict[str, Any]:
    """Collect live health data for a single service.

    Returns a dict ready for Evidence conversion. On failure, returns
    structured error data (never raises).
    """
    try:
        result = get_service_health(service_name)
        # Convert to Evidence-compatible dict
        return {
            "service": result.get("service", service_name),
            "healthy": result.get("healthy", False),
            "status_code": result.get("status_code"),
            "url": result.get("url", ""),
            "error": result.get("error"),
        }
    except Exception as e:  # broad but contained; caller handles
        return {"service": service_name, "healthy": False, "error": str(e)}


def _live_logs(service_name: str, keyword: str) -> dict[str, Any]:
    """Collect live log search results for a service+keyword.

    On failure (missing log file, etc.), returns error dict (never raises).
    """
    try:
        result = search_logs(service_name, keyword)
        return {
            "service": result.get("service", service_name),
            "keyword": result.get("keyword", keyword),
            "matches": result.get("matches", []),
            "count": result.get("count", 0),
            "error": result.get("error"),
        }
    except Exception as e:  # broad but contained
        return {"service": service_name, "error": str(e)}


def _live_commits(limit: int = 5) -> dict[str, Any]:
    """Collect live recent commits.

    On failure (git not available, repo issues), returns error dict (never raises).
    """
    try:
        result = get_recent_commits(limit=limit)
        return {
            "available": result.get("available", False),
            "count": result.get("count", 0),
            "commits": result.get("commits", []),
            "error": result.get("error"),
        }
    except Exception as e:  # broad but contained
        return {"available": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Metrics: no dedicated live collector in V0 tools; use fixture fallback.
# ---------------------------------------------------------------------------


def _live_metrics() -> dict[str, Any]:
    """Return 'unavailable' for metrics since no live collector exists in V0 tools.

    This is intentional: V1 keeps the fixture-based metrics evidence
    deterministic and never fabricates live metrics data.
    """
    return {"available": False, "error": "no live metrics collector in V0 tools"}


# ---------------------------------------------------------------------------
# Evidence dict conversion from collector results
# ---------------------------------------------------------------------------


def _health_to_evidence(service_name: str, collector_result: dict[str, Any]) -> Evidence:
    """Convert a live health collector result to a canonical Evidence dict.

    If the service is healthy, we still produce an evidence entry with
    status info; if unhealthy, we include the error.
    """
    healthy = collector_result.get("healthy", False)
    error = collector_result.get("error")
    service = collector_result.get("service", service_name)
    url = collector_result.get("url", f"http://127.0.0.1:8000/health")

    if healthy:
        summary = f"Service {service} is healthy"
        raw_ref = f"health://{service}"
        if error:
            summary += f" (error: {error})"
    elif error:
        summary = f"Health collection unavailable for {service}: {error}"
        raw_ref = f"health://{service}"
    else:
        status_code = collector_result.get("status_code")
        summary = f"Service {service} is unhealthy"
        if status_code is not None:
            summary += f" (HTTP {status_code})"
        raw_ref = f"health://{service}"

    return Evidence(
        id=f"health:{service}",
        source_type="health",
        source=service,
        timestamp=datetime.now(timezone.utc).isoformat(),
        summary=summary,
        raw_reference=raw_ref,
        relevance=None,
        collected_by="live",
    )


def _logs_to_evidence(service_name: str, keyword: str, collector_result: dict[str, Any]) -> Evidence | None:
    """Convert a live logs collector result to a canonical Evidence dict.

    Returns None if no matches found and no error (graceful empty case).
    """
    matches = collector_result.get("matches", [])
    count = collector_result.get("count", 0)
    error = collector_result.get("error")

    if count > 0:
        # Build summary from actual matches
        match_messages = [m.get("message", "") for m in matches[:3]]
        summary = f"Found {count} matches for '{keyword}' in {service_name}"
        raw_ref = f"log://{service_name}/{keyword}"
        # Include first match preview
        if match_messages:
            summary += f": {match_messages[0][:80]}"
    elif error:
        summary = f"Log search failed for {service_name}: {error}"
        raw_ref = f"log://{service_name}/{keyword}"
    # No matches found and no error
    else:
        summary = f"No matches for '{keyword}' in {service_name} logs"
        raw_ref = f"log://{service_name}/{keyword}"

    return Evidence(
        id=f"logs:{service_name}_{keyword}",
        source_type="logs",
        source=service_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        summary=summary,
        raw_reference=raw_ref,
        relevance=None,
        collected_by="live",
    )


def _commits_to_evidence(collector_result: dict[str, Any]) -> list[Evidence]:
    """Convert live commits collector result to Evidence entries.

    Returns empty list if not available; never fabricates commit entries.
    """
    commits_data = collector_result.get("commits", [])
    available = collector_result.get("available", False)
    error = collector_result.get("error")

    evidence: list[Evidence] = []

    if available:
        for i, c in enumerate(commits_data[:3]):  # limit to 3 most recent
            commit_hash = c.get("hash", "")[:8] if c else ""
            author = c.get("author", "") if c else ""
            date = c.get("date", "") if c else ""
            message = c.get("message", "") if c else ""
            ev_id = f"commits:{commit_hash}" if commit_hash else f"commits:partial:{i}"
            summary = f"Commit: {message[:60]}"
            raw_ref = f"git://{commit_hash}" if commit_hash else f"git:partial:{i}"

            evidence.append(
                Evidence(
                    id=ev_id,
                    source_type="commits",
                    source="git",
                    timestamp=date,
                    summary=summary,
                    raw_reference=raw_ref,
                    relevance=None,
                    collected_by="live",
                )
            )
    else:
        # Even when unavailable, record that commits were investigated
        # with a single "unavailable" entry so the graph knows the domain was checked
        reason = error or "git is not available"
        evidence.append(
            Evidence(
                id="commits:unavailable",
                source_type="commits",
                source="git",
                timestamp="",
                summary=f"Git commits collection unavailable: {reason}",
                raw_reference=None,
                relevance=None,
                collected_by="live",
            )
        )

    return evidence


# -------------------------------------------------------------------------
# Main entry point: mode-gated evidence collection
# -------------------------------------------------------------------------


def collect_evidence(
    mode: str = "fixture",
    incident_id: str = "INC-001",
) -> dict[str, list[Evidence]]:
    """Collect evidence in the specified mode.

    Parameters:
        mode: "fixture" (default) or "live"
        incident_id: incident identifier (used for live mode context)

    Returns:
        dict mapping source_type -> list[Evidence] entries

    Mode Behavior:
        - "fixture": loads deterministic data from incidents/INC-001.json
          via the canonical mapper. Always succeeds; no network or file
          system dependencies beyond the fixture.
        - "live": attempts to invoke V0 collectors (health, logs, commits).
          Each collector independently handles failures; unavailable sources
          produce Evidence with error summaries, never exceptions.
          Metrics are always "unavailable" in live mode since no V0 live
          metrics collector exists.
    """
    result: dict[str, list[Evidence]] = {
        "health": [],
        "logs": [],
        "metrics": [],
        "commits": [],
    }

    if mode == "fixture":
        # Deterministic fixture mode - reuse existing V0 mapper
        fixture_evidence = _load_fixture_evidence(incident_id)
        # Distribute fixture evidence by source_type
        for ev in fixture_evidence:
            st = ev.source_type
            if st in result:
                result[st].append(ev)
        # Ensure all domains have at least an empty list
        return result

    # --- live mode ---
    # 1. Health evidence
    for svc in ["gateway", "orders", "catalog"]:
        live_result = _live_health(svc)
        ev = _health_to_evidence(svc, live_result)
        result["health"].append(ev)

    # 2. Logs evidence (orders + catalog keyword)
    for kw, svc in [("CATALOG_REQUEST_FAILED", "orders"), ("CATALOG_REQUEST_FAILED", "catalog")]:
        live_result = _live_logs(svc, kw)
        ev = _logs_to_evidence(svc, kw, live_result)
        if ev is not None:
            result["logs"].append(ev)

    # 3. Metrics - always unavailable in live mode (no live V0 collector)
    result["metrics"].append(
        Evidence(
            id="metrics:unavailable",
            source_type="metrics",
            source="",
            timestamp="",
            summary="Metrics evidence: unavailable (no live V0 collector); use fixture data",
            raw_reference=None,
            relevance=None,
            collected_by="live",
        )
    )

    # 4. Commits evidence
    live_result = _live_commits(limit=5)
    commits_ev = _commits_to_evidence(live_result)
    result["commits"].extend(commits_ev)

    return result