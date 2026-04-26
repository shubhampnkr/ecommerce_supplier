"""
AnalysisAgent – turns a raw DashboardSnapshot into a structured DailyReport
using LangChain + LLM.

Responsibilities:
  1. Rank products (top / worst performing)
  2. Detect pricing issues & generate recommendations
  3. Flag products to remove
  4. Generate business strategies
  5. Write an executive summary + action items
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from core.llm import get_llm
from core.logger import logger
from core.models import (
    AccountHealth,
    BusinessStrategy,
    DailyReport,
    DashboardSnapshot,
    OrderMetrics,
    ProductAlert,
    ProductMetrics,
    ProductRecommendation,
)


# ─────────────────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a senior e-commerce business analyst with deep expertise in the Indian
marketplace ecosystem (Meesho, Flipkart, Amazon India). Your job is to analyse
supplier performance data and generate actionable, data-driven insights.

Always return ONLY valid JSON – no markdown fences, no prose before or after.
Numbers must be numeric types. Percentages as numbers (e.g. 12.5 for 12.5%).
Dates as ISO-8601 strings.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builders
# ─────────────────────────────────────────────────────────────────────────────

def _product_summary(products: list[ProductMetrics]) -> str:
    rows = []
    for p in products:
        rows.append(
            f"  id={p.product_id} name='{p.product_name}' price={p.price} mrp={p.mrp} "
            f"sold_30d={p.units_sold_30d} revenue_30d={p.revenue_30d} "
            f"return_rate={p.return_rate_pct}% rating={p.rating} "
            f"ctr={p.ctr_pct}% conv={p.conversion_rate_pct}% active={p.is_active}"
        )
    return "\n".join(rows) if rows else "No product data available."


def _build_analysis_prompt(snapshot: DashboardSnapshot) -> str:
    om = snapshot.order_metrics
    ah = snapshot.account_health
    return f"""
Supplier: {snapshot.supplier_name or 'Unknown'} | Date: {datetime.now().strftime('%Y-%m-%d')}

=== ORDER METRICS ===
7-day orders: {om.total_orders_7d}  |  30-day orders: {om.total_orders_30d}
7-day revenue: ₹{om.revenue_7d:,.0f}  |  30-day revenue: ₹{om.revenue_30d:,.0f}
Avg order value: ₹{om.avg_order_value:,.0f}
Pending: {om.pending_orders}  Shipped: {om.shipped_orders}  Delivered: {om.delivered_orders}
Cancelled: {om.cancelled_orders}  Returns: {om.return_orders}

=== ACCOUNT HEALTH ===
Supplier rating: {ah.supplier_rating}/5
Cancellation rate: {ah.cancellation_rate_pct}%  |  Return rate: {ah.return_rate_pct}%
Dispatch score: {ah.dispatch_score}  |  Quality score: {ah.quality_score}
Penalties: ₹{ah.penalty_amount:,.0f} | Active: {ah.active_penalties}
Account status: {ah.account_status}

=== PRODUCTS ({len(snapshot.products)} total) ===
{_product_summary(snapshot.products)}

---
Based on the above data, return a single JSON object with this exact structure:

{{
  "top_performing_product_ids": ["id1", "id2", "id3", "id4", "id5"],
  "worst_performing_product_ids": ["id1", "id2", "id3", "id4", "id5"],
  "pricing_recommendations": [
    {{
      "product_id": "string",
      "product_name": "string",
      "current_price": 0.0,
      "recommended_price": 0.0,
      "reasoning": "string",
      "priority": "high|medium|low"
    }}
  ],
  "products_to_remove": [
    {{
      "product_id": "string",
      "product_name": "string",
      "alert_type": "remove|review|restock",
      "reason": "string",
      "urgency": "high|medium|low"
    }}
  ],
  "business_strategies": [
    {{
      "title": "string",
      "description": "string",
      "expected_impact": "string",
      "effort": "low|medium|high",
      "timeframe": "immediate|short_term|long_term"
    }}
  ],
  "executive_summary": "2-3 paragraph narrative summary",
  "key_highlights": ["bullet 1", "bullet 2", "bullet 3"],
  "action_items": ["action 1", "action 2", "action 3"]
}}

Rules:
- top/worst lists must reference product_ids that exist in the data above
- pricing recommendations: suggest at least 3 products where a price change could improve revenue or reduce returns
- products_to_remove: flag products with 0 sales in 30 days, >30% return rate, or rating <3.0
- business_strategies: provide at least 5 specific, actionable strategies relevant to Meesho/Indian ecommerce
- executive_summary: be direct, data-driven, and flag any critical account health issues
"""


# ─────────────────────────────────────────────────────────────────────────────
# AnalysisAgent
# ─────────────────────────────────────────────────────────────────────────────

class AnalysisAgent:
    def __init__(self) -> None:
        self.llm = get_llm(temperature=0.3)

    def _get_products_by_ids(
        self, products: list[ProductMetrics], ids: list[str]
    ) -> list[ProductMetrics]:
        id_map = {p.product_id: p for p in products}
        return [id_map[i] for i in ids if i in id_map]

    async def run(self, snapshot: DashboardSnapshot) -> DailyReport:
        logger.info("AnalysisAgent: starting LLM analysis…")

        prompt = _build_analysis_prompt(snapshot)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        import asyncio
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.llm.invoke(messages)
        )

        raw = response.content.strip()
        # Strip markdown fences
        import re
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

        try:
            analysis = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse LLM response as JSON: {exc}")
            logger.debug(f"Raw response: {raw[:500]}")
            analysis = {}

        # Build report
        report = DailyReport(
            report_date=datetime.now().strftime("%Y-%m-%d"),
            supplier_name=snapshot.supplier_name,
            order_metrics=snapshot.order_metrics,
            account_health=snapshot.account_health,
            snapshot=snapshot,
        )

        # Products
        top_ids = analysis.get("top_performing_product_ids", [])
        worst_ids = analysis.get("worst_performing_product_ids", [])
        report.top_performing_products = self._get_products_by_ids(snapshot.products, top_ids)
        report.worst_performing_products = self._get_products_by_ids(snapshot.products, worst_ids)

        # If LLM didn't return IDs, fall back to simple sort
        if not report.top_performing_products and snapshot.products:
            report.top_performing_products = sorted(
                snapshot.products, key=lambda p: p.revenue_30d, reverse=True
            )[:5]
        if not report.worst_performing_products and snapshot.products:
            report.worst_performing_products = sorted(
                snapshot.products, key=lambda p: p.revenue_30d
            )[:5]

        # Pricing recommendations
        report.pricing_recommendations = [
            ProductRecommendation(**r)
            for r in analysis.get("pricing_recommendations", [])
        ]

        # Products to remove
        report.products_to_remove = [
            ProductAlert(**a) for a in analysis.get("products_to_remove", [])
        ]

        # Business strategies
        report.business_strategies = [
            BusinessStrategy(**s) for s in analysis.get("business_strategies", [])
        ]

        # Narrative
        report.executive_summary = analysis.get("executive_summary", "")
        report.key_highlights = analysis.get("key_highlights", [])
        report.action_items = analysis.get("action_items", [])

        logger.info("AnalysisAgent: analysis complete ✓")
        return report
