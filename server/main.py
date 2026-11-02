from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from math import ceil, floor
from typing import List, Optional
from pydantic import BaseModel
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders, restock_catalog, suppliers

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str
    # Optional so older data without a supplier link still validates
    supplier_id: Optional[str] = None

class Supplier(BaseModel):
    id: str
    name: str
    country: str
    contact_email: str
    lead_time_days: int
    rating: int
    active: bool

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

class RestockLine(BaseModel):
    sku: str
    name: str
    trend: str
    category: str
    shortfall: int
    quantity: int
    unit_cost: float
    line_cost: float
    lead_time_days: int

class RestockRecommendations(BaseModel):
    budget: float
    max_budget: float
    total_cost: float
    lead_time_days: int
    items: List[RestockLine]

class RestockOrderLineRequest(BaseModel):
    sku: str
    quantity: int

class RestockOrderRequest(BaseModel):
    items: List[RestockOrderLineRequest]
    budget: float

class RestockOrder(BaseModel):
    id: str
    order_number: str
    items: List[RestockLine]
    total_cost: float
    budget: float
    lead_time_days: int
    submitted_date: str
    expected_delivery: str
    status: str

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    supplier: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    items = apply_filters(inventory_items, warehouse, category)
    # supplier is inventory-specific, so it is applied here rather than in the
    # shared apply_filters (orders have no supplier_id). 'all' means no filter.
    if supplier and supplier != 'all':
        items = [item for item in items if item.get('supplier_id') == supplier]
    return items

class LowStockAlert(BaseModel):
    id: str
    sku: str
    name: str
    quantity: int
    reorder_point: int
    warehouse: str
    category: str
    supplier_name: Optional[str] = None
    severity: str  # 'critical' | 'warning'

class LowStockAlertsResponse(BaseModel):
    count: int
    critical_count: int
    items: List[LowStockAlert]

@app.get("/api/alerts/low-stock", response_model=LowStockAlertsResponse)
def get_low_stock_alerts(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Items at or below their reorder point, most severe first"""
    items = apply_filters(inventory_items, warehouse, category)
    supplier_names = {s["id"]: s["name"] for s in suppliers}

    alerts = []
    for item in items:
        qty, reorder = item["quantity_on_hand"], item["reorder_point"]
        if qty > reorder:
            continue
        # Critical when stocked out or at/below half the reorder point.
        # Comparing qty * 2 <= reorder avoids float math; qty == 0 is checked
        # explicitly so items with reorder_point 0 and no stock still count.
        severity = "critical" if qty == 0 or qty * 2 <= reorder else "warning"
        alerts.append({
            "id": item["id"],
            "sku": item["sku"],
            "name": item["name"],
            "quantity": qty,
            "reorder_point": reorder,
            "warehouse": item["warehouse"],
            "category": item["category"],
            # supplier_id is optional on inventory; fall back to None
            "supplier_name": supplier_names.get(item.get("supplier_id")),
            "severity": severity,
        })

    # Sort: critical before warning, then lowest stock-to-reorder ratio first.
    # max(reorder, 1) guards against division by zero for reorder_point == 0.
    alerts.sort(key=lambda a: (a["severity"] != "critical", a["quantity"] / max(a["reorder_point"], 1)))

    return {
        "count": len(alerts),
        "critical_count": sum(1 for a in alerts if a["severity"] == "critical"),
        "items": alerts,
    }

@app.get("/api/suppliers", response_model=List[Supplier])
def get_suppliers():
    """Get all suppliers"""
    return suppliers

@app.get("/api/suppliers/{supplier_id}", response_model=Supplier)
def get_supplier(supplier_id: str):
    """Get a specific supplier"""
    supplier = next((s for s in suppliers if s["id"] == supplier_id), None)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    return supplier

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports():
    """Get quarterly performance reports"""
    # Calculate quarterly statistics from orders
    quarters = {}

    for order in orders:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends():
    """Get month-over-month trends"""
    months = {}

    for order in orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result



# Restocking
restock_orders: list = []

def get_restock_candidates() -> list:
    """Join demand forecasts with inventory (preferred) or the restock catalog to price and size each SKU"""
    candidates = []
    for forecast in demand_forecasts:
        sku = forecast["item_sku"]
        stock_rows = [i for i in inventory_items if i["sku"] == sku]
        fallback = restock_catalog["items"].get(sku)
        if stock_rows:
            category = stock_rows[0]["category"]
            unit_cost = stock_rows[0]["unit_cost"]
            current_stock = sum(i["quantity_on_hand"] for i in stock_rows)
        elif fallback:
            category = fallback["category"]
            unit_cost = fallback["unit_cost"]
            current_stock = fallback["current_stock"]
        else:
            continue
        lead_times = restock_catalog["lead_times"]
        candidates.append({
            "sku": sku,
            "name": forecast["item_name"],
            "trend": forecast["trend"],
            "category": category,
            "shortfall": max(0, forecast["forecasted_demand"] - current_stock),
            "unit_cost": unit_cost,
            "lead_time_days": lead_times.get(category, lead_times["default"]),
        })
    return candidates

def to_restock_line(candidate: dict, quantity: int) -> dict:
    return {**candidate, "quantity": quantity, "line_cost": round(quantity * candidate["unit_cost"], 2)}

@app.get("/api/restocking/recommendations", response_model=RestockRecommendations)
def get_restock_recommendations(budget: float = 0):
    """Recommend restock items for a budget: increasing-trend items first, then largest shortfall"""
    if budget < 0:
        raise HTTPException(status_code=400, detail="Budget must not be negative")
    candidates = [c for c in get_restock_candidates() if c["shortfall"] > 0]
    max_budget = max(100, ceil(sum(c["shortfall"] * c["unit_cost"] for c in candidates) / 100) * 100)

    # Greedy fill: each item takes min(shortfall, what the remaining budget can afford), so a
    # high-priority item that does not fully fit still gets a partial quantity
    remaining = budget
    lines = []
    for c in sorted(candidates, key=lambda c: (c["trend"] != "increasing", -c["shortfall"])):
        quantity = min(c["shortfall"], floor(remaining / c["unit_cost"]))
        if quantity <= 0:
            continue
        line = to_restock_line(c, quantity)
        remaining -= line["line_cost"]
        lines.append(line)

    return {
        "budget": budget,
        "max_budget": max_budget,
        "total_cost": round(sum(l["line_cost"] for l in lines), 2),
        "lead_time_days": max((l["lead_time_days"] for l in lines), default=0),
        "items": lines,
    }

@app.post("/api/restocking/orders", response_model=RestockOrder, status_code=201)
def create_restock_order(request: RestockOrderRequest):
    """Submit a restocking order. Prices and lead times come from the server, not the client."""
    if not request.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")
    candidates = {c["sku"]: c for c in get_restock_candidates()}
    lines = []
    for item in request.items:
        if item.sku not in candidates:
            raise HTTPException(status_code=400, detail=f"Unknown SKU: {item.sku}")
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Quantity must be positive for {item.sku}")
        lines.append(to_restock_line(candidates[item.sku], item.quantity))

    total_cost = round(sum(l["line_cost"] for l in lines), 2)
    if total_cost > request.budget:
        raise HTTPException(status_code=400, detail="Order total exceeds budget")

    # An order ships together, so its lead time is that of its slowest item
    now = datetime.now()
    lead_time_days = max(l["lead_time_days"] for l in lines)
    order = {
        "id": str(len(restock_orders) + 1),
        "order_number": f"RST-{now.year}-{len(restock_orders) + 1:04d}",
        "items": lines,
        "total_cost": total_cost,
        "budget": request.budget,
        "lead_time_days": lead_time_days,
        "submitted_date": now.isoformat(timespec="seconds"),
        "expected_delivery": (now + timedelta(days=lead_time_days)).isoformat(timespec="seconds"),
        "status": "Submitted",
    }
    restock_orders.append(order)
    return order

@app.get("/api/restocking/orders", response_model=List[RestockOrder])
def get_restock_orders():
    """Get submitted restocking orders, newest first"""
    return list(reversed(restock_orders))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
