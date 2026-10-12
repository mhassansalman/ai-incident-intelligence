import os
import httpx
import pytest

BASE = os.getenv("TEST_GATEWAY_URL", "http://127.0.0.1:8080")

async def _get(client, path):
    r = await client.get(f"{BASE}{path}")
    r.raise_for_status()
    return r.json()

async def _post(client, path, json):
    r = await client.post(f"{BASE}{path}", json=json)
    r.raise_for_status()
    return r.json()

@pytest.mark.asyncio
async def test_order_flow():
    async with httpx.AsyncClient(timeout=3.0) as client:
        items = await _get(client, "/api/items")
        assert items, "catalog should have seed items"
        order = await _post(client, "/api/orders", {"item_id": items[0]["id"], "qty": 2})
        assert order["total"]
