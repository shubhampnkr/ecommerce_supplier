"""Test HTML report rendering with mock data."""
import pytest
from datetime import datetime
from core.models import (
    AccountHealth,
    BusinessStrategy,
    DailyReport,
    OrderMetrics,
    ProductMetrics,
    ProductRecommendation,
    ProductAlert,
)
from agents.report_agent import ReportAgent


def _mock_report() -> DailyReport:
    return DailyReport(
        report_date="2024-06-01",
        supplier_name="Test Supplier",
        order_metrics=OrderMetrics(
            total_orders_7d=120,
            total_orders_30d=480,
            revenue_7d=45_000,
            revenue_30d=1_80_000,
            pending_orders=12,
            shipped_orders=80,
            delivered_orders=360,
            cancelled_orders=20,
            return_orders=8,
            avg_order_value=375.0,
        ),
        account_health=AccountHealth(
            supplier_rating=4.2,
            cancellation_rate_pct=4.2,
            return_rate_pct=1.7,
            dispatch_score=88,
            quality_score=91,
            penalty_amount=0,
            account_status="active",
        ),
        top_performing_products=[
            ProductMetrics(
                product_id="P001",
                product_name="Cotton Kurti Set",
                price=499,
                mrp=799,
                units_sold_30d=120,
                revenue_30d=59_880,
                return_rate_pct=2.1,
                rating=4.5,
                conversion_rate_pct=8.3,
            )
        ],
        worst_performing_products=[
            ProductMetrics(
                product_id="P099",
                product_name="Synthetic Bedsheet",
                price=299,
                mrp=599,
                units_sold_30d=3,
                revenue_30d=897,
                return_rate_pct=33.3,
                rating=2.8,
                conversion_rate_pct=0.4,
            )
        ],
        pricing_recommendations=[
            ProductRecommendation(
                product_id="P099",
                product_name="Synthetic Bedsheet",
                current_price=299,
                recommended_price=199,
                reasoning="High return rate suggests quality-price mismatch. Reducing to ₹199 aligns with buyer expectations.",
                priority="high",
            )
        ],
        products_to_remove=[
            ProductAlert(
                product_id="P099",
                product_name="Synthetic Bedsheet",
                alert_type="remove",
                reason="0 sales in 30 days, 33% return rate, rating below 3.0",
                urgency="high",
            )
        ],
        business_strategies=[
            BusinessStrategy(
                title="Bundle Best-Sellers",
                description="Create combo packs of your top Kurti sets with matching dupatta.",
                expected_impact="15-25% increase in AOV",
                effort="low",
                timeframe="immediate",
            )
        ],
        executive_summary="Strong performance in ethnic wear. Bedsheet category dragging metrics down.",
        key_highlights=["Revenue ₹1.8L in 30d", "Top product 120 units sold"],
        action_items=["Remove Synthetic Bedsheet listing", "Launch Kurti bundle pack"],
    )


def test_html_render():
    agent = ReportAgent()
    report = _mock_report()
    html = agent.render_html(report)
    assert "Cotton Kurti Set" in html
    assert "Test Supplier" in html
    assert "Meesho" in html
    assert "1.8" in html or "1,80,000" in html or "₹" in html


def test_report_save(tmp_path):
    import os
    os.environ["REPORT_DOWNLOAD_DIR"] = str(tmp_path)
    
    from config.settings import settings
    settings.report_download_dir = tmp_path

    agent = ReportAgent()
    agent.download_dir = tmp_path
    report = _mock_report()
    html_path, pdf_path = agent.save_report(report)
    assert html_path.exists()
    assert html_path.suffix == ".html"
