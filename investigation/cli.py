""" CLI entry point for minimal incident investigation using compiled LangGraph.

Usage:
    python -m investigation.cli --incident incidents/INC-001.json
    python -m investigation.cli --incident incidents/INC-001.json --live

This compiles a StateGraph (START -> Intake -> Planner -> Evidence -> END)
and invokes it, displaying results. RCA (Root Cause Analysis) is not
implemented in Stage 3 but is required later within V1.
The investigation stops after evidence aggregation.

Mode behaviour:
  - Fixture (default): deterministic evidence from incidents/INC-001.json.
    Always succeeds; no network or service dependencies.
  - Live (--live): attempts V0 collectors (health, logs, commits) when
    local services are running. Each collector independently handles failures;
    unavailable sources produce Evidence with error summaries, never exceptions.
    Metrics are always marked unavailable since no live V0 metrics collector
    exists. Fixture baseline is preserved and overlaid with live where available.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from investigation.state import IncidentState, map_v0_json_to_incident_state
from investigation.nodes import intake_node, planner_node, evidence_node

# Maximum recursion limit for graph execution
GRAPH_RECURSION_LIMIT = 10


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


def run_investigation(incident_path: Path, live: bool = False) -> None:
    """Run the minimal investigation graph and display results.

    Parameters:
        incident_path: Path to incident JSON fixture (default: incidents/INC-001.json).
        live: If True, attempt live V0 collector invocation in addition to
          fixture baseline. If False (default), fixture-only mode is used.
   """
    # Load and map V0 incident (fixture baseline)
    try:
        with open(incident_path, "r", encoding="utf-8") as f:
            v0_incident = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: malformed JSON in incident file: {incident_path}: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: incident file not found: {incident_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading incident file: {incident_path}: {e}", file=sys.stderr)
        sys.exit(1)

    initial_state: IncidentState = map_v0_json_to_incident_state(v0_incident)

    # Override evidence mode if --live was specified
    if live:
        initial_state["evidence_mode"] = "live"

    graph = build_graph(checkpointer=True)

    # Execute the compiled graph with values mode
    # stream() yields the full state dict after each node execution
    final_state = initial_state
    for state in graph.stream(initial_state, {"recursion_limit": GRAPH_RECURSION_LIMIT}, stream_mode="values"):
        final_state = state

    # Display results
    print("\n" + "=" * 60)
    print("INVESTIGATION EXECUTION RESULTS (compiled LangGraph)")
    print("=" * 60 + "\n")

    mode = final_state.get("evidence_mode", "fixture")
    print(f"  evidence_mode: {mode}")

    print(f"\n  incident_id: {final_state.get('incident_id')}")
    print(f"  status: {final_state.get('status')}")
    print(f"  iteration: {final_state.get('iteration')}/{final_state.get('max_iterations')}")
    rc = final_state.get("root_cause")
    if rc is not None:
        print(f"  root_cause: status={rc.get('status', 'N/A')}, evidence_id={rc.get('evidence_id', 'N/A')}, confidence={rc.get('confidence', 'N/A')}")
    else:
        print(f"  root_cause: None (RCA not implemented in Stage 3 but required later within V1)")

    evidence = final_state.get("evidence", [])
    print(f"  evidence_count: {len(evidence)}")
    for ev in evidence:
        src = ev.collected_by if hasattr(ev, 'collected_by') else "unknown"
        print(f"    - [{src}] {ev.source_type}:{ev.id} - {ev.summary[:80]}")

    mis = final_state.get("missing_evidence", [])
    print(f"  missing_evidence: {mis if mis else 'none'}")

    errs = final_state.get("errors", [])
    print(f"  errors: {errs if errs else 'none'}")

    sh = final_state.get("selected_hypothesis")
    if sh:
        print(f"  selected_hypothesis: id={sh.get('id', 'N/A')}, claim={sh.get('claim', '')[:50]}")
    else:
        print(f"  selected_hypothesis: None")

    print("\n" + "=" * 60)
    print("NOTE: This is V1 Reactive Incident Commander — Stage 3.")
    print("      RCA (Root Cause Analysis) is not implemented in Stage 3")
    print("      but is required later within V1.")
    print("      The investigation stops after evidence aggregation.")
    print("      Fixture mode: deterministic, always available.")
    if mode == "live":
        print("      Live mode: V0 collectors invoked; unavailable sources marked, never fabricated.")
    print("      The investigation stops after evidence aggregation.")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Minimal incident investigation CLI (V1 Reactive — LangGraph compiled, Stage 3)"
    )
    parser.add_argument(
        "--incident",
        type=Path,
        default=Path("incidents/INC-001.json"),
        help="Path to incident JSON fixture (default: incidents/INC-001.json)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Attempt live V0 collector invocation (health, logs, commits) "
             "in addition to fixture baseline. Services are assumed to run "
             "on default ports (gateway:8080, orders:8001, catalog:8000).",
    )
    args = parser.parse_args()

    if not args.incident.is_file():
        print(f"Error: incident file not found: {args.incident}", file=sys.stderr)
        sys.exit(1)

    run_investigation(args.incident, live=args.live)


if __name__ == "__main__":
    main()