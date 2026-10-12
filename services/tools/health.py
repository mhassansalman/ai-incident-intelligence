import httpx


SERVICES = {
    "gateway": "http://127.0.0.1:8080",
    "orders": "http://127.0.0.1:8001",
    "catalog": "http://127.0.0.1:8000",
}


def get_service_health(service_name: str):
    url = SERVICES[service_name] + "/health"

    try:
        response = httpx.get(url, timeout=2)

        return {
            "service": service_name,
            "healthy": response.status_code == 200,
            "status_code": response.status_code,
            "url": url,
        }

    except httpx.RequestError as error:
        return {
            "service": service_name,
            "healthy": False,
            "status_code": None,
            "url": url,
            "error": str(error),
        }


if __name__ == "__main__":
    for service in SERVICES:
        print(get_service_health(service))