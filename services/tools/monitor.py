import json
import time
from datetime import datetime
from pathlib import Path

from services.tools.health import get_service_health
from services.tools.evidence import collect_incident_evidence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INCIDENT_DIR = PROJECT_ROOT / "incidents"
INCIDENT_DIR.mkdir(parents=True, exist_ok=True)

CHECK_INTERVAL = 5


def next_incident_id() -> str:
    existing = list(INCIDENT_DIR.glob("INC-*.json"))

    numbers = []

    for path in existing:
        try:
            numbers.append(
                int(path.stem.split("-")[1])
            )
        except (IndexError, ValueError):
            pass

    next_number = max(numbers, default=0) + 1

    return f"INC-{next_number:03d}"


def create_incident() -> str:
    incident_id = next_incident_id()

    evidence = collect_incident_evidence(
        incident_id
    )

    incident = {
        "incident_id": incident_id,
        "created_at": datetime.now().isoformat(
            timespec="seconds"
        ),
        "trigger": {
            "service": "catalog",
            "reason": "health check failed",
        },
        "evidence": evidence,
    }

    path = INCIDENT_DIR / f"{incident_id}.json"

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            incident,
            file,
            indent=2,
        )

    print(
        f"[INCIDENT CREATED] {incident_id}"
    )

    return incident_id


def monitor():
    incident_open = False

    print("Incident monitor started...")

    while True:
        health = get_service_health(
            "catalog"
        )

        if health["healthy"]:
            print("Catalog ✅")

            if incident_open:
                print("Catalog recovered ✅")
                incident_open = False

        else:
            print("Catalog ❌")

            if not incident_open:
                create_incident()
                incident_open = True

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor()