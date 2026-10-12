from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "logs"


def search_logs(
    service_name: str,
    keyword: str,
) -> dict:

    log_file = LOG_DIR / f"{service_name}.log"

    if not log_file.exists():
        return {
            "service": service_name,
            "keyword": keyword,
            "matches": [],
            "count": 0,
            "error": "log file not found",
        }

    matches = []

    with log_file.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line_number, line in enumerate(
            file,
            start=1,
        ):

            if keyword.lower() in line.lower():

                matches.append(
                    {
                        "line": line_number,
                        "message": line.strip(),
                    }
                )

    return {
        "service": service_name,
        "keyword": keyword,
        "matches": matches,
        "count": len(matches),
    }


if __name__ == "__main__":

    result = search_logs(
        service_name="orders",
        keyword="CATALOG_REQUEST_FAILED",
    )

    print(result)