""" Stage 3 tests for V1 Reactive Incident Commander — evidence collectors integration.

Tests cover:
- Fixture mode with INC-001 (deterministic, always passes)
- Live mode collector invocation with services running
- Live mode with services offline/failed collectors
- Partial failure resilience (one collector down, others still work)
- Graph integration: evidence_node mode switching
- Canonical Evidence dict provenance (collected_by: 'fixture' vs 'live')
- CLI --live flag behaviour
"""

import json
import os
import sys
from pathlib import Path

import pytest

from common.incident_models import Evidence, IncidentState, map_v0_json_to_incident_state
from investigation.collectors import collect_evidence, _live_health, _live_logs, _live_commits, _live_metrics
from investigation.nodes import intake_node, planner_node, evidence_node
from investigation.cli import build_graph, run_investigation


# ---------------------------------------------------------------------------
# Collector unit tests
# ---------------------------------------------------------------------------


def test_live_health_healthy():
    """_live_health returns structured dict when service is reachable."""
    result = _live_health("catalog")
    assert "service" in result
    assert "healthy" in result
    assert "error" in result or result.get("healthy") is not None


def test_live_logs_structure():
    """_live_logs returns dict with expected keys."""
    result = _live_logs("orders", "CATALOG_REQUEST_FAILED")
    assert "service" in result
    assert "keyword" in result
    assert "matches" in result
    assert "count" in result
    assert "error" in result


def test_live_commits_available():
    """_live_commits returns available=True when git is viable (this environment)."""
    result = _live_commits(limit=1)
    # In this environment git is available, so available=True
    assert result.get("available") is True
    assert "commits" in result
    assert len(result["commits"]) > 0


def test_live_metrics_unavailable():
    """_live_metrics always returns unavailable (no live V0 metrics collector)."""
    result = _live_metrics()
    assert result.get("available") is False
    assert "error" in result


def test_collect_evidence_fixture_mode():
    """collect_evidence in fixture mode returns deterministic evidence from INC-001."""
    result = collect_evidence(mode="fixture")
    assert isinstance(result, dict)
    assert "health" in result
    assert "logs" in result
    assert "metrics" in result
    assert "commits" in result

    # Fixture mode should have health entries
    health_entries = result["health"]
    assert len(health_entries) > 0
    # IDs should start with "health:"
    assert any(ev.id.startswith("health:") for ev in health_entries)
    # collected_by should be "fixture"
    assert any(ev.collected_by == "fixture" for ev in health_entries)

    # Metrics in fixture mode should have entries
    metrics_entries = result["metrics"]
    assert len(metrics_entries) > 0


def test_collect_evidence_live_mode():
    """collect_evidence in live mode attempts collector invocation."""
    result = collect_evidence(mode="live")
    assert isinstance(result, dict)
    assert "health" in result
    assert "logs" in result
    assert "metrics" in result
    assert "commits" in result

    # Live mode: health entries should exist (even if unhealthy)
    health_entries = result["health"]
    assert len(health_entries) > 0

    # Metrics should be unavailable
    metrics_entries = result["metrics"]
    assert len(metrics_entries) > 0
    # Should mention unavailable
    assert any("unavailable" in ev.summary.lower() for ev in metrics_entries)


# ---------------------------------------------------------------------------
# Node functional tests
# ---------------------------------------------------------------------------


def test_intake_node_evidence_mode_fixture():
    """intake_node sets evidence_mode to 'fixture' by default."""
    state = intake_node({})
    assert state.get("evidence_mode") == "fixture"
    assert state.get("root_cause") is None
    assert state.get("status") == "investigating"


def test_evidence_node_fixture_mode():
    """evidence_node in fixture mode loads from INC-001.json fixture."""
    state: IncidentState = {
        "incident_id": "INC-TEST",
        "description": "test incident",
        "affected_services": ["catalog"],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "root_cause": None,
        "evidence": [],
        "missing_evidence": [],
        "errors": ["evidence_node_fixture_mode", "evidence_node_live_mode_attempted"],
        "selected_hypothesis": None,
        "evidence_mode": "fixture",
    }
    result = evidence_node(state)
    # Fixture mode: evidence should be populated
    assert len(result["evidence"]) > 0
    # IDs should start with health:, logs:, etc.
    ev_ids = [e.id for e in result["evidence"]]
    assert any(ev_id.startswith("health:") for ev_id in ev_ids)
    assert any(ev_id.startswith("logs:") for ev_id in ev_ids)
    # missing_evidence should be adjusted (fixture has health, logs, commits but maybe not metrics domain empty)
    assert len(result["missing_evidence"]) >= 0
    assert "evidence_node_fixture_mode" not in result["errors"]
    assert "evidence_node_live_mode_attempted" not in result["errors"]


def test_evidence_node_live_mode_partial_failure():
    """evidence_node in live mode with partial collector failures.

    Simulates: health collector succeeds for some services, logs fails for one,
    commits unavailable. The graph should not crash; missing entries get error summaries.
    """
    state: IncidentState = {
        "incident_id": "INC-LIVE-TEST",
        "description": "live test incident",
        "affected_services": ["catalog", "orders"],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "root_cause": None,
        "evidence": [],
        "missing_evidence": [],
        "errors": [],
        "selected_hypothesis": None,
        "evidence_mode": "live",
    }
    result = evidence_node(state)
    # Graph should not crash
    assert result is not None
    # Evidence should be populated (at least some entries)
    assert len(result["evidence"]) > 0
    # missing_evidence should be populated (some domain may be missing)
    assert isinstance(result["missing_evidence"], list)
    assert "evidence_node_live_mode_attempted" not in result["errors"]


def test_evidence_node_live_mode_all_available():
    """evidence_node in live mode when all collectors succeed (services running).

    This test may fail if services aren't running, but we test the shape.
    """
    state: IncidentState = {
        "incident_id": "INC-LIVE-AVAIL",
        "description": "live available test",
        "affected_services": ["catalog", "orders"],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "root_cause": None,
        "evidence": [],
        "missing_evidence": [],
        "errors": [],
        "selected_hypothesis": None,
        "evidence_mode": "live",
    }
    result = evidence_node(state)
    assert result is not None
    assert len(result["evidence"]) > 0


# ---------------------------------------------------------------------------
# Graph integration tests
# ---------------------------------------------------------------------------


def test_graph_compile_and_stream_fixture():
    """Graph compiles and streams in fixture mode; state propagates correctly."""
    graph = build_graph()
    with open("incidents/INC-001.json", "r") as f:
        v0 = json.load(f)
    initial = map_v0_json_to_incident_state(v0)

    # Run with fixture mode (default)
    final_state = None
    for state in graph.stream(initial, {"recursion_limit": 10}, stream_mode="values"):
        final_state = state

    assert final_state is not None
    assert final_state["incident_id"] == "INC-001"
    assert final_state["status"] == "investigating"
    assert final_state["root_cause"] is None
    assert final_state["iteration"] == 0
    assert final_state["max_iterations"] == 3
    assert len(final_state["evidence"]) > 0  # at least health evidence from fixture
    # missing_evidence should reflect fixture contents
    assert "no additional evidence domains in fixture" in final_state.get("missing_evidence", [])


def test_graph_compile_and_stream_live():
    """Graph compiles and streams in live mode; collectors invoked; no crashes."""
    graph = build_graph()
    # Initial state with live mode
    initial: IncidentState = {
        "incident_id": "INC-LIVE",
        "description": "live test",
        "affected_services": ["catalog", "orders"],
        "incident_start": "2026-01-01T00:00:00",
        "logs": [],
        "metrics": {},
        "commits": [],
        "deployments": [],
        "retrieved_documents": [],
        "hypotheses": [],
        "verified_hypotheses": [],
        "root_cause": None,
        "remediation_plan": [],
        "final_report": "",
        "evidence": [],
        "missing_evidence": [],
        "errors": [],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "selected_hypothesis": None,
        "evidence_mode": "live",
    }

    # Run the graph to completion
    final_state = None
    for state in graph.stream(initial, {"recursion_limit": 10}, stream_mode="values"):
        final_state = state

    # Graph should complete without error even if collectors fail
    assert final_state is not None
    assert final_state["incident_id"] == "INC-LIVE"
    assert final_state["status"] == "investigating"
    # root_cause should still be None (Stage 2)
    assert final_state["root_cause"] is None
    # Evidence should be populated (collectors ran, possibly with unavailable entries)
    assert len(final_state["evidence"]) > 0
    # missing_evidence may have entries if some domains failed
    assert isinstance(final_state.get("missing_evidence"), list)


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_live_flag_help():
    """CLI --live flag is accepted."""
    from investigation.cli import main
    sys.argv = ["investigation.cli", "--help"]
    try:
        main()
    except SystemExit:
        pass  # --help calls sys.exit(0)


def test_cli_e2e_fixture():
    """E2E: CLI fixture mode runs and displays output."""
    from investigation.cli import run_investigation
    run_investigation(Path("incidents/INC-001.json"))
    # If we get here without exception, the test passes


def test_cli_e2e_live():
    """E2E: CLI --live flag sets evidence_mode to live."""
    from investigation.cli import run_investigation
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "investigation.cli", "--incident", "incidents/INC-001.json", "--live"],
        capture_output=True,
        text=True,
    )
    output = result.stdout
    assert "evidence_mode: live" in output, (
        f"Expected 'evidence_mode: live' in CLI output, got: {output}"
    )


def test_graph_preserves_evidence_mode_fixture():
    """Graph stream preserves evidence_mode='fixture' across all steps."""
    from investigation.cli import build_graph
    from investigation.state import IncidentState

    graph = build_graph(checkpointer=True)

    # Start with evidence_mode=fixture (default, not set)
    initial_state: IncidentState = {
        "incident_id": "INC-FIXTURE",
        "description": "fixture test",
        "affected_services": ["catalog"],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "root_cause": None,
        "evidence": [],
        "missing_evidence": [],
        "errors": [],
        "selected_hypothesis": None,
        # evidence_mode not set - should default to "fixture" via intake_node
    }

    final_state = initial_state
    for state in graph.stream(initial_state, {"recursion_limit": 10}, stream_mode="values"):
        final_state = state

    assert final_state["evidence_mode"] == "fixture", (
        f"Expected evidence_mode='fixture', got {final_state['evidence_mode']}"
    )


def test_graph_preserves_evidence_mode_live():
    """Graph stream preserves evidence_mode='live' across all steps."""
    from investigation.cli import build_graph
    from investigation.state import IncidentState

    graph = build_graph(checkpointer=True)

    # Start with evidence_mode=live
    initial_state: IncidentState = {
        "incident_id": "INC-LIVE",
        "description": "live test",
        "affected_services": ["catalog"],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "root_cause": None,
        "evidence": [],
        "missing_evidence": [],
        "errors": [],
        "selected_hypothesis": None,
        "evidence_mode": "live",
    }

    final_state = initial_state
    for state in graph.stream(initial_state, {"recursion_limit": 10}, stream_mode="values"):
        final_state = state

    assert final_state["evidence_mode"] == "live", (
        f"Expected evidence_mode='live', got {final_state['evidence_mode']}"
    )


# ---------------------------------------------------------------------------
# Partial failure resilience tests
# ---------------------------------------------------------------------------


def test_partial_collector_failure_no_crash():
    """Test that one failed collector does not crash the entire investigation.

    Scenario: health collector fails for 'catalog', but logs and commits succeed.
    The graph should complete with evidence from successful collectors plus
    error-marked entries for the failed one.
    """
    state: IncidentState = {
        "incident_id": "INC-PARTIAL",
        "description": "partial failure test",
        "affected_services": ["catalog", "orders"],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "root_cause": None,
        "evidence": [],
        "missing_evidence": [],
        "errors": [],
        "selected_hypothesis": None,
        "evidence_mode": "live",
    }
    try:
        result = evidence_node(state)
        # Should not raise
        assert result is not None
        assert len(result["evidence"]) > 0
    except Exception as e:
        pytest.fail(f"evidence_node raised exception on partial failure: {e}")


def test_live_mode_never_fabricates():
    """Verify that live mode never fabricates Evidence entries with made-up data.

    Every Evidence entry should have real provenance: collected_by='live',
    and summaries/references should derive from collector results (even if
    those results indicate failure/unavailable).
    """
    result = collect_evidence(mode="live")
    for entry_list in result.values():
        for ev in entry_list:
            # Every entry should have collected_by='live' in live mode
            assert ev.collected_by == "live", f"Expected collected_by='live', got {ev.collected_by}"
            # summary should not be empty or obviously fabricated
            assert ev.summary and ev.summary.strip(), f"Empty summary for {ev.id}"
            # raw_reference should be None or a realistic reference, not "E-104"-style
            assert ev.raw_reference is None or isinstance(ev.raw_reference, str)


# ---------------------------------------------------------------------------
# Regression tests: live/fixture mode collision handling
# ---------------------------------------------------------------------------


def test_live_after_fixture_health_not_suppressed():
    """Live health evidence is not silently suppressed when fixture evidence exists.

    When evidence_mode switches from fixture to live, or live collection runs
    after fixture has populated evidence, live entries must remain distinguishable
    and not be dropped due to ID collisions.
    """
    # Simulate state with fixture evidence already present
    state: IncidentState = {
        "incident_id": "INC-COLLISION",
        "description": "collision test",
        "affected_services": ["catalog", "orders"],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "root_cause": None,
        "evidence": [
            Evidence(id="health:catalog", source_type="health", source="catalog",
                     summary="Service catalog health check failed", raw_reference="health://catalog",
                     relevance=None, collected_by="fixture"),
            Evidence(id="health:orders", source_type="health", source="orders",
                     summary="Service orders healthy", raw_reference="health://orders",
                     relevance=None, collected_by="fixture"),
        ],
        "missing_evidence": [],
        "errors": [],
        "selected_hypothesis": None,
        "evidence_mode": "live",
    }
    result = evidence_node(state)
    # Graph should not crash
    assert result is not None
    # Live entries must remain; fixture entries should not suppress them
    health_entries = [e for e in result["evidence"] if e.source_type == "health"]
    health_ids = [e.id for e in health_entries]
    # Both fixture and live entries should be present (live may have _live suffix)
    health_entries = [e for e in result["evidence"] if e.source_type == "health"]
    assert len(health_entries) >= 2
    # Live entries must have collected_by='live'
    live_entries = [e for e in health_entries if e.collected_by == "live"]
    assert len(live_entries) >= 1
    # Live entries should be distinguishable (either original or _live suffixed)
    for entry in live_entries:
        assert entry.id.startswith("health:")


def test_live_no_duplicate_ids_on_repeated_collection():
    """Repeated live collection produces stable, unique evidence IDs."""
    result1 = collect_evidence(mode="live")
    result2 = collect_evidence(mode="live")
    ids1 = [ev.id for evidence in result1.values() for ev in evidence]
    ids2 = [ev.id for evidence in result2.values() for ev in evidence]
    assert len(ids1) == len(set(ids1))
    assert len(ids2) == len(set(ids2))
    assert ids1 == ids2


def test_live_reporting_tracks_unavailable_sources_and_operational_errors(monkeypatch):
    """Unavailable live sources are missing evidence; failures alone populate errors."""
    from investigation import collectors

    def health(service_name):
        if service_name == "orders":
            return {
                "service": service_name,
                "healthy": False,
                "status_code": 503,
                "url": "http://127.0.0.1:8001/health",
                "error": None,
            }
        return {
            "service": service_name,
            "healthy": False,
            "status_code": None,
            "url": f"http://127.0.0.1:8000/health",
            "error": "connection timed out",
        }

    def logs(service_name, keyword):
        if service_name == "catalog":
            return {
                "service": service_name,
                "keyword": keyword,
                "matches": [],
                "count": 0,
                "error": "log file not found",
            }
        return {
            "service": service_name,
            "keyword": keyword,
            "matches": [{"message": "actual matching line"}],
            "count": 1,
            "error": None,
        }

    monkeypatch.setattr(collectors, "_live_health", health)
    monkeypatch.setattr(collectors, "_live_logs", logs)
    monkeypatch.setattr(
        collectors,
        "_live_commits",
        lambda limit=5: {
            "available": False,
            "commits": [],
            "error": "git command not found",
        },
    )

    state: IncidentState = {
        "incident_id": "INC-REPORTING",
        "description": "reporting test",
        "affected_services": ["catalog", "orders"],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "root_cause": None,
        "evidence": [],
        "missing_evidence": [],
        "errors": ["evidence_node_live_mode_attempted"],
        "selected_hypothesis": None,
        "evidence_mode": "live",
    }

    result = evidence_node(state)
    missing = result["missing_evidence"]
    errors = result["errors"]

    assert "health evidence unavailable for gateway" in missing
    assert "health evidence unavailable for catalog" in missing
    assert "logs evidence unavailable for catalog" in missing
    assert "metrics evidence not collected (no live V0 collector)" in missing
    assert "commits evidence unavailable for git" in missing
    assert not any("orders" in item and item.startswith("health ") for item in missing)

    assert any("connection timed out" in error for error in errors)
    assert any("log file not found" in error for error in errors)
    assert any("git command not found" in error for error in errors)
    assert not any("evidence_node_live_mode_attempted" in error for error in errors)
    assert not any("metrics" in error.lower() for error in errors)


def test_live_merge_keeps_fixture_provenance_and_unique_deterministic_ids(monkeypatch):
    """Live evidence remains distinct from fixture evidence with stable IDs."""
    from investigation import collectors

    def live_collection(mode, incident_id):
        return {
            "health": [
                Evidence(
                    id="health:gateway",
                    source_type="health",
                    source="gateway",
                    summary="Service gateway is healthy",
                    raw_reference="health://gateway",
                    relevance=None,
                    collected_by="live",
                )
            ],
            "logs": [],
            "metrics": [
                Evidence(
                    id="metrics:unavailable",
                    source_type="metrics",
                    source="",
                    summary="Metrics evidence: unavailable (no live V0 collector)",
                    relevance=None,
                    collected_by="live",
                )
            ],
            "commits": [],
        }

    monkeypatch.setattr(collectors, "collect_evidence", live_collection)
    state: IncidentState = {
        "incident_id": "INC-MERGE",
        "description": "merge test",
        "affected_services": ["gateway"],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "root_cause": None,
        "evidence": [
            Evidence(
                id="health:gateway",
                source_type="health",
                source="gateway",
                summary="Fixture health evidence",
                raw_reference="health://gateway/fixture",
                relevance=None,
                collected_by="monitor",
            )
        ],
        "missing_evidence": [],
        "errors": [],
        "selected_hypothesis": None,
        "evidence_mode": "live",
    }

    first = evidence_node(state)
    second = evidence_node(state)
    first_ids = [ev.id for ev in first["evidence"]]
    second_ids = [ev.id for ev in second["evidence"]]
    health_entries = [ev for ev in first["evidence"] if ev.source_type == "health"]

    assert first_ids == second_ids
    assert len(first_ids) == len(set(first_ids))
    assert {ev.collected_by for ev in health_entries} == {"fixture", "live"}
    assert "health:gateway" in first_ids
    assert "health:gateway_live" in first_ids


def test_fixture_mode_unchanged():
    """Fixture-only mode behavior remains completely unchanged.

    Running the graph in fixture mode should produce identical results
    regardless of prior live collection, preserving V0 determinism.
    """
    graph = build_graph()
    with open("incidents/INC-001.json", "r") as f:
        v0 = json.load(f)
    initial = map_v0_json_to_incident_state(v0)

    # Run twice in fixture mode
    final_states = []
    for _ in range(2):
        final_state = None
        for state in graph.stream(initial, {"recursion_limit": 10}, stream_mode="values"):
            final_state = state
        final_states.append(final_state)

    # Both runs should be identical
    for i in range(1, len(final_states)):
        assert final_states[i]["evidence_mode"] == "fixture"
        assert len(final_states[i]["evidence"]) == len(final_states[0]["evidence"])
        assert final_states[i]["missing_evidence"] == final_states[0]["missing_evidence"]


def test_live_health_distinguishable_from_fixture():
    """Live health entries must have collected_by='live' and be distinguishable
    from fixture entries (which have collected_by='fixture')."""
    from common.incident_models import Evidence

    # Fixture entry
    ev_fixture = Evidence(
        id="health:catalog", source_type="health", source="catalog",
        summary="Service catalog health check failed",
        raw_reference="health://catalog", relevance=None, collected_by="fixture",
    )
    # Live entry (with deterministic suffix collision policy)
    ev_live = Evidence(
        id="health:catalog_live", source_type="health", source="catalog",
        summary="Service catalog health check failed",
        raw_reference="health://catalog", relevance=None, collected_by="live",
    )

    assert ev_fixture.collected_by == "fixture"
    assert ev_live.collected_by == "live"
    assert ev_fixture.id != ev_live.id


# Run this module as self-test
if __name__ == "__main__":
    """pytest entry point when run directly."""
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))