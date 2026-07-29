import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders, tasks, restock_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

# Simulated per-category supplier lead times (days) for restocking orders
LEAD_TIME_BY_CATEGORY = {
    'Circuit Boards': 21,
    'Sensors': 14,
    'Actuators': 18,
    'Controllers': 16,
    'Power Supplies': 10,
}
DEFAULT_LEAD_TIME_DAYS = 14

# Urgency multiplier by demand trend, used by the restocking recommendation algorithm
TREND_WEIGHT = {'increasing': 1.3, 'stable': 1.0, 'decreasing': 0.7}

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
    purchase_order_id: Optional[str] = None

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

class Task(BaseModel):
    id: str
    title: str
    priority: str
    dueDate: str
    status: str

class CreateTaskRequest(BaseModel):
    title: str
    priority: str
    dueDate: str

class RestockRecommendationItem(BaseModel):
    sku: str
    item_name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    forecasted_demand: int
    trend: str
    unit_cost: float
    shortfall: int
    recommended_quantity: int
    is_partial: bool
    urgency: float
    value_density: float
    line_cost: float

class RestockRecommendationsResponse(BaseModel):
    recommendations: List[RestockRecommendationItem]
    budget: float
    total_cost: float
    remaining_budget: float
    max_addressable_cost: float
    candidate_count: int

class RestockOrderItem(BaseModel):
    sku: str
    name: str
    category: str
    quantity: int
    unit_cost: float
    line_total: float

class RestockOrder(BaseModel):
    id: str
    order_number: str
    items: List[RestockOrderItem]
    status: str
    budget: float
    total_cost: float
    order_date: str
    lead_time_days: int
    expected_delivery: str
    warehouse: Optional[str] = None
    category: Optional[str] = None

class RestockOrderRequest(BaseModel):
    budget: float
    warehouse: Optional[str] = None
    category: Optional[str] = None

def build_restock_candidates(warehouse: Optional[str] = None, category: Optional[str] = None) -> list:
    """All shortfall>0 inventory items in scope, sorted desc by value_density. Budget-independent."""
    filtered_inventory = apply_filters(inventory_items, warehouse, category)
    forecast_by_sku = {f['item_sku']: f for f in demand_forecasts}

    candidates = []
    for item in filtered_inventory:
        forecast = forecast_by_sku.get(item['sku'])
        forecasted_demand = forecast['forecasted_demand'] if forecast else 0
        trend = forecast['trend'] if forecast else 'stable'

        shortfall = max(
            forecasted_demand - item['quantity_on_hand'],
            item['reorder_point'] - item['quantity_on_hand'],
            0
        )
        if shortfall <= 0:
            continue

        stock_ratio = item['quantity_on_hand'] / max(item['reorder_point'], 1)
        trend_weight = TREND_WEIGHT.get(trend, 1.0)
        urgency = trend_weight / max(stock_ratio, 0.1)
        unit_cost = item['unit_cost']
        value_density = urgency / unit_cost if unit_cost > 0 else float('inf')

        candidates.append({
            'sku': item['sku'],
            'item_name': item['name'],
            'category': item['category'],
            'warehouse': item['warehouse'],
            'quantity_on_hand': item['quantity_on_hand'],
            'reorder_point': item['reorder_point'],
            'forecasted_demand': forecasted_demand,
            'trend': trend,
            'unit_cost': unit_cost,
            'shortfall': shortfall,
            'urgency': urgency,
            'value_density': value_density,
        })

    candidates.sort(key=lambda c: c['value_density'], reverse=True)
    return candidates

def allocate_budget(candidates: list, budget: float):
    """Greedy walk by value_density: full shortfall while it fits, one partial fill, then stop."""
    remaining = budget
    recs = []

    for c in candidates:
        full_cost = c['shortfall'] * c['unit_cost']
        if full_cost <= remaining:
            recs.append({**c, 'recommended_quantity': c['shortfall'], 'is_partial': False, 'line_cost': full_cost})
            remaining -= full_cost
            continue

        # Doesn't fully fit: take a partial quantity, then stop (later items are less cost-efficient anyway)
        qty = int((remaining + 1e-6) / c['unit_cost']) if c['unit_cost'] > 0 else 0
        if qty > 0:
            line_cost = qty * c['unit_cost']
            recs.append({**c, 'recommended_quantity': qty, 'is_partial': True, 'line_cost': line_cost})
            remaining -= line_cost
        break

    total_cost = sum(r['line_cost'] for r in recs)
    return recs, total_cost, remaining

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

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
    # Add has_purchase_order flag and purchase_order_id to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        matching_po = next((po for po in purchase_orders if po["backlog_item_id"] == item["id"]), None)
        item_dict["has_purchase_order"] = matching_po is not None
        item_dict["purchase_order_id"] = matching_po["id"] if matching_po else None
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

@app.post("/api/purchase-orders", response_model=PurchaseOrder, status_code=201)
def create_purchase_order(request: CreatePurchaseOrderRequest):
    """Create a purchase order for a backlog item"""
    purchase_order = {
        "id": str(uuid.uuid4()),
        "backlog_item_id": request.backlog_item_id,
        "supplier_name": request.supplier_name,
        "quantity": request.quantity,
        "unit_cost": request.unit_cost,
        "expected_delivery_date": request.expected_delivery_date,
        "status": "Pending",
        "created_date": datetime.now().isoformat(),
        "notes": request.notes,
    }
    purchase_orders.append(purchase_order)
    return purchase_order

@app.get("/api/purchase-orders/{backlog_item_id}", response_model=PurchaseOrder)
def get_purchase_order_by_backlog_item(backlog_item_id: str):
    """Get the purchase order for a specific backlog item"""
    purchase_order = next(
        (po for po in purchase_orders if po["backlog_item_id"] == backlog_item_id), None
    )
    if not purchase_order:
        raise HTTPException(status_code=404, detail=f"No purchase order found for backlog item {backlog_item_id}")
    return purchase_order

@app.get("/api/tasks", response_model=List[Task])
def get_tasks():
    """Get all tasks"""
    return tasks

@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(request: CreateTaskRequest):
    """Create a new task"""
    task = {
        "id": str(uuid.uuid4()),
        "title": request.title,
        "priority": request.priority,
        "dueDate": request.dueDate,
        "status": "pending",
    }
    tasks.append(task)
    return task

@app.delete("/api/tasks/{task_id}", response_model=Task)
def delete_task(task_id: str):
    """Delete a task"""
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    tasks.remove(task)
    return task

@app.patch("/api/tasks/{task_id}", response_model=Task)
def toggle_task(task_id: str):
    """Toggle a task's status between pending and completed"""
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task["status"] = "completed" if task["status"] == "pending" else "pending"
    return task

@app.get("/api/restocking/recommendations", response_model=RestockRecommendationsResponse)
def get_restock_recommendations(
    budget: float = 0,
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Recommend inventory items to restock within a budget, ranked by urgency-per-dollar"""
    if budget < 0:
        raise HTTPException(status_code=400, detail="budget must be >= 0")

    candidates = build_restock_candidates(warehouse, category)
    recommendations, total_cost, remaining = allocate_budget(candidates, budget)
    max_addressable_cost = sum(c['shortfall'] * c['unit_cost'] for c in candidates)

    return {
        "recommendations": recommendations,
        "budget": budget,
        "total_cost": round(total_cost, 2),
        "remaining_budget": round(remaining, 2),
        "max_addressable_cost": round(max_addressable_cost, 2),
        "candidate_count": len(candidates),
    }

@app.post("/api/restocking/orders", response_model=RestockOrder, status_code=201)
def create_restock_order(request: RestockOrderRequest):
    """Submit a restocking order for the recommended items within the given budget"""
    if request.budget <= 0:
        raise HTTPException(status_code=400, detail="budget must be greater than 0")

    candidates = build_restock_candidates(request.warehouse, request.category)
    recommendations, total_cost, _ = allocate_budget(candidates, request.budget)
    if not recommendations:
        raise HTTPException(status_code=400, detail="No restock recommendations for the given budget and filters")

    now = datetime.now()
    lead_time_days = max(
        LEAD_TIME_BY_CATEGORY.get(r['category'], DEFAULT_LEAD_TIME_DAYS) for r in recommendations
    )

    order = {
        "id": str(len(restock_orders) + 1),
        "order_number": f"RSO-{now.year}-{len(restock_orders) + 1:04d}",
        "items": [
            {
                "sku": r['sku'],
                "name": r['item_name'],
                "category": r['category'],
                "quantity": r['recommended_quantity'],
                "unit_cost": r['unit_cost'],
                "line_total": round(r['line_cost'], 2),
            }
            for r in recommendations
        ],
        "status": "Submitted",
        "budget": request.budget,
        "total_cost": round(total_cost, 2),
        "order_date": now.isoformat(),
        "lead_time_days": lead_time_days,
        "expected_delivery": (now + timedelta(days=lead_time_days)).isoformat(),
        "warehouse": request.warehouse,
        "category": request.category,
    }
    restock_orders.append(order)
    return order

@app.get("/api/restocking/orders", response_model=List[RestockOrder])
def get_restock_orders():
    """Get all submitted restocking orders (not filterable by warehouse/category)"""
    return restock_orders

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
