"""
Tests for restocking endpoints (recommendations and submitted orders).
"""
import pytest

import main


@pytest.fixture(autouse=True)
def clear_restock_orders():
    """Restock orders live in a module-level list, so isolate each test."""
    main.restock_orders.clear()
    yield
    main.restock_orders.clear()


class TestRestockRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_zero_budget_recommends_nothing(self, client):
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total_cost"] == 0
        assert data["lead_time_days"] == 0
        assert data["max_budget"] >= 100

    def test_negative_budget_rejected(self, client):
        response = client.get("/api/restocking/recommendations?budget=-5")
        assert response.status_code == 400

    def test_total_never_exceeds_budget(self, client):
        for budget in (50, 500, 5000, 20000):
            data = client.get(f"/api/restocking/recommendations?budget={budget}").json()
            assert data["total_cost"] <= budget
            assert data["total_cost"] == pytest.approx(sum(i["line_cost"] for i in data["items"]))

    def test_max_budget_covers_every_shortfall(self, client):
        max_budget = client.get("/api/restocking/recommendations?budget=0").json()["max_budget"]
        data = client.get(f"/api/restocking/recommendations?budget={max_budget}").json()
        assert data["items"]
        for item in data["items"]:
            assert item["quantity"] == item["shortfall"]

    def test_increasing_trend_items_come_first(self, client):
        max_budget = client.get("/api/restocking/recommendations?budget=0").json()["max_budget"]
        items = client.get(f"/api/restocking/recommendations?budget={max_budget}").json()["items"]
        trends = [i["trend"] == "increasing" for i in items]
        assert trends == sorted(trends, reverse=True)

    def test_partial_quantity_when_budget_is_tight(self, client):
        data = client.get("/api/restocking/recommendations?budget=100").json()
        assert data["items"]
        assert any(i["quantity"] < i["shortfall"] for i in data["items"])

    def test_lead_time_is_longest_item(self, client):
        max_budget = client.get("/api/restocking/recommendations?budget=0").json()["max_budget"]
        data = client.get(f"/api/restocking/recommendations?budget={max_budget}").json()
        assert data["lead_time_days"] == max(i["lead_time_days"] for i in data["items"])


class TestRestockOrders:
    """Test suite for POST and GET /api/restocking/orders."""

    def _recommend(self, client, budget=5000):
        return client.get(f"/api/restocking/recommendations?budget={budget}").json()

    def test_submit_order(self, client):
        rec = self._recommend(client)
        payload = {
            "budget": 5000,
            "items": [{"sku": i["sku"], "quantity": i["quantity"]} for i in rec["items"]],
        }
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"].startswith("RST-")
        assert order["status"] == "Submitted"
        assert order["total_cost"] == pytest.approx(rec["total_cost"])
        assert order["lead_time_days"] == rec["lead_time_days"]
        assert order["expected_delivery"] > order["submitted_date"]

    def test_submitted_order_listed_newest_first(self, client):
        rec = self._recommend(client)
        item = rec["items"][0]
        payload = {"budget": 5000, "items": [{"sku": item["sku"], "quantity": 1}]}
        first = client.post("/api/restocking/orders", json=payload).json()
        second = client.post("/api/restocking/orders", json=payload).json()

        listed = client.get("/api/restocking/orders").json()
        assert [o["id"] for o in listed] == [second["id"], first["id"]]

    def test_empty_order_rejected(self, client):
        response = client.post("/api/restocking/orders", json={"budget": 100, "items": []})
        assert response.status_code == 400

    def test_unknown_sku_rejected(self, client):
        response = client.post(
            "/api/restocking/orders",
            json={"budget": 100, "items": [{"sku": "NOPE-000", "quantity": 1}]},
        )
        assert response.status_code == 400

    def test_non_positive_quantity_rejected(self, client):
        sku = self._recommend(client)["items"][0]["sku"]
        response = client.post(
            "/api/restocking/orders",
            json={"budget": 5000, "items": [{"sku": sku, "quantity": 0}]},
        )
        assert response.status_code == 400

    def test_over_budget_rejected_and_not_stored(self, client):
        item = self._recommend(client)["items"][0]
        response = client.post(
            "/api/restocking/orders",
            json={"budget": 1, "items": [{"sku": item["sku"], "quantity": item["shortfall"]}]},
        )
        assert response.status_code == 400
        assert client.get("/api/restocking/orders").json() == []
