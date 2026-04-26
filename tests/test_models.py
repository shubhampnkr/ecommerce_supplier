"""Unit tests for core data models."""
import pytest
from core.models import (
    AccountHealth,
    DailyReport,
    DashboardSnapshot,
    OrderMetrics,
    ProductMetrics,
)


def test_product_metrics_defaults():
    p = ProductMetrics(product_id="P001", product_name="Test Product")
    assert p.price == 0.0
    assert p.is_active is True
    assert p.return_rate_pct == 0.0


def test_order_metrics_defaults():
    om = OrderMetrics()
    assert om.total_orders_7d == 0
    assert om.revenue_30d == 0.0


def test_dashboard_snapshot_creation():
    snap = DashboardSnapshot()
    assert snap.products == []
    assert snap.raw_pages == {}


def test_daily_report_creation():
    report = DailyReport(report_date="2024-01-01", supplier_name="Test Supplier")
    assert report.top_performing_products == []
    assert report.business_strategies == []
    assert report.action_items == []
