"""
Shared Pydantic data models used across all agents.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Raw scrape models
# ─────────────────────────────────────────────────────────────────────────────

class ProductMetrics(BaseModel):
    product_id: str
    product_name: str
    sku: str = ""
    category: str = ""
    price: float = 0.0
    mrp: float = 0.0
    discount_pct: float = 0.0
    units_sold_7d: int = 0
    units_sold_30d: int = 0
    revenue_7d: float = 0.0
    revenue_30d: float = 0.0
    returns_7d: int = 0
    return_rate_pct: float = 0.0
    rating: float = 0.0
    review_count: int = 0
    inventory: int = 0
    impressions_7d: int = 0
    clicks_7d: int = 0
    ctr_pct: float = 0.0
    conversion_rate_pct: float = 0.0
    is_active: bool = True
    raw_data: dict[str, Any] = Field(default_factory=dict)


class OrderMetrics(BaseModel):
    total_orders_7d: int = 0
    total_orders_30d: int = 0
    revenue_7d: float = 0.0
    revenue_30d: float = 0.0
    pending_orders: int = 0
    shipped_orders: int = 0
    delivered_orders: int = 0
    cancelled_orders: int = 0
    return_orders: int = 0
    avg_order_value: float = 0.0


class AccountHealth(BaseModel):
    supplier_rating: float = 0.0
    cancellation_rate_pct: float = 0.0
    return_rate_pct: float = 0.0
    dispatch_score: float = 0.0
    quality_score: float = 0.0
    penalty_amount: float = 0.0
    active_penalties: list[str] = Field(default_factory=list)
    account_status: str = "active"


class DashboardSnapshot(BaseModel):
    """Complete snapshot scraped from Meesho Supplier Portal."""
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    supplier_id: str = ""
    supplier_name: str = ""
    order_metrics: OrderMetrics = Field(default_factory=OrderMetrics)
    account_health: AccountHealth = Field(default_factory=AccountHealth)
    products: list[ProductMetrics] = Field(default_factory=list)
    raw_pages: dict[str, str] = Field(default_factory=dict)  # page_name -> HTML/text


# ─────────────────────────────────────────────────────────────────────────────
# Analysis / report models
# ─────────────────────────────────────────────────────────────────────────────

class ProductRecommendation(BaseModel):
    product_id: str
    product_name: str
    current_price: float
    recommended_price: float
    reasoning: str
    priority: str = "medium"  # high | medium | low


class ProductAlert(BaseModel):
    product_id: str
    product_name: str
    alert_type: str  # remove | review | restock | price_drop
    reason: str
    urgency: str = "medium"


class BusinessStrategy(BaseModel):
    title: str
    description: str
    expected_impact: str
    effort: str  # low | medium | high
    timeframe: str  # immediate | short_term | long_term


class DailyReport(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    report_date: str = ""
    supplier_name: str = ""

    # Metrics summary
    order_metrics: OrderMetrics = Field(default_factory=OrderMetrics)
    account_health: AccountHealth = Field(default_factory=AccountHealth)

    # Product intelligence
    top_performing_products: list[ProductMetrics] = Field(default_factory=list)
    worst_performing_products: list[ProductMetrics] = Field(default_factory=list)

    # AI-generated insights
    pricing_recommendations: list[ProductRecommendation] = Field(default_factory=list)
    products_to_remove: list[ProductAlert] = Field(default_factory=list)
    business_strategies: list[BusinessStrategy] = Field(default_factory=list)

    # Narrative sections
    executive_summary: str = ""
    key_highlights: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)

    # Raw snapshot for traceability
    snapshot: Optional[DashboardSnapshot] = None
