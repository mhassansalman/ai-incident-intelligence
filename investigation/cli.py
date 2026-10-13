""" CLI entry point for minimal incident investigation using compiled LangGraph.

Usage:
    python -m investigation.cli --incident incidents/INC-001.json

This compiles a StateGraph (START -> Intake -> Planner -> Evidence -> END)
and invokes it, displaying results. RCA (Root Cause Analysis) is required
later in V1 but is not implemented in Stage 2; the investigation stops
after evidence aggregation with root_cause=None."""
import argparse
import json
import sys
from pathlib import Path
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from investigation.state import IncidentState, map_v0_json_to_incident_state
from investigation.nodes import intake_node, planner_node, evidence_node


def build_graph(checkpointer: bool = False) -> Any:
    """Build and return a compiled LangGraph StateGraph.

    If checkpointer=True, a MemorySaver checkpointer is attached so the
    graph can resume across runs. Required for graph.stream() to avoid
    the "Checkpointer requires configurable keys" ValueError."""
    graph = StateGraph(IncidentState)
    graph.add_node("intake", intake_node)
    graph.add_node("planner", planner_node)
    graph.add_node("evidence", evidence_node)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "planner")
    graph.add_edge("planner", "evidence")
    graph.add_edge("evidence", END)

    if checkpointer:
        # Attach a checkpointer so graph.stream() doesn't raise ValueError
        graph.checkpointer = MemorySaver()

    return graph.compile()


def run_investigation(incident_path: Path) -> None:
    """Run the minimal investigation graph and display results."""
    # Load and map V0 incident
    try:
        with open(incident_path, "r", encoding="utf-8") as f:
            v0_incident = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: malformed JSON in incident file: {incident_path}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading incident file: {incident_path}: {e}", file=sys.stderr)
        sys.exit(1)

    initial_state: IncidentState = map_v0_json_to_incident_state(v0_incident)

    graph = build_graph(checkpointer=True)

    # Execute the compiled graph with values mode
    # stream() yields the full state dict after each node execution
    final_state = initial_state
    for state in graph.stream(initial_state, {"recursion_limit": 10}, stream_mode="values"):
        final_state = state

    # Display results
    print("\n" + "=" * 60)
    print("INVESTIGATION EXECUTION RESULTS (compiled LangGraph)")
    print("=" * 60 + "\n")

    print(f"\n  incident_id: {state.get('incident_id')}")
    print(f"  status: {state.get('status')}")
    print(f"  iteration: {state.get('iteration')}/{state.get('max_iterations')}")
    rc = state.get("root_cause")
    if rc is not None:
        print(f"  root_cause: status={rc.get('status', 'N/A')}, evidence_id={rc.get('evidence_id', 'N/A')}, confidence={rc.get('confidence', 'N/A')}")
    else:
        print(f"  root_cause: None (RCA not implemented in Stage 2 — required for V1 future versions)")

    print(f"  evidence_count: {len(state.get('evidence', []))}")
    mis = state.get("missing_evidence", [])
    print(f"  missing_evidence: {mis if mis else 'none'}")
    errs = state.get("errors", [])
    print(f"  errors: {errs if errs else 'none'}")
    sh = state.get("selected_hypothesis")
    if sh:
        print(f"  selected_hypothesis: id={sh.get('id', 'N/A')}, claim={sh.get('claim', '')[:50]}")
    else:
        print(f"  selected_hypothesis: None")

    print("\n" + "=" * 60)
    print("NOTE: This is V1 Reactive Incident Commander.")
    print("      RCA (Root Cause Analysis) is not implemented in Stage 2")
    print("      but is required later for V1 future versions.")
    print("      The investigation stops after evidence aggregation.")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Minimal incident investigation CLI (V1 Reactive — LangGraph compiled)"
    )
    parser.add_argument(
        "--incident",
        type=Path,
        default=Path("incidents/INC-001.json"),
        help="Path to incident JSON fixture (default: incidents/INC-001.json)",
    )
    args = parser.parse_args()

    if not args.incident.is_file():
        print(f"Error: incident file not found: {args.incident}", file=sys.stderr)
        sys.exit(1)

    run_investigation(args.incident)