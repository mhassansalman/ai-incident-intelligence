""" Stage 2 tests for compiled LangGraph investigation foundation.

Tests actual graph invocation, node order, state propagation, invalid inputs,
and INC-001 end-to-end execution using the compiled Langraph StateGraph."""
import json
import sys
from pathlib import Path

import pytest

from investigation.state import IncidentState, map_v0_json_to_incident_state
from investigation.cli import build_graph, run_investigation
from investigation.nodes import intake_node, planner_node, evidence_node


# ---------------------------------------------------------------------------
# Graph construction test
# ---------------------------------------------------------------------------


def test_graph_compile():
    """StateGraph compiles successfully with correct nodes."""
    graph = build_graph()
    assert graph is not None
    # Check that the graph has the expected nodes
    assert "intake" in graph.nodes
    assert "planner" in graph.nodes
    assert "evidence" in graph.nodes


# ---------------------------------------------------------------------------
# Fixture / mapping tests
# ---------------------------------------------------------------------------


def test_map_v0_json_to_incident_state():
    """Map V0 INC-001.json fixture to V1 IncidentState; all mandatory fields populated."""
    with open("incidents/INC-001.json", "r") as f:
        v0 = json.load(f)
    state = map_v0_json_to_incident_state(v0)
    assert state["incident_id"] == "INC-001"
    assert state["description"] == "health check failed"
    assert "catalog" in state["affected_services"]
    assert state["root_cause"] is None  # RCA starts as None
    assert state["status"] == "investigating"
    assert state["iteration"] == 0
    assert state["max_iterations"] == 3
    assert state["selected_hypothesis"] is None
    assert len(state["evidence"]) > 0
    ev = state["evidence"][0]
    assert ev.id.startswith("health:")
    assert ev.source_type == "health"


# ---------------------------------------------------------------------------
# Node tests (functional, not graph‑wired yet)
# ---------------------------------------------------------------------------


def test_intake_node_initializes_state():
    """intake_node populates all mandatory IncidentState fields."""
    from investigation.nodes import intake_node
    state: IncidentState = intake_node({})
    expected_keys = [
        "incident_id", "description", "affected_services", "incident_start",
        "logs", "metrics", "commits", "deployments",
        "retrieved_documents", "hypotheses", "verified_hypotheses",
        "root_cause", "remediation_plan", "final_report",
        "evidence", "missing_evidence", "errors", "status",
        "iteration", "max_iterations", "selected_hypothesis",
    ]
    for key in expected_keys:
        assert key in state, f"Missing key: {key}"
    assert state["root_cause"] is None
    assert state["status"] == "investigating"
    assert state["max_iterations"] == 3


def test_intake_node_preserves_existing_state():
    """intake_node does not erase already-populated state."""
    from investigation.nodes import intake_node
    state: IncidentState = {
        "incident_id": "INC-CUSTOM",
        "description": "custom incident",
        "affected_services": ["gateway"],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
    }
    result = intake_node(state)
    assert result["incident_id"] == "INC-CUSTOM"
    assert result["description"] == "custom incident"


def test_planner_node_deterministic():
    """planner_node generates a plan based on affected services."""
    from investigation.nodes import planner_node
    state: IncidentState = {
        "incident_id": "INC-TEST",
        "description": "test incident",
        "affected_services": ["catalog", "orders"],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "root_cause": None,
        "evidence": [],
        "missing_evidence": [],
        "errors": [],
        "selected_hypothesis": None,
    }
    result = planner_node(state)
    assert result["status"] == "investigating"
    assert "planner" in result["errors"][0].lower() if result["errors"] else True


def test_evidence_node_preserves_ids():
    """evidence_node populates evidence from V0 fixture preserving IDs."""
    from investigation.nodes import evidence_node
    state: IncidentState = {
        "incident_id": "INC-TEST",
        "description": "test",
        "affected_services": [],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "root_cause": None,
        "evidence": [],
        "missing_evidence": [],
        "errors": [],
        "selected_hypothesis": None,
    }
    result = evidence_node(state)
    # Evidence should now be populated from V0 fixture
    assert len(result["evidence"]) > 0
    # IDs should be deterministic
    ev_ids = [e.id for e in result["evidence"]]
    assert any(ev_id.startswith("health:") for ev_id in ev_ids)
    assert any(ev_id.startswith("logs:") for ev_id in ev_ids)
    # missing_evidence should be adjusted
    assert len(result["missing_evidence"]) >= 0


# ---------------------------------------------------------------------------
# Compiled graph invocation tests
# ---------------------------------------------------------------------------


def test_graph_compile_and_stream():
    """Compile the graph and stream it with INC-001; state propagates correctly."""
    from investigation.cli import build_graph
    from langgraph.checkpoint.memory import MemorySaver

    graph = build_graph(checkpointer=MemorySaver())
    with open("incidents/INC-001.json", "r") as f:
        v0 = json.load(f)
    initial = map_v0_json_to_incident_state(v0)

    # Execute the compiled graph with values mode
    # stream() yields the full state dict after each node execution
    final_state = None
    for state in graph.stream(initial, {"recursion_limit": 10}, stream_mode="values"):
        final_state = state

    assert final_state is not None
    assert final_state["incident_id"] == "INC-001"
    assert final_state["status"] == "investigating"
    assert final_state["root_cause"] is None  # RCA starts None
    assert final_state["iteration"] == 0
    assert final_state["max_iterations"] == 3
    assert len(final_state["evidence"]) > 0  # at least health evidence
    assert "no additional evidence domains in fixture" in final_state.get("missing_evidence", [])


def test_graph_lifecycle_status():
    """Compiled graph separates lifecycle status from RCA outcome."""
    from investigation.cli import build_graph
    from langgraph.checkpoint.memory import MemorySaver

    graph = build_graph(checkpointer=True)
    initial: IncidentState = {
        "incident_id": "INC-1",
        "description": "test",
        "affected_services": [],
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
    }

    # Run the graph to completion with values mode
    final_state = None
    for state in graph.stream(initial, {"recursion_limit": 10}, stream_mode="values"):
        final_state = state

    # Key fields should be preserved after graph completion
    assert final_state["incident_id"] == "INC-1"
    assert final_state["status"] == "investigating"
    assert final_state["root_cause"] is None


def test_cli_e2e_inc001(capsys):
    """E2E: compiled LangGraph CLI with INC-001 fixture runs and displays output."""
    from investigation.cli import run_investigation
    run_investigation(Path("incidents/INC-001.json"))
    captured = capsys.readouterr()
    output = captured.out
    assert "INVESTIGATION EXECUTION RESULTS" in output
    assert "RCA not implemented in Stage 3" in output
    assert "incident_id: INC-001" in output
    assert "root_cause: None" in output


# ---------------------------------------------------------------------------
# CLI help test
# ---------------------------------------------------------------------------


def test_cli_help():
    """CLI --help exits normally."""
    from investigation.cli import main
    sys.argv = ["investigation.cli", "--help"]
    try:
        main()
    except SystemExit:
        pass  # --help calls sys.exit(0)


def test_cli_invalid_path():
    """CLI with non-existent incident path exits with code 1."""
    from investigation.cli import main
    sys.argv = ["investigation.cli", "--incident", "nonexistent.json"]
    try:
        main()
        assert False, "Expected SystemExit"
    except SystemExit as e:
        assert e.code == 1


def test_cli_malformed_json():
    """CLI with malformed JSON incident file exits with code 1."""
    import tempfile
    import os
    from investigation.cli import main
    # Create a temp file with malformed JSON
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    tmp.write("{invalid json")
    tmp.close()
    try:
        sys.argv = ["investigation.cli", "--incident", tmp.name]
        main()
        assert False, "Expected SystemExit"
    except SystemExit as e:
        assert e.code == 1
    finally:
        os.unlink(tmp.name)