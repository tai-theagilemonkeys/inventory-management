"""
Tests for the purchase order endpoints.
"""
import pytest


@pytest.fixture(autouse=True)
def reset_purchase_orders():
    """Snapshot/restore purchase_orders so POST tests don't leak state across the run."""
    from mock_data import purchase_orders
    snapshot = list(purchase_orders)
    yield
    purchase_orders.clear()
    purchase_orders.extend(snapshot)


class TestCreatePurchaseOrderEndpoint:
    """Test suite for POST /api/purchase-orders."""

    def test_create_purchase_order_success(self, client):
        """Test creating a purchase order for a real backlog item."""
        response = client.post("/api/purchase-orders", json={
            "backlog_item_id": "1",
            "supplier_name": "Acme Filters Co.",
            "quantity": 500,
            "unit_cost": 12.5,
            "expected_delivery_date": "2025-11-01",
            "notes": "Rush order"
        })
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["backlog_item_id"] == "1"
        assert data["supplier_name"] == "Acme Filters Co."
        assert data["quantity"] == 500
        assert data["unit_cost"] == 12.5
        assert data["expected_delivery_date"] == "2025-11-01"
        assert data["notes"] == "Rush order"
        assert "status" in data
        assert "created_date" in data

    def test_create_purchase_order_without_notes(self, client):
        """Test creating a purchase order without the optional notes field."""
        response = client.post("/api/purchase-orders", json={
            "backlog_item_id": "2",
            "supplier_name": "Motor Supply Inc.",
            "quantity": 20,
            "unit_cost": 250.0,
            "expected_delivery_date": "2025-11-10"
        })
        assert response.status_code == 201
        assert response.json()["notes"] is None

    def test_create_purchase_order_missing_required_field(self, client):
        """Test that missing required fields are rejected."""
        response = client.post("/api/purchase-orders", json={
            "backlog_item_id": "1",
            "supplier_name": "Acme Filters Co.",
        })
        assert response.status_code == 422


class TestGetPurchaseOrderByBacklogItemEndpoint:
    """Test suite for GET /api/purchase-orders/{backlog_item_id}."""

    def test_get_purchase_order_by_backlog_item(self, client):
        """Test fetching a purchase order by its backlog item id."""
        create_response = client.post("/api/purchase-orders", json={
            "backlog_item_id": "3",
            "supplier_name": "Valve Works",
            "quantity": 80,
            "unit_cost": 156.0,
            "expected_delivery_date": "2025-11-05"
        })
        created = create_response.json()

        response = client.get("/api/purchase-orders/3")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == created["id"]
        assert data["backlog_item_id"] == "3"

    def test_get_purchase_order_by_backlog_item_not_found(self, client):
        """Test fetching a purchase order for a backlog item with no PO."""
        response = client.get("/api/purchase-orders/nonexistent-backlog-item")
        assert response.status_code == 404


class TestBacklogPurchaseOrderIntegration:
    """Test suite verifying /api/backlog exposes purchase_order_id consistently."""

    def test_backlog_items_without_po_have_null_purchase_order_id(self, client):
        """Test that backlog items without a purchase order report purchase_order_id as null."""
        response = client.get("/api/backlog")
        data = response.json()

        for item in data:
            assert "purchase_order_id" in item
            assert item["purchase_order_id"] is None
            assert item["has_purchase_order"] is False

    def test_backlog_reflects_created_purchase_order_id(self, client):
        """Test that creating a PO makes the backlog item report the new purchase_order_id."""
        create_response = client.post("/api/purchase-orders", json={
            "backlog_item_id": "4",
            "supplier_name": "Widget World",
            "quantity": 200,
            "unit_cost": 30.0,
            "expected_delivery_date": "2025-11-15"
        })
        created_po = create_response.json()

        response = client.get("/api/backlog")
        data = response.json()

        item = next(i for i in data if i["id"] == "4")
        assert item["has_purchase_order"] is True
        assert item["purchase_order_id"] == created_po["id"]
