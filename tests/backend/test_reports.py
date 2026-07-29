"""
Tests for reports API endpoints (quarterly and monthly-trends).
"""
import pytest


class TestQuarterlyReportsEndpoint:
    """Test suite for /api/reports/quarterly."""

    def test_get_quarterly_reports_unfiltered(self, client):
        """Test getting quarterly reports with no filters returns all quarters with orders."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        assert "quarter" in first
        assert "total_orders" in first
        assert "total_revenue" in first
        assert "delivered_orders" in first
        assert "avg_order_value" in first
        assert "fulfillment_rate" in first

    def test_quarterly_reports_by_warehouse(self, client):
        """Filtering by warehouse should only aggregate orders from that warehouse."""
        unfiltered = client.get("/api/reports/quarterly").json()
        filtered = client.get("/api/reports/quarterly?warehouse=Tokyo").json()

        unfiltered_total = sum(q["total_orders"] for q in unfiltered)
        filtered_total = sum(q["total_orders"] for q in filtered)
        assert filtered_total <= unfiltered_total
        assert filtered_total > 0

    def test_quarterly_reports_by_category(self, client):
        """Filtering by category should only aggregate orders from that category."""
        unfiltered = client.get("/api/reports/quarterly").json()
        filtered = client.get("/api/reports/quarterly?category=Sensors").json()

        unfiltered_total = sum(q["total_orders"] for q in unfiltered)
        filtered_total = sum(q["total_orders"] for q in filtered)
        assert filtered_total <= unfiltered_total
        assert filtered_total > 0

    def test_quarterly_reports_by_status(self, client):
        """Filtering by status should only aggregate orders with that status."""
        response = client.get("/api/reports/quarterly?status=Delivered")
        assert response.status_code == 200
        data = response.json()
        for q in data:
            # every delivered-only quarter must have delivered_orders == total_orders
            assert q["delivered_orders"] == q["total_orders"]

    def test_quarterly_reports_narrow_filter_reduces_totals(self, client):
        """A combination of filters should never produce more orders than the unfiltered total."""
        unfiltered = client.get("/api/reports/quarterly").json()
        filtered = client.get(
            "/api/reports/quarterly?warehouse=London&category=Actuators&status=Backordered"
        ).json()

        unfiltered_total = sum(q["total_orders"] for q in unfiltered)
        filtered_total = sum(q["total_orders"] for q in filtered)
        assert filtered_total <= unfiltered_total


class TestMonthlyTrendsEndpoint:
    """Test suite for /api/reports/monthly-trends."""

    def test_get_monthly_trends_unfiltered(self, client):
        """Test getting monthly trends with no filters returns all months with orders."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        assert "month" in first
        assert "order_count" in first
        assert "revenue" in first
        assert "delivered_count" in first

    def test_monthly_trends_by_warehouse(self, client):
        """Filtering by warehouse should only aggregate orders from that warehouse."""
        unfiltered = client.get("/api/reports/monthly-trends").json()
        filtered = client.get("/api/reports/monthly-trends?warehouse=San Francisco").json()

        unfiltered_total = sum(m["order_count"] for m in unfiltered)
        filtered_total = sum(m["order_count"] for m in filtered)
        assert filtered_total <= unfiltered_total
        assert filtered_total > 0

    def test_monthly_trends_by_month(self, client):
        """Filtering by a specific month should only include that month's orders."""
        all_months = client.get("/api/reports/monthly-trends").json()
        assert len(all_months) > 0
        target_month = all_months[0]["month"]

        response = client.get(f"/api/reports/monthly-trends?month={target_month}")
        assert response.status_code == 200
        data = response.json()
        assert all(m["month"] == target_month for m in data)

    def test_monthly_trends_by_status(self, client):
        """Filtering by status should only aggregate orders with that status."""
        response = client.get("/api/reports/monthly-trends?status=Delivered")
        assert response.status_code == 200
        data = response.json()
        for m in data:
            assert m["delivered_count"] == m["order_count"]
