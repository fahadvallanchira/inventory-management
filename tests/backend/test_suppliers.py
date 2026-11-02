"""
Tests for supplier API endpoints and the inventory supplier filter.
"""
import pytest


class TestSuppliersEndpoints:
    """Test suite for supplier-related endpoints."""

    def test_get_all_suppliers(self, client):
        """Test getting all suppliers."""
        response = client.get("/api/suppliers")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 8

        first = data[0]
        for field in ("id", "name", "country", "contact_email", "lead_time_days", "rating", "active"):
            assert field in first

    def test_supplier_field_types(self, client):
        """Test supplier field types and valid ranges."""
        for s in client.get("/api/suppliers").json():
            assert isinstance(s["lead_time_days"], int)
            assert s["lead_time_days"] > 0
            assert 1 <= s["rating"] <= 5
            assert isinstance(s["active"], bool)
            assert s["contact_email"].endswith(".example.com")

    def test_supplier_ids_unique(self, client):
        """Test that supplier ids are unique."""
        ids = [s["id"] for s in client.get("/api/suppliers").json()]
        assert len(ids) == len(set(ids))

    def test_get_supplier_by_id(self, client):
        """Test getting a specific supplier by ID."""
        all_suppliers = client.get("/api/suppliers").json()
        supplier_id = all_suppliers[0]["id"]

        response = client.get(f"/api/suppliers/{supplier_id}")
        assert response.status_code == 200
        assert response.json()["id"] == supplier_id

    def test_get_nonexistent_supplier(self, client):
        """Test getting a supplier that doesn't exist."""
        response = client.get("/api/suppliers/nonexistent-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestInventorySupplierLink:
    """Test suite for linking inventory items to suppliers."""

    def test_inventory_items_have_supplier_id(self, client):
        """Every inventory item references a real supplier."""
        supplier_ids = {s["id"] for s in client.get("/api/suppliers").json()}
        items = client.get("/api/inventory").json()
        assert len(items) > 0
        for item in items:
            assert "supplier_id" in item
            assert item["supplier_id"] in supplier_ids

    def test_every_supplier_supplies_items(self, client):
        """Each supplier should supply at least one item (useful demo data)."""
        used = {i["supplier_id"] for i in client.get("/api/inventory").json()}
        supplier_ids = {s["id"] for s in client.get("/api/suppliers").json()}
        assert used == supplier_ids

    def test_get_inventory_by_supplier(self, client):
        """Test filtering inventory by supplier."""
        supplier_id = client.get("/api/suppliers").json()[0]["id"]
        response = client.get(f"/api/inventory?supplier={supplier_id}")
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0
        for item in data:
            assert item["supplier_id"] == supplier_id

    def test_get_inventory_supplier_all(self, client):
        """supplier=all must not filter."""
        everything = client.get("/api/inventory").json()
        response = client.get("/api/inventory?supplier=all")
        assert response.status_code == 200
        assert len(response.json()) == len(everything)

    def test_get_inventory_unknown_supplier_empty(self, client):
        """An unknown supplier id yields an empty list."""
        response = client.get("/api/inventory?supplier=nonexistent-999")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_inventory_supplier_and_warehouse(self, client):
        """Supplier filter combines with warehouse filter."""
        supplier_id = client.get("/api/suppliers").json()[0]["id"]
        response = client.get(f"/api/inventory?supplier={supplier_id}&warehouse=Tokyo")
        assert response.status_code == 200
        for item in response.json():
            assert item["supplier_id"] == supplier_id
            assert item["warehouse"] == "Tokyo"
