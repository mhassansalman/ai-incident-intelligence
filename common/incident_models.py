# common/incident_models.py
from __future__ import annotations

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ValidationError
from typing_extensions import Literal, TypedDict


class HealthError(BaseModel):
    """Structured error details when a service health check fails."""
    type: str = Field(..., description="Error type/class")
    message: str = Field(..., description="Human-readable error message")


class HealthService(BaseModel):
    """Health evidence for a single service, matching INC-001.json structure.

    Accepts V0 string-valued ``error`` field via ``Union[str, HealthError]``.
    """
    service: str = Field(..., min_length=1, description="Service name")
    healthy: bool = Field(..., description="Whether the service is healthy")
    status_code: Optional[int] = Field(
        None, description="HTTP status code, None if unhealthy"
    )
    url: str = Field(..., min_length=1, description="Health check URL")
    error: Optional[Union[str, HealthError]] = Field(
        None, description="Error string (V0) or structured HealthError (V1)"
    )


class LogMatch(BaseModel):
    """A single matching log entry."""
    line: int = Field(..., ge=1, description="Line number in the log file")
    message: str = Field(..., description="Log message text")


class LogsEvidence(BaseModel):
    """Logs evidence from searching a service's logs, matching INC-001.json."""
    service: str = Field(..., min_length=1, description="Service name")
    keyword: str = Field(..., min_length=1, description="Keyword/search term used")
    matches: List[LogMatch] = Field(
        default_factory=list, description="Matching log entries"
    )
    count: int = Field(0, ge=0, description="Total match count")


class ServiceMetrics(BaseModel):
    """Metrics for a single service, matching INC-001.json nested structure."""
    service: str = Field(..., min_length=1, description="Service name")
    orders_received: int = Field(0, ge=0, description="Number of orders received")
    orders_created: int = Field(0, ge=0, description="Number of orders created")
    catalog_requests: int = Field(0, ge=0, description="Number of catalog requests")
    catalog_failures: int = Field(0, ge=0, description="Number of catalog failures")


class MetricsEvidence(BaseModel):
    """Metrics evidence from a service, matching INC-001.json.

    Distinguishes ``available=False`` (missing data) from zero metrics.
    """
    available: bool = Field(..., description="Whether metrics are available")
    metrics: ServiceMetrics = Field(..., description="Metric values")


class Commit(BaseModel):
    """A single git commit, matching INC-001.json."""
    hash: str = Field(
        ..., min_length=40, max_length=40, description="Commit hash (40-char hex)"
    )
    author: str = Field(..., min_length=1, description="Commit author")
    date: str = Field(..., description="Commit date/time")
    message: str = Field(..., min_length=1, description="Commit message")


class RecentCommitsEvidence(BaseModel):
    """Recent commits evidence, matching INC-001.json."""
    available: bool = Field(..., description="Whether commits are available")
    count: int = Field(0, ge=0, description="Total commit count")
    commits: List[Commit] = Field(
        default_factory=list, description="Commit entries"
    )


class EvidenceMetadata(BaseModel):
    """Metadata for a collection of evidence."""

    incident_id: str = Field(..., description="Incident identifier")
    collected_at: str = Field(
        ..., description="Timestamp when evidence was collected (ISO format)"
    )
    source: str = Field(
        ..., description="Source of the evidence (e.g., 'monitor', 'manual')"
    )
    verification_cycles: int = Field(
        0, ge=0, description="Number of verification cycles performed"
    )


class Evidence(BaseModel):
    """Evidence entry matching ARCHITECTURE/04_INCIDENT_STATE_AND_EVIDENCE.md.

    V1 sets ``relevance`` to ``null`` (pre-RAG); source metadata preserved
    deterministically from V0 fixture.
    """
    id: str = Field(..., description="Deterministic evidence ID (e.g., 'E-104')")
    source_type: str = Field(
        ..., description="Type of source: 'health' | 'logs' | 'metrics' | 'commits'"
    )
    source: str = Field(..., description="Service or origin (e.g., 'catalog')")
    timestamp: Optional[str] = Field(
        None, description="ISO timestamp from evidence collection"
    )
    summary: str = Field(..., description="Human-readable summary")
    raw_reference: Optional[str] = Field(
        None, description="Deterministic raw reference (e.g., 'health://catalog/...')"
    )
    relevance: Optional[float] = Field(
        None, description="Set to null in V1; computed after RAG baseline"
    )
    collected_by: str = Field(
        ..., description="Who collected: 'fixture' | 'live' | 'monitor' | 'manual'"
    )


class Hypothesis(BaseModel):
    """A competing hypothesis during investigation."""
    id: str = Field(..., description="Unique hypothesis identifier")
    claim: str = Field(..., description="Human-readable claim")
    supporting_evidence_ids: List[str] = Field(
        default_factory=list, description="Evidence IDs supporting this hypothesis"
    )
    contradicting_evidence_ids: List[str] = Field(
        default_factory=list, description="Evidence IDs that contradict this hypothesis"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in this hypothesis (0..1)"
    )
    status: str = Field(
        ...,
        description="Hypothesis status: 'proposed' | 'under_review' | 'supported' | 'rejected'",
    )


class IncidentState(TypedDict):
    """LangGraph state for reactive incident investigation.

    Minimal V1 contract grounded in ARCHITECTURE/04 essential requirements.
    Separates lifecycle ``status`` from RCA ``root_cause``.  ``root_cause``
    starts as ``None``; ``inconclusive`` is a legitimate terminal result after
    investigation whose report must explain missing or conflicting evidence.

    All Pydantic-submodel values are dict-compatible via ``.model_dump()/model_validate()
    for graph edge serialization.
    """

    evidence_mode: Literal["fixture", "live"]
    incident_id: str
    """Unique incident identifier (e.g., 'INC-001')."""

    description: str
    """Free-text description of the incident provided by the user."""

    affected_services: List[str]
    """Services affected by the incident, e.g. ['catalog', 'orders']."""

    incident_start: str
    """ISO timestamp when incident was created (from V0 ``created_at``)."""

    logs: List[Any]
    """
    Log evidence. Holds either a ``LogsEvidence`` instance, a list of raw match dicts,
    or an empty list if no logs are available. Accepts ``Any`` to remain flexible across
    stages of the investigation graph.
    """

    metrics: Dict[str, Any]
    """
    Metrics evidence. Holds either a ``MetricsEvidence`` instance, a nested dict,
    or an empty dict if no metrics are available.
    """

    commits: List[Dict[str, Any]]
    """
    Commit summaries. Each dict typically has ``hash``, ``author``, ``date``, ``message``.
    Empty list when no commits are available.
    """

    deployments: List[Dict[str, Any]]
    """
    Deployment records. Each dict typically has ``version``, ``timestamp``, ``author``.
    Empty list when no deployment history is available.
    """

    retrieved_documents: List[Dict[str, Any]]
    """
    RAG-retrieved documents (runbooks, historical incidents, architecture diagrams).
    Each dict typically has ``source``, ``content``, ``metadata``.
    Empty list when no documents have been retrieved yet.
    """

    hypotheses: List[Dict[str, Any]]
    """
    Competing hypotheses generated during investigation.
    Each dict typically has ``id``, ``description``, ``supporting_evidence``, ``confidence``.
    Empty list before hypothesis generation begins.
    """

    verified_hypotheses: List[Dict[str, Any]]
    """
    Hypotheses that have been verified (or rejected) during the verification phase.
    Each dict typically has ``id``, ``description``, ``verdict`` (``'supported'``/``'rejected'``),
    ``confidence``.
    Empty list before verification begins.
    """

    root_cause: Optional[Dict[str, Any]]
    """
    Root cause determination. ``None`` until the RCA phase completes.

    When present, ``status`` is ``"resolved"`` | ``"inconclusive"`` | ``"contradiction"``.

    Typical shape::

        {
            "status": "resolved" | "inconclusive" | "contradiction",
            "evidence_id": str,       # ID of the supporting evidence entry
            "description": str,       # Human-readable root cause description
            "confidence": float       # 0.0 <= confidence <= 1.0
        }
    """

    remediation_plan: List[Dict[str, Any]]
    """
    Recommended remediation actions, one step per dict.
    Each step typically has ``action``, ``owner``, ``deadline``, ``success_criteria``.
    Empty list before remediation planning begins.
    """

    final_report: str
    """
    Fully-formed incident report text. Empty string ``""`` until the report is generated.
    Populated after the verification and RCA phases complete.

    Must explain ``why`` the outcome is ``inconclusive`` (missing/conflicting evidence)
    rather than fabricating certainty.
    """

    evidence: List[Evidence]
    """
    Structured evidence entries per ARCHITECTURE/04 Evidence model.

    Each entry preserves deterministic source metadata and raw references.
    ``relevance`` is ``null`` in V1 (computed after RAG baseline).
    """

    missing_evidence: List[str]
    """
    Known gaps in evidence collected so far. Used to guide further investigation
    or flag when ``max_iterations`` has been reached.
    """

    errors: List[str]
    """
    Validation errors, tool failures, or data-unavailable messages captured
    during evidence collection. Does not invalidate the state; surfaced for
    the report and RCA reasoning.
    """

    status: str
    """
    Top-level lifecycle status: ``"investigating"`` | ``"verified"`` | ``"closed"``.
    Separate from ``root_cause.status``; tracks overall investigation progress.
    """

    iteration: int
    """
    Current verification cycle count. Starts at 0, incremented each cycle.
    Enforced ``max_iterations`` bound (3 per V1 rule).
    """

    max_iterations: int
    """
    Maximum allowed verification cycles. Default 3; graph stopping behavior
    belongs to Stage 2, but the contract validates the bound.
    """

    selected_hypothesis: Optional[Dict[str, Any]]
    """
    Currently selected hypothesis. ``None`` before hypothesis selection.
    When set, typically corresponds to a ``Hypothesis`` model converted to dict.
    """


def map_v0_json_to_incident_state(v0_json: dict) -> IncidentState:
    """Minimal V0 JSON -> V1 IncidentState mapping for Stage 2 compatibility.

    Does NOT force a full adapter; documents the minimal field mapping.

    Returns an IncidentState dict with mandatory fields populated; optional
    fields are set to ``None`` / empty defaults.

    Key mapping decisions:
    - ``root_cause`` starts as ``None`` (RCA has not begun)
    - ``max_iterations`` defaults to 3 per V1 rule
    - V0 string-valued health errors preserved as ``str`` in ``HealthService.error``
    - ``Evidence`` entries have deterministic ``id``, ``source_type``, ``raw_reference``
    - ``relevance`` is ``null`` in V1 (computed after RAG baseline)
    """
    evidence_list: List[Evidence] = []

    # Health evidence from V0 JSON
    health = v0_json.get("evidence", {}).get("health", {})
    for service_name, service_health in health.items():
        error_val = service_health.get("error")
        if isinstance(error_val, str):
            error_repr = error_val
        elif isinstance(error_val, dict):
            error_repr = error_val.get("message", "") if isinstance(error_val, dict) else str(error_val)
        else:
            error_repr = None

        evidence_list.append(
            Evidence(
                id=f"health:{service_name}",
                source_type="health",
                source=service_name,
                timestamp=v0_json.get("created_at"),
                summary=(
                    f"Service {service_health.get('healthy', False)}"
                    f"{' healthy' if service_health.get('healthy') else f'unhealthy ({error_repr})' if error_repr else ''}"
                ),
                raw_reference=f"health://{service_name}/{v0_json.get('incident_id')}",
                relevance=None,
                collected_by="monitor",
            )
        )

    # Logs evidence from V0 JSON
    for log_key, log_data in v0_json.get("evidence", {}).get("logs", {}).items():
        matches = log_data.get("matches", [])
        match_objs = [
            {"line": m["line"], "message": m["message"]} if isinstance(m, dict) else {"line": 0, "message": str(m)}
            for m in matches
        ]
        evidence_list.append(
            Evidence(
                id=f"logs:{log_key}",
                source_type="logs",
                source=log_data.get("service", "unknown"),
                timestamp=v0_json.get("created_at"),
                summary=f"Found {log_data.get('count', 0)} matches for '{log_data.get('keyword', '')}'",
                raw_reference=f"log://{log_data.get('service', 'unknown')}/{log_data.get('keyword', '')}",
                relevance=None,
                collected_by="monitor",
            )
        )

    # Metrics evidence from V0 JSON
    metrics = v0_json.get("evidence", {}).get("metrics", {})
    for service_name, metrics_data in metrics.items():
        evidence_list.append(
            Evidence(
                id=f"metrics:{service_name}",
                source_type="metrics",
                source=service_name,
                timestamp=v0_json.get("created_at"),
                summary=(
                    f"{service_name}: "
                    f"orders_received={metrics_data.get('metrics', {}).get('orders_received', 0)}, "
                    f"catalog_failures={metrics_data.get('metrics', {}).get('catalog_failures', 0)}"
                ),
                raw_reference=f"metrics://{service_name}/{v0_json.get('incident_id')}",
                relevance=None,
                collected_by="monitor",
            )
        )

    # Commits evidence from V0 JSON
    commits = v0_json.get("evidence", {}).get("recent_commits", {})
    if commits.get("available", False):
        for c in commits.get("commits", [])[:3]:
            evidence_list.append(
                Evidence(
                    id=f"commits:{c.get('hash', '')[:8]}",
                    source_type="commits",
                    source="git",
                    timestamp=v0_json.get("created_at"),
                    summary=c.get("message", ""),
                    raw_reference=f"git://{c.get('hash', '')}",
                    relevance=None,
                    collected_by="monitor",
                )
            )

    return IncidentState(
        incident_id=v0_json.get("incident_id", "INC-UNKNOWN"),
        description=v0_json.get("trigger", {}).get("reason", ""),
        affected_services=list(health.keys()) if "health" in v0_json.get("evidence", {}) else [],
        incident_start=v0_json.get("created_at", ""),
        logs=[],
        metrics={},
        commits=[],
        deployments=[],
        retrieved_documents=[],
        hypotheses=[],
        verified_hypotheses=[],
        root_cause=None,  # RCA starts as None, not inconclusive
        remediation_plan=[],
        final_report="",
        evidence=evidence_list,
        missing_evidence=[],
        errors=[],
        status="investigating",
        iteration=0,
        max_iterations=3,
        selected_hypothesis=None,
        evidence_mode="fixture",
    )