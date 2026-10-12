from services.tools.health import get_service_health
from services.tools.logs import search_logs
from services.tools.commits import get_recent_commits
from services.tools.metrices import get_metrics


def get_orders_metrics():
    """Keep the existing incident-evidence response shape for V0 consumers."""
    result = get_metrics("orders")
    evidence = {
        "available": result["available"],
        "metrics": result["metrics"],
    }
    if "error" in result:
        evidence["error"] = result["error"]
    return evidence


def collect_incident_evidence(
    incident_id: str,
) -> dict:

    return {
        "incident_id": incident_id,

        "health": {
            "gateway": get_service_health("gateway"),
            "orders": get_service_health("orders"),
            "catalog": get_service_health("catalog"),
        },

        "logs": {
            "orders_catalog_failures": search_logs(
                service_name="orders",
                keyword="CATALOG_REQUEST_FAILED",
            ),
        },

        "metrics": {
            "orders": get_orders_metrics(),
        },

        "recent_commits": get_recent_commits(
            limit=5
        ),
    }