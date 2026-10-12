import httpx


SERVICES = {
    "orders": "http://127.0.0.1:8001",
}


def get_metrics(service_name: str) -> dict:
    url = SERVICES[service_name] + "/metrics"

    try:
        response = httpx.get(url, timeout=2)
        response.raise_for_status()

        return {
            "service": service_name,
            "available": True,
            "status_code": response.status_code,
            "metrics": response.json(),
        }

    except httpx.HTTPStatusError as error:
        return {
            "service": service_name,
            "available": False,
            "status_code": error.response.status_code,
            "metrics": None,
            "error": str(error),
        }

    except httpx.RequestError as error:
        return {
            "service": service_name,
            "available": False,
            "status_code": None,
            "metrics": None,
            "error": str(error),
        }


if __name__ == "__main__":
    print(get_metrics("orders"))