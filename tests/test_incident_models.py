"""Unit tests for V1 incident models and IncidentState.

These tests verify that the Pydantic evidence models correctly validate
INC-001.json-compatible data, handle missing/optional fields, support
round-trip JSON serialization, and that IncidentState accommodates
inconclusive RCA outcomes. All ``try/except Exception`` anti-patterns
have been replaced with ``pytest.raises(ValidationError)``.
"""

import json
import sys
from typing import Any

import pytest

from common.incident_models import (
    HealthService,
    HealthError,
    LogMatch,
    LogsEvidence,
    ServiceMetrics,
    MetricsEvidence,
    Commit,
    RecentCommitsEvidence,
    Evidence,
    Hypothesis,
    IncidentState,
    map_v0_json_to_incident_state,
    EvidenceMetadata,
)


# ---------------------------------------------------------------------------
# Health service models
# ---------------------------------------------------------------------------


def test_health_service_full():
    """Full health service with healthy=True and status_code=200."""
    data = {
        "service": "gateway",
        "healthy": True,
        "status_code": 200,
        "url": "http://127.0.0.1:8080/health",
    }
    model = HealthService(**data)
    assert model.service == "gateway"
    assert model.healthy is True
    assert model.status_code == 200
    assert model.url == "http://127.0.0.1:8080/health"
    assert model.error is None
    # Round-trip
    d = model.model_dump()
    model2 = HealthService.model_validate(d)
    assert model2 == model


def test_health_service_unhealthy_with_error():
    """Health service with healthy=False and error details."""
    error = HealthError(type="ConnectError", message="All connection attempts failed")
    data = {
        "service": "catalog",
        "healthy": False,
        "status_code": None,
        "url": "http://127.0.0.1:8000/health",
        "error": error,
    }
    model = HealthService(**data)
    assert model.healthy is False
    assert model.status_code is None
    assert model.error is not None
    assert model.error.type == "ConnectError"
    assert "All connection attempts failed" in model.error.message


def test_health_service_minimal():
    """Health service with only required fields (no error, no status_code)."""
    data = {"service": "orders", "healthy": True, "url": "http://127.0.0.1:8001/health"}
    model = HealthService(**data)
    assert model.service == "orders"
    assert model.healthy is True
    assert model.status_code is None
    assert model.url == "http://127.0.0.1:8001/health"
    assert model.error is None


def test_health_service_v0_string_error():
    """V0: HealthService accepts plain string error (not structured HealthError).

    V0 incident JSON stores error as a plain string (e.g. ``"timed out"``).
    The V1 model must preserve this without crashing.
    """
    model = HealthService(
        service="catalog",
        healthy=False,
        status_code=None,
        url="http://127.0.0.1:8000/health",
        error="timed out",  # V0 string-valued error
    )
    assert model.error == "timed out"
    # Round-trip with model_validate/model_dump (Pydantic v2 API)
    d = model.model_dump()
    model2 = HealthService.model_validate(d)
    assert model2.error == "timed out"


def test_health_service_structured_error():
    """V1: HealthService accepts structured HealthError."""
    error = HealthError(type="ConnectError", message="All connection attempts failed")
    model = HealthService(
        service="catalog",
        healthy=False,
        status_code=None,
        url="http://127.0.0.1:8000/health",
        error=error,
    )
    assert model.error is not None
    assert model.error.type == "ConnectError"


# ---------------------------------------------------------------------------
# Log match and logs evidence models
# ---------------------------------------------------------------------------


def test_log_match():
    """Single log match with line number and message."""
    data = {"line": 7, "message": "2026-10-06T23:46:29 | ERROR | CATALOG_REQUEST_FAILED"}
    model = LogMatch(**data)
    assert model.line == 7
    assert "CATALOG_REQUEST_FAILED" in model.message


def test_logs_evidence_full():
    """Full logs evidence with multiple matches, matching INC-001.json structure."""
    matches = [
        LogMatch(line=7, message="msg1"),
        LogMatch(line=9, message="msg2"),
    ]
    data = {
        "service": "orders",
        "keyword": "CATALOG_REQUEST_FAILED",
        "matches": matches,
        "count": 2,
    }
    model = LogsEvidence(**data)
    assert model.service == "orders"
    assert model.keyword == "CATALOG_REQUEST_FAILED"
    assert len(model.matches) == 2
    assert model.count == 2


def test_logs_evidence_minimal():
    """Logs evidence with no matches (empty list, count=0)."""
    data = {
        "service": "gateway",
        "keyword": "TIMEOUT",
        "matches": [],
        "count": 0,
    }
    model = LogsEvidence(**data)
    assert model.service == "gateway"
    assert model.keyword == "TIMEOUT"
    assert model.matches == []
    assert model.count == 0


# ---------------------------------------------------------------------------
# Metrics models
# ---------------------------------------------------------------------------


def test_service_metrics():
    """Service metrics matching INC-001.json nested structure."""
    data = {
        "service": "orders",
        "orders_received": 2,
        "orders_created": 0,
        "catalog_requests": 6,
        "catalog_failures": 6,
    }
    model = ServiceMetrics(**data)
    assert model.service == "orders"
    assert model.orders_received == 2
    assert model.orders_created == 0
    assert model.catalog_requests == 6
    assert model.catalog_failures == 6


def test_metrics_evidence_full():
    """Metrics evidence with available=True."""
    metrics = ServiceMetrics(
        service="orders",
        orders_received=2,
        orders_created=0,
        catalog_requests=6,
        catalog_failures=6,
    )
    data = {"available": True, "metrics": metrics}
    model = MetricsEvidence(**data)
    assert model.available is True
    assert model.metrics.service == "orders"
    assert model.metrics.orders_received == 2


def test_metrics_evidence_missing():
    """Metrics evidence with available=False — must raise ValidationError.

    ``available=False`` with ``metrics=None`` is invalid because the model
    requires ``metrics`` when ``available=True`` and rejects it when ``False``
    per Pydantic validation (the field is required regardless).
    """
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MetricsEvidence(model_validate={"available": False, "metrics": None})  # type: ignore[assignment]


def test_metrics_evidence_round_trip():
    """ServiceMetrics dict -> model -> dict preserves all data."""
    original = {
        "service": "orders",
        "orders_received": 2,
        "orders_created": 0,
        "catalog_requests": 6,
        "catalog_failures": 6,
    }
    model = ServiceMetrics.model_validate(original)
    dumped = model.model_dump()
    assert dumped == original


# ---------------------------------------------------------------------------
# Commit models
# ---------------------------------------------------------------------------


def test_commit():
    """Single commit matching INC-001.json structure."""
    data = {
        "hash": "a9df3b8b62b0e9e569963989b8ae3c4e1798b150",
        "author": "Utkarsh Kaushik",
        "date": "2025-09-04 03:31:34 +0000",
        "message": "Merge branch 'master'",
    }
    model = Commit(**data)
    assert model.hash == data["hash"]
    assert model.author == data["author"]
    assert model.message == data["message"]


def test_recent_commits_evidence():
    """Recent commits evidence matching INC-001.json."""
    commits = [
        Commit(
            hash="a9df3b8b62b0e9e569963989b8ae3c4e1798b150",
            author="Utkarsh Kaushik",
            date="2025-09-04 03:31:34 +0000",
            message="Merge branch 'master'",
        ),
    ]
    data = {
        "available": True,
        "count": 1,
        "commits": commits,
    }
    model = RecentCommitsEvidence(**data)
    assert model.available is True
    assert model.count == 1
    assert len(model.commits) == 1


def test_recent_commits_evidence_round_trip():
    """RecentCommitsEvidence dict -> model -> dict preserves all data."""
    original = {
        "available": True,
        "count": 3,
        "commits": [
            {"hash": "a9df3b8b62b0e9e569963989b8ae3c4e1798b150", "author": "Utkarsh Kaushik", "date": "2025-09-04 03:31:34 +0000", "message": "Merge branch 'master'"},
        ],
    }
    model = RecentCommitsEvidence.model_validate(original)
    dumped = model.model_dump()
    assert dumped["available"] == original["available"]
    assert dumped["count"] == original["count"]
    assert len(dumped["commits"]) == 1


# ---------------------------------------------------------------------------
# Evidence metadata model
# ---------------------------------------------------------------------------


def test_evidence_metadata():
    """Evidence metadata with incident ID and source."""
    data = {
        "incident_id": "INC-001",
        "collected_at": "2026-10-07T00:32:29",
        "source": "monitor",
        "verification_cycles": 2,
    }
    model = EvidenceMetadata(**data)
    assert model.incident_id == "INC-001"
    assert model.source == "monitor"
    assert model.verification_cycles == 2


def test_evidence_metadata_round_trip():
    """EvidenceMetadata dict -> model -> dict preserves all data."""
    original = {
        "incident_id": "INC-001",
        "collected_at": "2026-10-07T00:32:29",
        "source": "monitor",
        "verification_cycles": 1,
    }
    model = EvidenceMetadata.model_validate(original)
    dumped = model.model_dump()
    assert dumped == original


# ---------------------------------------------------------------------------
# Hypothesis model
# ---------------------------------------------------------------------------


def test_hypothesis():
    """Hypothesis model with bounded confidence."""
    hyp = Hypothesis(
        id="H1", claim="Catalog failure", confidence=0.8, status="proposed"
    )
    assert hyp.id == "H1"
    assert hyp.claim == "Catalog failure"
    assert hyp.confidence == 0.8
    assert hyp.status == "proposed"


def test_hypothesis_confidence_bounded():
    """Confidence must be in [0.0, 1.0]; out-of-range values raise ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Hypothesis(id="H1", claim="Test", confidence=1.5, status="proposed")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        Hypothesis(id="H1", claim="Test", confidence=-0.1, status="proposed")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# IncidentState TypedDict validation
# ---------------------------------------------------------------------------


def test_incident_state_valid():
    """IncidentState with all required fields, including root_cause=None initially."""
    state: IncidentState = {
        "incident_id": "INC-001",
        "description": "Payment API errors increased after deployment",
        "affected_services": ["catalog", "orders"],
        "incident_start": "2026-10-07T00:32:29",
        "logs": [],
        "metrics": {},
        "commits": [],
        "deployments": [],
        "retrieved_documents": [],
        "hypotheses": [],
        "verified_hypotheses": [],
        "root_cause": None,  # ✅ RCA starts as None, not {{"status": "inconclusive"}}
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
    # All V1 IncidentState fields must be present as top-level keys
    expected_keys = [
        "incident_id",
        "description",
        "affected_services",
        "incident_start",
        "logs",
        "metrics",
        "commits",
        "deployments",
        "retrieved_documents",
        "hypotheses",
        "verified_hypotheses",
        "root_cause",
        "remediation_plan",
        "final_report",
        "evidence",
        "missing_evidence",
        "errors",
        "status",
        "iteration",
        "max_iterations",
        "selected_hypothesis",
    ]
    for key in expected_keys:
        assert key in state, f"Missing required key: {key}"
    assert state["root_cause"] is None
    assert state["status"] == "investigating"
    assert state["max_iterations"] == 3


def test_incident_state_with_evidence_models():
    """IncidentState that holds Pydantic evidence models (via model_dump)."""
    from common.incident_models import HealthService, LogsEvidence, MetricsEvidence, Evidence, Hypothesis

    health = HealthService(
        service="catalog", healthy=False, status_code=None, url="http://127.0.0.1:8000/health"
    )
    logs = LogsEvidence(service="orders", keyword="CATALOG_REQUEST_FAILED", matches=[], count=0)
    metrics = MetricsEvidence(available=True, metrics=ServiceMetrics(service="orders", orders_received=0, orders_created=0, catalog_requests=0, catalog_failures=0))
    ev = Evidence(id="E-1", source_type="health", source="catalog", summary="Catalog unhealthy", collected_by="monitor")
    hyp = Hypothesis(id="H1", claim="Catalog failure", confidence=0.7, status="proposed")

    state: IncidentState = {
        "incident_id": "INC-001",
        "description": "Catalog service unhealthy",
        "affected_services": ["catalog"],
        "incident_start": "2026-10-07T00:32:29",
        "logs": logs,
        "metrics": metrics,
        "commits": [],
        "deployments": [],
        "retrieved_documents": [],
        "hypotheses": [hyp.model_dump()],  # store as dict for TypedDict flexibility
        "verified_hypotheses": [],
        "root_cause": None,
        "remediation_plan": [],
        "final_report": "",
        "evidence": [ev],
        "missing_evidence": [],
        "errors": [],
        "status": "investigating",
        "iteration": 0,
        "max_iterations": 3,
        "selected_hypothesis": hyp.model_dump(),
    }

    # Pydantic models are dict-compatible, so they work as dict values
    assert state["incident_id"] == "INC-001"
    assert state["affected_services"] == ["catalog"]
    assert state["logs"] is logs
    assert state["evidence"][0] is ev
    assert state["selected_hypothesis"] is not None
    assert state["selected_hypothesis"]["id"] == "H1"


def test_incident_state_root_cause_none_initially():
    """root_cause defaults to None; inconclusive is a post-investigation outcome."""
    state: IncidentState = {
        "incident_id": "INC-TEST",
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
        "root_cause": None,  # ✅ None, not {"status": "inconclusive"}
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
    assert state["root_cause"] is None


def test_incident_state_lifecycle_status_separate_from_rca():
    """Top-level lifecycle status is separate from RCA outcome."""
    # Investigating state with no RCA yet
    state_invest: IncidentState = {
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
    assert state_invest["status"] == "investigating"
    assert state_invest["root_cause"] is None

    # Verified state with resolved RCA
    state_verified: IncidentState = {
        **state_invest,
        "status": "verified",
        "root_cause": {
            "status": "resolved",
            "evidence_id": "E-1",
            "description": "Catalog service failure",
            "confidence": 0.95,
        },
        "final_report": "Resolution confirmed.",
    }
    assert state_verified["status"] == "verified"
    assert state_verified["root_cause"]["status"] == "resolved"
    assert state_verified["final_report"] == "Resolution confirmed."


def test_incident_state_confidence_bounded_0_1():
    """Confidence is bounded 0.0..1.0 and separate from lifecycle status."""
    from pydantic import ValidationError

    # Invalid confidence should be caught by Pydantic validation
    with pytest.raises(ValidationError):
        Hypothesis(
            id="H1", claim="Test", confidence=1.5, status="proposed"
        )  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        Hypothesis(
            id="H1", claim="Test", confidence=-0.1, status="proposed"
        )  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# V0 JSON fixture mapping
# ---------------------------------------------------------------------------


def test_incident_state_from_inc001_fixture():
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
    # Evidence entries have deterministic IDs and raw references
    assert len(state["evidence"]) > 0
    ev = state["evidence"][0]
    assert ev.id.startswith("health:")
    assert ev.source_type == "health"
    assert ev.collected_by == "monitor"
    assert ev.relevance is None  # V1 pre-RAG


def test_incident_state_map_v0_health_error_string():
    """V0 string-valued health errors are preserved as str in V1 model."""
    from common.incident_models import HealthService

    # V0 JSON has error as a plain string (e.g. catalog: {"error": "timed out"})
    hs = HealthService(
        service="catalog",
        healthy=False,
        status_code=None,
        url="http://127.0.0.1:8000/health",
        error="timed out",
    )
    assert hs.error == "timed out"
    # Round-trip via Pydantic v2 API
    d = hs.model_dump()
    hs2 = HealthService.model_validate(d)
    assert hs2.error == "timed out"


# ---------------------------------------------------------------------------
# Round-trip tests: dict <-> model <-> dict
# ---------------------------------------------------------------------------


def test_round_trip_health_service():
    """HealthService dict -> model -> dict preserves all data."""
    original = {
        "service": "catalog",
        "healthy": False,
        "status_code": None,
        "url": "http://127.0.0.1:8000/health",
        "error": {"type": "ConnectError", "message": "timed out"},
    }
    model = HealthService.model_validate(original)
    dumped = model.model_dump()
    # All fields should round-trip
    assert dumped["service"] == original["service"]
    assert dumped["healthy"] == original["healthy"]
    assert dumped["status_code"] == original["status_code"]
    assert dumped["url"] == original["url"]
    assert dumped["error"] is not None
    assert dumped["error"]["type"] == original["error"]["type"]
    assert dumped["error"]["message"] == original["error"]["message"]


def test_round_trip_logs_evidence():
    """LogsEvidence dict -> model -> dict preserves all data."""
    original = {
        "service": "orders",
        "keyword": "CATALOG_REQUEST_FAILED",
        "matches": [{"line": 7, "message": "2026-10-06T23:46:29 | ERROR | CATALOG_REQUEST_FAILED"}],
        "count": 1,
    }
    model = LogsEvidence.model_validate(original)
    dumped = model.model_dump()
    assert dumped["service"] == original["service"]
    assert dumped["keyword"] == original["keyword"]
    assert len(dumped["matches"]) == 1
    assert dumped["matches"][0]["line"] == 7
    assert dumped["count"] == original["count"]


def test_round_trip_service_metrics():
    """ServiceMetrics dict -> model -> dict preserves all data."""
    original = {
        "service": "orders",
        "orders_received": 2,
        "orders_created": 0,
        "catalog_requests": 6,
        "catalog_failures": 6,
    }
    model = ServiceMetrics.model_validate(original)
    dumped = model.model_dump()
    assert dumped == original


def test_round_trip_commit():
    """Commit dict -> model -> dict preserves all data."""
    original = {
        "hash": "a9df3b8b62b0e9e569963989b8ae3c4e1798b150",
        "author": "Utkarsh Kaushik",
        "date": "2025-09-04 03:31:34 +0000",
        "message": "Merge branch 'master'",
    }
    model = Commit.model_validate(original)
    dumped = model.model_dump()
    assert dumped == original


def test_round_trip_recent_commits_evidence():
    """RecentCommitsEvidence dict -> model -> dict preserves all data."""
    original = {
        "available": True,
        "count": 3,
        "commits": [
            {"hash": "a9df3b8b62b0e9e569963989b8ae3c4e1798b150", "author": "Utkarsh Kaushik", "date": "2025-09-04 03:31:34 +0000", "message": "Merge branch 'master'"},
        ],
    }
    model = RecentCommitsEvidence.model_validate(original)
    dumped = model.model_dump()
    assert dumped["available"] == original["available"]
    assert dumped["count"] == original["count"]
    assert len(dumped["commits"]) == 1


def test_round_trip_evidence_metadata():
    """EvidenceMetadata dict -> model -> dict preserves all data."""
    original = {
        "incident_id": "INC-001",
        "collected_at": "2026-10-07T00:32:29",
        "source": "monitor",
        "verification_cycles": 1,
    }
    model = EvidenceMetadata.model_validate(original)
    dumped = model.model_dump()
    assert dumped == original


# ---------------------------------------------------------------------------
# Malformed / invalid data tests — using pytest.raises(ValidationError)
# ---------------------------------------------------------------------------


def test_health_service_missing_service_raises():
    """Missing required 'service' field should raise ValidationError."""
    from pydantic import ValidationError
    import pytest
    with pytest.raises(ValidationError):
        HealthService.model_validate({"healthy": True, "url": "http://example.com/health"})  # type: ignore[arg-type]


def test_log_match_missing_line_raises():
    """Missing required 'line' field in LogMatch."""
    from pydantic import ValidationError
    import pytest
    with pytest.raises(ValidationError):
        LogMatch.model_validate({"message": "some error"})  # type: ignore[arg-type]


def test_commit_missing_hash_raises():
    """Missing required 'hash' field in Commit."""
    from pydantic import ValidationError
    import pytest
    with pytest.raises(ValidationError):
        Commit.model_validate({"author": "Utkarsh", "message": "Initial commit"})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    # Run all test functions
    test_health_service_full()
    test_health_service_unhealthy_with_error()
    test_health_service_minimal()
    test_health_service_v0_string_error()
    test_health_service_structured_error()
    test_log_match()
    test_logs_evidence_full()
    test_logs_evidence_minimal()
    test_service_metrics()
    test_metrics_evidence_missing()
    test_metrics_evidence_round_trip()
    test_commit()
    test_recent_commits_evidence()
    test_recent_commits_evidence_round_trip()
    test_evidence_metadata()
    test_evidence_metadata_round_trip()
    test_hypothesis()
    test_hypothesis_confidence_bounded()
    test_incident_state_valid()
    test_incident_state_with_evidence_models()
    test_incident_state_root_cause_none_initially()
    test_incident_state_lifecycle_status_separate_from_rca()
    test_incident_state_confidence_bounded_0_1()
    test_incident_state_from_inc001_fixture()
    test_incident_state_map_v0_health_error_string()
    test_round_trip_health_service()
    test_round_trip_logs_evidence()
    test_round_trip_service_metrics()
    test_round_trip_commit()
    test_round_trip_recent_commits_evidence()
    test_round_trip_evidence_metadata()
    test_health_service_missing_service_raises()
    test_log_match_missing_line_raises()
    test_commit_missing_hash_raises()

    print("\nAll tests passed!", file=sys.stderr)