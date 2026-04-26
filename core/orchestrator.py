"""
Orchestrator – ties BrowserAgent → AnalysisAgent → ReportAgent together
using a simple async pipeline (LangGraph state machine style).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.logger import logger
from core.models import DailyReport, DashboardSnapshot


@dataclass
class PipelineState:
    snapshot: Optional[DashboardSnapshot] = None
    report: Optional[DailyReport] = None
    html_path: Optional[Path] = None
    pdf_path: Optional[Path] = None
    errors: list[str] = field(default_factory=list)
    success: bool = False


async def run_pipeline(skip_email: bool = False) -> PipelineState:
    """
    Full pipeline:
      1. BrowserAgent  – login + scrape
      2. AnalysisAgent – LLM analysis
      3. ReportAgent   – generate PDF, email
    """
    from agents.browser_agent import BrowserAgent
    from agents.analysis_agent import AnalysisAgent
    from agents.report_agent import ReportAgent

    state = PipelineState()

    # ── Step 1: Scrape ────────────────────────────────────────────────────────
    logger.info("═" * 60)
    logger.info("STEP 1/3 — Browser Agent: scraping Meesho dashboard…")
    logger.info("═" * 60)
    try:
        async with BrowserAgent() as browser:
            state.snapshot = await browser.run()
    except Exception as exc:
        logger.error(f"BrowserAgent failed: {exc}")
        state.errors.append(f"Scraping error: {exc}")
        return state

    # ── Step 2: Analyse ───────────────────────────────────────────────────────
    logger.info("═" * 60)
    logger.info("STEP 2/3 — Analysis Agent: generating insights…")
    logger.info("═" * 60)
    try:
        analysis_agent = AnalysisAgent()
        state.report = await analysis_agent.run(state.snapshot)
    except Exception as exc:
        logger.error(f"AnalysisAgent failed: {exc}")
        state.errors.append(f"Analysis error: {exc}")
        return state

    # ── Step 3: Report ────────────────────────────────────────────────────────
    logger.info("═" * 60)
    logger.info("STEP 3/3 — Report Agent: generating PDF + sending email…")
    logger.info("═" * 60)
    try:
        report_agent = ReportAgent()
        if skip_email:
            html_path, pdf_path = report_agent.save_report(state.report)
        else:
            html_path, pdf_path = await report_agent.run(state.report)
        state.html_path = html_path
        state.pdf_path = pdf_path
    except Exception as exc:
        logger.error(f"ReportAgent failed: {exc}")
        state.errors.append(f"Report/email error: {exc}")
        return state

    state.success = True
    logger.info("✅ Pipeline complete!")
    logger.info(f"   HTML: {state.html_path}")
    logger.info(f"   PDF:  {state.pdf_path}")
    return state
