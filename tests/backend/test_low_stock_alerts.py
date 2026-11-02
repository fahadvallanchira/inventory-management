"""
Tests for the low-stock alerts API endpoint.
"""
import main


def _item(id_, qty, reorder, warehouse="Tokyo", category="Sensors", supplier_id="SUP-001"):
    return {
        "id": id_, "sku": f"SKU-{id_}", "name": f"Item {id_}", "category": category,
        "warehouse": warehouse, "quantity_on_hand": qty, "reorder_point": reorder,
        "unit_cost": 1.0, "location": "A-1", "last_updated": "2025-01-01T00:00:00",
        "supplier_id": supplier_id,
    }


class TestLowStockAlertsEndpoint:
    """Test suite for GET /api/alerts/low-stock."""

    def test_response_structure(self, client):
        response = client.get("/api/alerts/low-stock")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data and "critical_count" in data and "items" in data
        assert data["count"] == len(data["items"])
        assert data["count"] > 0
        for key in ["id", "sku", "name", "quantity", "reorder_point", "warehouse",
                    "category", "supplier_name", "severity"]:
            assert key in data["items"][0]

    def test_only_items_at_or_below_reorder_point(self, client):
        data = client.get("/api/alerts/low-stock").json()
        inventory = {i["id"]: i for i in client.get("/api/inventory").json()}
        expected = {i for i, v in inventory.items() if v["quantity_on_hand"] <= v["reorder_point"]}
        assert {a["id"] for a in data["items"]} == expected

    def test_supplier_name_resolved(self, client):
        data = client.get("/api/alerts/low-stock").json()
        suppliers = {s["id"]: s["name"] for s in client.get("/api/suppliers").json()}
        inventory = {i["id"]: i for i in client.get("/api/inventory").json()}
        for a in data["items"]:
            assert a["supplier_name"] == suppliers[inventory[a["id"]]["supplier_id"]]

    def test_filter_by_warehouse(self, client):
        all_items = client.get("/api/alerts/low-stock").json()["items"]
        wh = all_items[0]["warehouse"]
        data = client.get("/api/alerts/low-stock", params={"warehouse": wh}).json()
        assert data["count"] >= 1
        assert all(a["warehouse"] == wh for a in data["items"])

    def test_filter_by_category(self, client):
        all_items = client.get("/api/alerts/low-stock").json()["items"]
        cat = all_items[0]["category"]
        data = client.get("/api/alerts/low-stock", params={"category": cat.upper()}).json()
        assert data["count"] >= 1
        assert all(a["category"].lower() == cat.lower() for a in data["items"])

    def test_all_filters_are_no_filter(self, client):
        base = client.get("/api/alerts/low-stock").json()
        both = client.get("/api/alerts/low-stock?warehouse=all&category=all").json()
        assert base == both

    def test_no_match_returns_empty(self, client):
        data = client.get("/api/alerts/low-stock?warehouse=Nowhere").json()
        assert data == {"count": 0, "critical_count": 0, "items": []}

    def test_severity_rules_and_sorting(self, client, monkeypatch):
        items = [
            _item("a", 100, 100),   # exactly at reorder point -> warning
            _item("b", 50, 100),    # exactly 50% -> critical
            _item("c", 0, 100),     # zero -> critical
            _item("d", 51, 100),    # just above 50% -> warning
            _item("e", 200, 100),   # healthy -> excluded
            _item("f", 10, 100),    # 10% -> critical
            _item("g", 0, 0),       # zero stock, zero reorder point -> critical
        ]
        monkeypatch.setattr(main, "inventory_items", items)
        data = client.get("/api/alerts/low-stock").json()
        by_id = {a["id"]: a for a in data["items"]}
        assert "e" not in by_id
        assert {k: v["severity"] for k, v in by_id.items()} == {
            "a": "warning", "b": "critical", "c": "critical",
            "d": "warning", "f": "critical", "g": "critical",
        }
        assert data["count"] == 6
        assert data["critical_count"] == 4
        # Critical first, then warnings; within a severity, lowest stock ratio first
        severities = [a["severity"] for a in data["items"]]
        assert severities == sorted(severities, key=lambda s: s != "critical")
        warn_ids = [a["id"] for a in data["items"] if a["severity"] == "warning"]
        assert warn_ids == ["d", "a"]

    def test_missing_supplier_does_not_error(self, client, monkeypatch):
        monkeypatch.setattr(main, "inventory_items", [_item("x", 1, 10, supplier_id=None)])
        data = client.get("/api/alerts/low-stock").json()
        assert data["items"][0]["supplier_name"] is None
