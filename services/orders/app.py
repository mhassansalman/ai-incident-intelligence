from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException

from common.schemas import Order, OrderCreate, Health, Item
from .models import store


# =========================================================
# Configuration
# =========================================================

SERVICE = "orders"
VERSION = os.getenv("APP_VERSION", "0.1.0")

CATALOG_URL = os.getenv(
    "CATALOG_URL",
    "http://catalog:8000",
)

HTTP_TIMEOUT = float(
    os.getenv("HTTP_TIMEOUT", "2.5")
)

RETRY_ATTEMPTS = int(
    os.getenv("RETRY_ATTEMPTS", "2")
)


# =========================================================
# Local Metrics
# =========================================================

METRICS = {
    "orders_received": 0,
    "orders_created": 0,
    "catalog_requests": 0,
    "catalog_failures": 0,
}


# =========================================================
# Evidence Log
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "orders.log"

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def write_log(
    level: str,
    event: str,
    **data,
) -> None:

    timestamp = datetime.now().isoformat(
        timespec="seconds"
    )

    details = " ".join(
        f"{key}={value}"
        for key, value in data.items()
    )

    line = f"{timestamp} | {level} | {event}"

    if details:
        line += f" | {details}"

    with LOG_FILE.open(
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            line + "\n"
        )


# =========================================================
# FastAPI
# =========================================================

app = FastAPI(
    title="Orders Service"
)


# =========================================================
# Health
# =========================================================

@app.get(
    "/health",
    response_model=Health,
)
async def health() -> Health:

    return Health(
        service=SERVICE,
        version=VERSION,
    )


# =========================================================
# Metrics
# =========================================================

@app.get("/metrics")
async def metrics():

    return {
        "service": SERVICE,
        **METRICS,
    }


# =========================================================
# Catalog Dependency
# =========================================================

async def get_item_safe(
    item_id: int,
) -> Item:

    last_exc: Exception | None = None

    for attempt in range(
        RETRY_ATTEMPTS + 1
    ):

        try:

            METRICS["catalog_requests"] += 1

            write_log(
                "INFO",
                "CATALOG_REQUEST_STARTED",
                item_id=item_id,
                attempt=attempt + 1,
            )

            async with httpx.AsyncClient(
                timeout=HTTP_TIMEOUT
            ) as client:

                response = await client.get(
                    f"{CATALOG_URL}/items/{item_id}"
                )

            if response.status_code == 404:

                raise HTTPException(
                    status_code=404,
                    detail="Item not found in catalog",
                )

            response.raise_for_status()

            write_log(
                "INFO",
                "CATALOG_REQUEST_SUCCESS",
                item_id=item_id,
                attempt=attempt + 1,
                status_code=response.status_code,
            )

            return Item(
                **response.json()
            )

        except Exception as exc:

            last_exc = exc

            METRICS["catalog_failures"] += 1

            write_log(
                "ERROR",
                "CATALOG_REQUEST_FAILED",
                item_id=item_id,
                attempt=attempt + 1,
                error=repr(exc),
            )

    write_log(
        "ERROR",
        "CATALOG_LOOKUP_EXHAUSTED",
        item_id=item_id,
        error=repr(last_exc),
    )

    raise HTTPException(
        status_code=502,
        detail=(
            f"Catalog lookup failed: "
            f"{last_exc}"
        ),
    )


# =========================================================
# Create Order
# =========================================================

@app.post(
    "/orders",
    response_model=Order,
    status_code=201,
)
async def create_order(
    payload: OrderCreate,
) -> Order:

    METRICS["orders_received"] += 1

    write_log(
        "INFO",
        "ORDER_REQUEST_RECEIVED",
        item_id=payload.item_id,
        qty=payload.qty,
    )

    item = await get_item_safe(
        payload.item_id
    )

    order = store.create(
        payload,
        price=Decimal(
            str(item.price)
        ),
    )

    METRICS["orders_created"] += 1

    write_log(
        "INFO",
        "ORDER_CREATED",
        order_id=order.id,
        item_id=order.item_id,
        qty=order.qty,
    )

    return order


# =========================================================
# Get Order
# =========================================================

@app.get(
    "/orders/{order_id}",
    response_model=Order,
)
async def get_order(
    order_id: int,
) -> Order:

    order = store.get(
        order_id
    )

    if not order:

        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    return order