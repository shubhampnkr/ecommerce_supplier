"""
CLI entry point – `meesho-agent` command.
"""
from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
app = typer.Typer(name="meesho-agent", help="🛍️  Meesho Supplier AI Agent")


@app.command("run")
def run(
    skip_email: bool = typer.Option(False, "--skip-email", "-n", help="Generate report but don't send email"),
    debug: bool = typer.Option(False, "--debug", help="Show browser window"),
):
    """Run the full pipeline: scrape → analyse → report → email."""
    from core.orchestrator import run_pipeline
    from config.settings import settings

    if debug:
        import os
        os.environ["HEADLESS"] = "false"

    console.print(Panel.fit("🛍️  [bold magenta]Meesho Supplier Agent[/] starting…", border_style="magenta"))

    state = asyncio.run(run_pipeline(skip_email=skip_email))

    if state.success:
        console.print("\n[bold green]✅ Pipeline completed successfully![/]")
        console.print(f"   📄 HTML: [cyan]{state.html_path}[/]")
        console.print(f"   📕 PDF:  [cyan]{state.pdf_path}[/]")
    else:
        console.print("\n[bold red]❌ Pipeline failed![/]")
        for err in state.errors:
            console.print(f"   [red]• {err}[/]")
        raise typer.Exit(code=1)


@app.command("schedule")
def schedule_cmd(
    time: str = typer.Option(None, "--time", "-t", help="HH:MM time (IST). Defaults to REPORT_SCHEDULE_TIME in .env"),
):
    """Schedule the agent to run daily at a specified time."""
    import schedule as sched
    import time as time_module

    from config.settings import settings
    from core.orchestrator import run_pipeline

    run_time = time or settings.report_schedule_time
    console.print(f"⏰ Scheduling daily report at [bold]{run_time} IST[/]")

    def _job():
        console.print(f"[bold]Running scheduled pipeline…[/]")
        asyncio.run(run_pipeline())

    sched.every().day.at(run_time).do(_job)
    console.print("[green]Scheduler started. Press Ctrl+C to stop.[/]")

    while True:
        sched.run_pending()
        time_module.sleep(30)


@app.command("check")
def check():
    """Verify configuration and connectivity."""
    from config.settings import settings

    table = Table(title="Configuration Check", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Status")

    def _mask(s: str) -> str:
        if len(s) > 8:
            return s[:4] + "****" + s[-4:]
        return "****"

    checks = [
        ("Meesho Email", settings.meesho_email, "✅" if settings.meesho_email else "❌"),
        ("Meesho Password", _mask(settings.meesho_password), "✅" if settings.meesho_password else "❌"),
        ("LLM Provider", settings.llm_provider, "✅"),
        ("LLM API Key", _mask(settings.anthropic_api_key or settings.openai_api_key), "✅" if (settings.anthropic_api_key or settings.openai_api_key) else "❌"),
        ("SMTP Host", settings.smtp_host, "✅"),
        ("SMTP User", settings.smtp_username, "✅" if settings.smtp_username else "❌"),
        ("Report Recipient", settings.report_recipient_email, "✅" if settings.report_recipient_email else "❌"),
        ("Report Dir", str(settings.report_download_dir), "✅"),
        ("Schedule Time", settings.report_schedule_time + " IST", "✅"),
        ("Headless Mode", str(settings.headless), "✅"),
    ]

    for name, val, status in checks:
        table.add_row(name, val, status)

    console.print(table)


if __name__ == "__main__":
    app()
