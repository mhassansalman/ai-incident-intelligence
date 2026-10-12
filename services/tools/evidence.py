import httpx

from services.tools.health import get_service_health
from services.tools.logs import search_logs
from services.tools.commits import get_recent_commits


def get_orders_metrics():
    try:
        response = httpx.get(
            "http://127.0.0.1:8001/metrics",
            timeout=2,
        )

        response.raise_for_status()

        return {
            "available": True,
            "metrics": response.json(),
        }

    except Exception as error:
        return {
            "available": False,
            "metrics": None,
            "error": str(error),
        }


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