"""
Tests for the restocking recommendation and order endpoints.
"""
import pytest


@pytest.fixture(autouse=True)
def reset_restock_orders():
    """Snapshot/restore restock_orders so POST tests don't leak state across the run."""
    from mock_data import restock_orders
    snapshot = list(restock_orders)
    yield
    restock_orders.clear()
    restock_orders.extend(snapshot)


class TestRestockRecommendationsEndpoint:
    """Test suite for GET /api/restocking/recommendations."""

    def test_get_recommendations_basic(self, client):
        """Test getting recommendations returns the expected response shape."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        assert response.status_code == 200

        data = response.json()
        assert "recommendations" in data
        assert "budget" in data
        assert "total_cost" in data
        assert "remaining_budget" in data
        assert "max_addressable_cost" in data
        assert "candidate_count" in data
        assert isinstance(data["recommendations"], list)
        assert data["candidate_count"] > 0
        assert len(data["recommendations"]) > 0

        item = data["recommendations"][0]
        for field in [
            "sku", "item_name", "category", "warehouse", "quantity_on_hand",
            "reorder_point", "forecasted_demand", "trend", "unit_cost",
            "shortfall", "recommended_quantity", "is_partial", "urgency",
            "value_density", "line_cost",
        ]:
            assert field in item, f"Missing field {field}"

    def test_recommendations_respect_budget(self, client):
        """Test that total_cost never exceeds the given budget."""
        for budget in [500, 2000, 10000, 30000]:
            response = client.get(f"/api/restocking/recommendations?budget={budget}")
            data = response.json()
            assert data["total_cost"] <= budget + 1e-6

    def test_recommendations_sorted_by_value_density_desc(self, client):
        """Test that recommendations are sorted by value_density descending."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        data = response.json()

        densities = [item["value_density"] for item in data["recommendations"]]
        assert densities == sorted(densities, reverse=True)

    def test_zero_budget_returns_no_recommendations(self, client):
        """Test that a budget of 0 yields no recommendations but still reports candidates."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["recommendations"] == []
        assert data["total_cost"] == 0
        assert data["candidate_count"] > 0

    def test_negative_budget_rejected(self, client):
        """Test that a negative budget is rejected."""
        response = client.get("/api/restocking/recommendations?budget=-10")
        assert response.status_code == 400

    def test_recommendations_filtered_by_warehouse(self, client):
        """Test that all recommendations match the requested warehouse."""
        response = client.get("/api/restocking/recommendations?budget=50000&warehouse=London")
        data = response.json()

        assert len(data["recommendations"]) > 0
        for item in data["recommendations"]:
            assert item["warehouse"] == "London"

    def test_recommendations_filtered_by_category(self, client):
        """Test that all recommendations match the requested category."""
        response = client.get("/api/restocking/recommendations?budget=50000&category=Power Supplies")
        data = response.json()

        assert len(data["recommendations"]) > 0
        for item in data["recommendations"]:
            assert item["category"] == "Power Supplies"

    def test_no_candidates_for_narrow_scope(self, client):
        """Test a warehouse/category combination with no understocked items."""
        response = client.get(
            "/api/restocking/recommendations?budget=50000&warehouse=Tokyo&category=Circuit Boards"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["candidate_count"] == 0
        assert data["recommendations"] == []
        assert data["max_addressable_cost"] == 0

    def test_max_addressable_cost_is_budget_independent(self, client):
        """Test that max_addressable_cost and candidate_count don't change with budget."""
        low = client.get("/api/restocking/recommendations?budget=0").json()
        high = client.get("/api/restocking/recommendations?budget=999999").json()

        assert low["max_addressable_cost"] == high["max_addressable_cost"]
        assert low["candidate_count"] == high["candidate_count"]
        assert low["max_addressable_cost"] > 0

    def test_shortfall_zero_items_excluded(self, client):
        """Test that no returned candidate has quantity fully covering both demand and reorder point."""
        response = client.get("/api/restocking/recommendations?budget=999999")
        data = response.json()

        for item in data["recommendations"]:
            assert item["shortfall"] > 0
            assert (
                item["quantity_on_hand"] < item["forecasted_demand"]
                or item["quantity_on_hand"] < item["reorder_point"]
            )

    def test_partial_item_is_flagged(self, client):
        """Test that a budget landing mid-item produces exactly one partial-fill item."""
        full = client.get("/api/restocking/recommendations?budget=999999").json()
        candidates = full["recommendations"]
        assert len(candidates) >= 2

        # Budget that covers the first item fully but not the second
        first_cost = candidates[0]["line_cost"]
        second_cost = candidates[1]["line_cost"]
        budget = first_cost + (second_cost / 2)

        response = client.get(f"/api/restocking/recommendations?budget={budget}")
        data = response.json()

        partial_items = [item for item in data["recommendations"] if item["is_partial"]]
        assert len(partial_items) == 1
        assert partial_items[0]["recommended_quantity"] < partial_items[0]["shortfall"]
        assert partial_items[0]["recommended_quantity"] > 0


class TestRestockOrdersEndpoint:
    """Test suite for POST/GET /api/restocking/orders."""

    def test_create_restock_order_success(self, client):
        """Test placing a restock order with a large budget."""
        response = client.post("/api/restocking/orders", json={"budget": 50000})
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"].startswith("RSO-")
        assert len(order["items"]) > 0
        assert order["status"] == "Submitted"
        assert order["lead_time_days"] in {10, 14, 16, 18, 21}
        assert order["total_cost"] > 0
        assert order["total_cost"] <= order["budget"]

        for item in order["items"]:
            for field in ["sku", "name", "category", "quantity", "unit_cost", "line_total"]:
                assert field in item

    def test_create_restock_order_zero_budget_rejected(self, client):
        """Test that a zero budget order is rejected."""
        response = client.post("/api/restocking/orders", json={"budget": 0})
        assert response.status_code == 400

    def test_create_restock_order_no_candidates_rejected(self, client):
        """Test that an order with no eligible candidates is rejected."""
        response = client.post(
            "/api/restocking/orders",
            json={"budget": 50000, "warehouse": "Tokyo", "category": "Circuit Boards"},
        )
        assert response.status_code == 400

    def test_lead_time_is_max_of_involved_categories(self, client):
        """Test that a multi-category order's lead time is the max across its items' categories."""
        lead_time_by_category = {
            "Circuit Boards": 21,
            "Sensors": 14,
            "Actuators": 18,
            "Controllers": 16,
            "Power Supplies": 10,
        }

        response = client.post("/api/restocking/orders", json={"budget": 50000})
        order = response.json()

        categories = {item["category"] for item in order["items"]}
        expected_lead_time = max(lead_time_by_category.get(c, 14) for c in categories)
        assert order["lead_time_days"] == expected_lead_time

    def test_get_restock_orders_lists_created_order(self, client):
        """Test that a created order shows up in the GET listing."""
        create_response = client.post("/api/restocking/orders", json={"budget": 50000})
        created_order_number = create_response.json()["order_number"]

        list_response = client.get("/api/restocking/orders")
        assert list_response.status_code == 200

        order_numbers = [o["order_number"] for o in list_response.json()]
        assert created_order_number in order_numbers

    def test_get_restock_orders_not_filterable(self, client):
        """Test that GET /api/restocking/orders ignores warehouse/category query params."""
        client.post("/api/restocking/orders", json={"budget": 50000})

        unfiltered = client.get("/api/restocking/orders").json()
        with_params = client.get(
            "/api/restocking/orders?warehouse=Tokyo&category=Circuit Boards"
        ).json()

        assert len(unfiltered) == len(with_params)
