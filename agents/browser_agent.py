"""
BrowserAgent – logs in to Meesho Supplier Portal and scrapes all dashboard data.

Design philosophy:
  • Uses Playwright for robust, headless browser automation.
  • An LLM-based "DOM reader" is invoked after each page load to extract
    structured data from raw HTML – this makes the agent resilient to
    layout/class name changes on the Meesho side.
  • All raw HTML is stored in DashboardSnapshot.raw_pages so the AnalysisAgent
    can re-parse if needed.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from core.logger import logger
from core.llm import get_llm
from core.models import AccountHealth, DashboardSnapshot, OrderMetrics, ProductMetrics


# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

_EXTRACT_PROMPT = """
You are a data extraction assistant. Below is raw HTML (or text) from the Meesho Supplier Portal.
Extract all relevant business metrics and return ONLY a valid JSON object.
Do NOT include markdown fences, explanations, or extra text.

If a field is missing or unclear, use null.
Numbers should be numeric types (not strings).
Dates should be ISO-8601 strings.

Page context: {page_context}

HTML/Text:
{html}

Return JSON matching this schema:
{schema}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Helper: clean & truncate HTML for LLM
# ─────────────────────────────────────────────────────────────────────────────

def _clean_html(html: str, max_chars: int = 12_000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "svg", "path", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Collapse blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:max_chars]


# ─────────────────────────────────────────────────────────────────────────────
# BrowserAgent
# ─────────────────────────────────────────────────────────────────────────────

class BrowserAgent:
    """
    Playwright + LLM agent that logs in to Meesho and extracts dashboard data.
    """

    def __init__(self) -> None:
        self.llm = get_llm(temperature=0.0)
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def __aenter__(self) -> "BrowserAgent":
        await self._start_browser()
        return self

    async def __aexit__(self, *_) -> None:
        await self._close_browser()

    async def _start_browser(self) -> None:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=settings.headless,
            slow_mo=settings.slow_mo,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            java_script_enabled=True,
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(settings.browser_timeout)
        logger.info("Browser started.")

    async def _close_browser(self) -> None:
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_pw"):
            await self._pw.stop()
        logger.info("Browser closed.")

    # ── LLM extraction ───────────────────────────────────────────────────────

    async def _llm_extract(self, html: str, page_context: str, schema: str) -> dict[str, Any]:
        """Ask the LLM to extract structured data from raw HTML."""
        clean = _clean_html(html)
        prompt = _EXTRACT_PROMPT.format(
            page_context=page_context,
            html=clean,
            schema=schema,
        )
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.llm.invoke(prompt)
            )
            raw = response.content.strip()
            # Strip markdown fences if present
            raw = re.sub(r"^```(?:json)?\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)
        except Exception as exc:
            logger.warning(f"LLM extraction failed for '{page_context}': {exc}")
            return {}

    # ── Login ─────────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def login(self) -> bool:
        page = self._page
        logger.info("Navigating to Meesho Supplier Portal login page…")
        await page.goto(settings.meesho_login_url, wait_until="networkidle")

        # Wait for either phone/email field
        await page.wait_for_selector("input[type='text'], input[type='email'], input[type='tel']", timeout=15_000)

        html = await page.content()
        # Use LLM to identify the login form fields
        login_schema = '{"email_selector": "CSS selector for email/phone input", "password_selector": "CSS selector for password input", "submit_selector": "CSS selector for submit/login button"}'
        selectors = await self._llm_extract(html, "Login page", login_schema)

        email_sel = selectors.get("email_selector", "input[type='text']")
        pwd_sel = selectors.get("password_selector", "input[type='password']")
        submit_sel = selectors.get("submit_selector", "button[type='submit']")

        # Fill credentials
        await page.fill(email_sel, settings.meesho_email)
        await page.wait_for_timeout(500)

        # Handle OTP/password flow – click next if needed
        try:
            next_btn = page.locator("button:has-text('Next'), button:has-text('Continue')")
            if await next_btn.count() > 0:
                await next_btn.first.click()
                await page.wait_for_timeout(1500)
        except Exception:
            pass

        await page.fill(pwd_sel, settings.meesho_password)
        await page.wait_for_timeout(300)
        await page.click(submit_sel)

        # Wait for redirect
        await page.wait_for_url("**/dashboard**", timeout=30_000)
        logger.info("Login successful ✓")
        return True

    # ── Page scrapers ────────────────────────────────────────────────────────

    async def _scrape_dashboard_home(self) -> dict[str, Any]:
        page = self._page
        logger.info("Scraping dashboard home…")
        await page.goto(settings.meesho_dashboard_url, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        html = await page.content()

        schema = """{
  "supplier_name": "string",
  "supplier_id": "string",
  "total_orders_7d": "number",
  "total_orders_30d": "number",
  "revenue_7d": "number",
  "revenue_30d": "number",
  "pending_orders": "number",
  "shipped_orders": "number",
  "delivered_orders": "number",
  "cancelled_orders": "number",
  "avg_order_value": "number",
  "supplier_rating": "number",
  "cancellation_rate_pct": "number",
  "return_rate_pct": "number",
  "dispatch_score": "number",
  "quality_score": "number",
  "account_status": "string"
}"""
        data = await self._llm_extract(html, "Supplier dashboard home page", schema)
        data["_raw_html"] = html
        return data

    async def _scrape_products(self) -> list[dict[str, Any]]:
        """Navigate to products/catalogue section and extract all products."""
        page = self._page
        logger.info("Scraping product catalogue…")

        # Try common Meesho catalogue URLs
        catalogue_urls = [
            "https://supplier.meesho.com/product-listing",
            "https://supplier.meesho.com/catalogue",
            "https://supplier.meesho.com/products",
        ]

        products_data: list[dict] = []

        for url in catalogue_urls:
            try:
                await page.goto(url, wait_until="networkidle", timeout=20_000)
                await page.wait_for_timeout(2000)
                html = await page.content()

                schema = """[{
  "product_id": "string",
  "product_name": "string",
  "sku": "string",
  "category": "string",
  "price": "number",
  "mrp": "number",
  "discount_pct": "number",
  "units_sold_7d": "number",
  "units_sold_30d": "number",
  "revenue_7d": "number",
  "revenue_30d": "number",
  "returns_7d": "number",
  "return_rate_pct": "number",
  "rating": "number",
  "review_count": "number",
  "inventory": "number",
  "impressions_7d": "number",
  "clicks_7d": "number",
  "ctr_pct": "number",
  "conversion_rate_pct": "number",
  "is_active": "boolean"
}]"""
                extracted = await self._llm_extract(html, "Product catalogue listing page", schema)

                if isinstance(extracted, list) and extracted:
                    products_data = extracted
                    logger.info(f"Extracted {len(products_data)} products from {url}")
                    break
                elif isinstance(extracted, dict) and "products" in extracted:
                    products_data = extracted["products"]
                    break

            except Exception as exc:
                logger.debug(f"URL {url} failed: {exc}")
                continue

        # Scroll / paginate if needed
        if not products_data:
            logger.warning("Could not extract product data; returning empty list.")

        return products_data

    async def _scrape_orders(self) -> dict[str, Any]:
        """Scrape orders section for detailed order metrics."""
        page = self._page
        logger.info("Scraping orders section…")

        order_urls = [
            "https://supplier.meesho.com/orders",
            "https://supplier.meesho.com/order-management",
        ]

        for url in order_urls:
            try:
                await page.goto(url, wait_until="networkidle", timeout=20_000)
                await page.wait_for_timeout(2000)
                html = await page.content()

                schema = """{
  "total_orders_7d": "number",
  "total_orders_30d": "number",
  "revenue_7d": "number",
  "revenue_30d": "number",
  "pending_orders": "number",
  "shipped_orders": "number",
  "delivered_orders": "number",
  "cancelled_orders": "number",
  "return_orders": "number",
  "avg_order_value": "number"
}"""
                data = await self._llm_extract(html, "Orders management page", schema)
                if data:
                    return data
            except Exception as exc:
                logger.debug(f"Orders URL {url} failed: {exc}")

        return {}

    async def _scrape_payments(self) -> dict[str, Any]:
        """Scrape payment/settlement section."""
        page = self._page
        logger.info("Scraping payments section…")
        try:
            await page.goto("https://supplier.meesho.com/payments", wait_until="networkidle", timeout=20_000)
            await page.wait_for_timeout(2000)
            html = await page.content()
            schema = """{
  "pending_settlement": "number",
  "last_settlement_amount": "number",
  "last_settlement_date": "string",
  "total_settled_30d": "number",
  "penalty_amount": "number",
  "active_penalties": ["string"]
}"""
            return await self._llm_extract(html, "Payments and settlements page", schema)
        except Exception as exc:
            logger.debug(f"Payments scrape failed: {exc}")
            return {}

    # ── Main entry point ─────────────────────────────────────────────────────

    async def run(self) -> DashboardSnapshot:
        """Full scrape pipeline: login → scrape all sections → return snapshot."""
        snapshot = DashboardSnapshot()

        await self.login()

        # Home dashboard
        home_data = await self._scrape_dashboard_home()
        snapshot.supplier_name = home_data.get("supplier_name", "")
        snapshot.supplier_id = home_data.get("supplier_id", settings.meesho_supplier_id)
        snapshot.raw_pages["dashboard_home"] = home_data.pop("_raw_html", "")

        # Order metrics
        order_data = {**home_data, **await self._scrape_orders()}
        snapshot.order_metrics = OrderMetrics(
            total_orders_7d=order_data.get("total_orders_7d", 0),
            total_orders_30d=order_data.get("total_orders_30d", 0),
            revenue_7d=order_data.get("revenue_7d", 0.0),
            revenue_30d=order_data.get("revenue_30d", 0.0),
            pending_orders=order_data.get("pending_orders", 0),
            shipped_orders=order_data.get("shipped_orders", 0),
            delivered_orders=order_data.get("delivered_orders", 0),
            cancelled_orders=order_data.get("cancelled_orders", 0),
            return_orders=order_data.get("return_orders", 0),
            avg_order_value=order_data.get("avg_order_value", 0.0),
        )

        # Account health
        payment_data = await self._scrape_payments()
        snapshot.account_health = AccountHealth(
            supplier_rating=home_data.get("supplier_rating", 0.0),
            cancellation_rate_pct=home_data.get("cancellation_rate_pct", 0.0),
            return_rate_pct=home_data.get("return_rate_pct", 0.0),
            dispatch_score=home_data.get("dispatch_score", 0.0),
            quality_score=home_data.get("quality_score", 0.0),
            penalty_amount=payment_data.get("penalty_amount", 0.0),
            active_penalties=payment_data.get("active_penalties", []),
            account_status=home_data.get("account_status", "active"),
        )

        # Products
        raw_products = await self._scrape_products()
        snapshot.products = [ProductMetrics(**p) for p in raw_products if p.get("product_id")]

        logger.info(
            f"Snapshot complete: {len(snapshot.products)} products, "
            f"revenue_30d=₹{snapshot.order_metrics.revenue_30d:,.0f}"
        )
        return snapshot
