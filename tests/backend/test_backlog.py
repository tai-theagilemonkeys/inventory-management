"""
Tests for the backlog API endpoint: filtering and data-integrity regression coverage.

Backlog items reference an order_id but have no warehouse/category of their own,
so warehouse/category filtering must join through the referenced order -- not
through a backlog-SKU-in-inventory-catalog check, since a backordered item is not
guaranteed to exist in the current inventory master catalog.
"""
import pytest


class TestBacklogDataIntegrity:
    """Regression coverage for the order_id cross-reference bug."""

    def test_backlog_order_ids_reference_real_orders(self, client):
        """Every backlog item's order_id must resolve to a real order."""
        orders_response = client.get("/api/orders")
        order_ids = {o["id"] for o in orders_response.json()}

        backlog_response = client.get("/api/backlog")
        data = backlog_response.json()
        assert len(data) > 0

        for item in data:
            assert item["order_id"] in order_ids, \
                f"Backlog item references unknown order {item['order_id']}"


class TestBacklogFiltering:
    """Test suite for warehouse/category filtering on /api/backlog."""

    def test_get_backlog_unfiltered_returns_all(self, client):
        """No filters should return every backlog item."""
        unfiltered = client.get("/api/backlog").json()
        all_items = client.get("/api/backlog?warehouse=all&category=all").json()
        assert len(unfiltered) == len(all_items)

    def test_get_backlog_by_warehouse(self, client):
        """Filtering by warehouse should only include backlog items whose order is in that warehouse."""
        orders_by_id = {o["id"]: o for o in client.get("/api/orders").json()}

        response = client.get("/api/backlog?warehouse=Tokyo")
        assert response.status_code == 200
        data = response.json()

        for item in data:
            order = orders_by_id[item["order_id"]]
            assert order["warehouse"] == "Tokyo"

    def test_get_backlog_by_category(self, client):
        """Filtering by category should only include backlog items whose order is in that category."""
        orders_by_id = {o["id"]: o for o in client.get("/api/orders").json()}

        response = client.get("/api/backlog?category=Sensors")
        assert response.status_code == 200
        data = response.json()

        for item in data:
            order = orders_by_id[item["order_id"]]
            assert order["category"].lower() == "sensors"

    def test_get_backlog_by_warehouse_and_category(self, client):
        """Combined filters should narrow results without emptying them for a valid combination."""
        response = client.get("/api/backlog?warehouse=San Francisco&category=Actuators")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_backlog_filter_excludes_non_matching(self, client):
        """A filter that matches no backlog item's order should return an empty list, not an error."""
        response = client.get("/api/backlog?warehouse=Nonexistent Warehouse")
        assert response.status_code == 200
        assert response.json() == []
