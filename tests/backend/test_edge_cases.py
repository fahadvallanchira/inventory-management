"""
Edge-case tests for filtering and lookup behaviour of the API.

These pin down current server behaviour (see filter_by_month / apply_filters
in server/main.py), including quirks such as unknown quarters being ignored.
"""
import pytest

Q1_MONTHS = ("2025-01", "2025-02", "2025-03")


class TestQuarterFiltering:
    """Quarter / month handling in the `month` query param."""

    def test_unknown_quarter_returns_unfiltered(self, client):
        """QUARTER_MAP only covers 2025, so an unknown quarter is ignored."""
        all_orders = client.get("/api/orders").json()
        response = client.get("/api/orders?month=Q1-2099")
        assert response.status_code == 200
        assert response.json() == all_orders

    def test_malformed_quarter_returns_unfiltered(self, client):
        """Anything starting with 'Q' but not in QUARTER_MAP is ignored."""
        all_orders = client.get("/api/orders").json()
        response = client.get("/api/orders?month=Qwerty")
        assert response.status_code == 200
        assert response.json() == all_orders

    def test_q1_2025_only_contains_q1_months(self, client):
        """Q1-2025 returns only orders dated Jan-Mar 2025."""
        data = client.get("/api/orders?month=Q1-2025").json()
        assert len(data) > 0
        for order in data:
            assert order["order_date"].startswith(Q1_MONTHS)

    def test_quarters_partition_orders(self, client):
        """Each order falls into exactly one 2025 quarter (if dated in 2025)."""
        total = 0
        for q in ("Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025"):
            total += len(client.get(f"/api/orders?month={q}").json())
        in_2025 = [
            o for o in client.get("/api/orders").json()
            if o["order_date"].startswith("2025-")
        ]
        assert total == len(in_2025)

    def test_month_all_returns_everything(self, client):
        all_orders = client.get("/api/orders").json()
        assert client.get("/api/orders?month=all").json() == all_orders

    def test_empty_month_returns_everything(self, client):
        """An empty month string is falsy and treated as no filter."""
        all_orders = client.get("/api/orders").json()
        assert client.get("/api/orders?month=").json() == all_orders

    def test_nonexistent_month_returns_empty(self, client):
        """A direct month with no matching orders yields an empty list."""
        response = client.get("/api/orders?month=2025-13")
        assert response.status_code == 200
        assert response.json() == []

    def test_dashboard_unknown_quarter_matches_unfiltered(self, client):
        """Dashboard uses the same month filter, so unknown quarter is ignored."""
        base = client.get("/api/dashboard/summary").json()
        assert client.get("/api/dashboard/summary?month=Q7-2025").json() == base


class TestNotFound:
    """Invalid IDs return 404 with a detail message."""

    @pytest.mark.parametrize("path", [
        "/api/inventory/does-not-exist",
        "/api/orders/does-not-exist",
        "/api/inventory/0",
        "/api/orders/-1",
        "/api/inventory/%20",
    ])
    def test_invalid_id_returns_404(self, client, path):
        response = client.get(path)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_unknown_route_returns_404(self, client):
        assert client.get("/api/nope").status_code == 404

    def test_unimplemented_routes_return_404(self, client):
        """api.js calls these, but the server has no such routes (Known Gaps)."""
        assert client.get("/api/tasks").status_code == 404
        assert client.get("/api/purchase-orders").status_code == 404


class TestAllFilterValue:
    """'all' disables a filter on every endpoint that supports it."""

    def test_inventory_all_filters(self, client):
        everything = client.get("/api/inventory").json()
        data = client.get("/api/inventory?warehouse=all&category=all").json()
        assert data == everything

    def test_orders_all_filters(self, client):
        everything = client.get("/api/orders").json()
        data = client.get(
            "/api/orders?warehouse=all&category=all&status=all&month=all"
        ).json()
        assert data == everything

    def test_dashboard_all_filters(self, client):
        base = client.get("/api/dashboard/summary").json()
        filtered = client.get(
            "/api/dashboard/summary?warehouse=all&category=all&status=all&month=all"
        ).json()
        assert filtered == base

    def test_all_combined_with_real_filter(self, client):
        """'all' for one filter does not disturb another active filter."""
        data = client.get("/api/orders?warehouse=all&status=Delivered").json()
        assert len(data) > 0
        for order in data:
            assert order["status"] == "Delivered"


class TestFilterMatching:
    """Case sensitivity and empty-result behaviour."""

    def test_category_is_case_insensitive(self, client):
        lower = client.get("/api/inventory?category=power supplies").json()
        proper = client.get("/api/inventory?category=Power Supplies").json()
        assert len(proper) > 0
        assert lower == proper

    def test_status_is_case_insensitive(self, client):
        lower = client.get("/api/orders?status=delivered").json()
        proper = client.get("/api/orders?status=Delivered").json()
        assert len(proper) > 0
        assert lower == proper

    def test_warehouse_is_case_sensitive(self, client):
        """Warehouse is an exact match, unlike category and status."""
        assert len(client.get("/api/inventory?warehouse=Tokyo").json()) > 0
        assert client.get("/api/inventory?warehouse=tokyo").json() == []

    def test_unknown_warehouse_returns_empty_list(self, client):
        response = client.get("/api/inventory?warehouse=Atlantis")
        assert response.status_code == 200
        assert response.json() == []

    def test_unknown_category_and_status_return_empty_list(self, client):
        assert client.get("/api/orders?category=Nothing").json() == []
        assert client.get("/api/orders?status=Lost").json() == []

    def test_combined_filters_can_return_empty_list(self, client):
        """Valid values individually, but no order matches all of them."""
        response = client.get(
            "/api/orders?warehouse=Tokyo&status=Delivered&month=2025-13"
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_dashboard_with_no_matches_returns_zeros(self, client):
        data = client.get("/api/dashboard/summary?warehouse=Atlantis").json()
        assert data["total_inventory_value"] == 0
        assert data["low_stock_items"] == 0
        assert data["pending_orders"] == 0
        assert data["total_orders_value"] == 0

    def test_inventory_ignores_month_param(self, client):
        """Inventory has no time dimension; an unsupported month is ignored."""
        everything = client.get("/api/inventory").json()
        assert client.get("/api/inventory?month=2025-01").json() == everything

    def test_filters_do_not_mutate_global_data(self, client):
        before = client.get("/api/orders").json()
        client.get("/api/orders?warehouse=Tokyo&status=Delivered&month=Q1-2025")
        assert client.get("/api/orders").json() == before
