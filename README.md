# 🛍️ Meesho Supplier AI Agent

> An autonomous multi-agent system that logs into your Meesho Supplier Portal, scrapes all business metrics, generates AI-powered insights, produces a beautiful PDF report, and emails it to you — every day on autopilot.

---

## ✨ What It Does

| Agent | Responsibility |
|-------|---------------|
| **BrowserAgent** | Logs into `supplier.meesho.com`, navigates every section (dashboard, products, orders, payments), and scrapes all data using Playwright + LLM-powered DOM parsing |
| **AnalysisAgent** | Sends the raw data to Claude/GPT-4 for deep analysis — ranks products, flags pricing issues, identifies dead SKUs, and generates ecommerce strategies |
| **ReportAgent** | Renders a pixel-perfect HTML/PDF report, saves it locally, and emails it to you via SMTP |

### Report Sections
- 📊 **Business Performance** – Revenue, orders, AOV (7-day & 30-day)
- 🏥 **Account Health** – Rating, cancellation rate, return rate, dispatch/quality scores, penalties
- 🏆 **Top Performing Products** – Best sellers by revenue
- ⚠️ **Worst Performing Products** – Dragging your metrics down
- 💰 **Pricing Recommendations** – AI-suggested price changes with reasoning
- 🗑️ **Products to Remove** – Dead inventory to clean up
- 🚀 **Business Strategies** – Meesho-specific growth tactics
- ✅ **Action Items** – Prioritised to-do list for the day

---

## 🏗️ Architecture

```
meesho_agent/
├── agents/
│   ├── browser_agent.py     # Playwright login + scraping + LLM DOM parsing
│   ├── analysis_agent.py    # LLM-powered business analysis
│   └── report_agent.py      # PDF generation + email sending
├── core/
│   ├── models.py            # Pydantic data models
│   ├── llm.py               # LLM factory (Anthropic / OpenAI)
│   ├── orchestrator.py      # Pipeline: scrape → analyse → report
│   ├── cli.py               # Typer CLI
│   └── logger.py            # Loguru logging
├── config/
│   └── settings.py          # Pydantic Settings (reads .env)
├── templates/
│   └── report.html.j2       # Jinja2 HTML report template
├── tests/
│   ├── test_models.py
│   └── test_report_render.py
├── reports/downloads/        # Auto-created; daily reports saved here
├── logs/                     # Auto-created; rotating log files
├── .env.example
├── pyproject.toml
├── requirements.txt
├── Makefile
├── main.py
├── README.md
└── SETUP.md
```

---

## ⚡ Quick Start

```bash
# 1. Clone and enter project
git clone <repo-url> && cd meesho_agent

# 2. Full setup (installs deps + Playwright Chromium)
make setup

# 3. Configure credentials
nano .env   # Fill in Meesho login, LLM API key, Gmail SMTP

# 4. Verify configuration
make check

# 5. Run!
make run
```

> 📖 For detailed setup instructions, see **[SETUP.md](./SETUP.md)**

---

## 🔧 CLI Commands

```bash
meesho-agent run              # Full pipeline
meesho-agent run --skip-email # Generate report locally only
meesho-agent run --debug      # Show browser window (useful for troubleshooting)
meesho-agent schedule         # Run daily at REPORT_SCHEDULE_TIME
meesho-agent check            # Validate .env configuration
```

Or via Make:

```bash
make run
make run-no-email
make run-debug
make schedule
make check
```

---

## 🤖 LLM Resilience

The BrowserAgent uses an LLM to parse the DOM — this means **even if Meesho redesigns their dashboard**, the agent adapts automatically. Instead of fragile CSS selectors, it sends cleaned HTML to Claude/GPT and asks "what are the revenue metrics on this page?" — getting structured JSON back.

---

## 📧 Email Setup (Gmail)

1. Go to [Google Account → Security → 2-Step Verification](https://myaccount.google.com/security)
2. Enable 2FA (required for App Passwords)
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Create a new App Password for "Mail"
5. Use that 16-character password as `SMTP_PASSWORD` in `.env`

---

## 🔒 Security Notes

- Credentials are stored in `.env` — never commit this file
- `.gitignore` excludes `.env`, `reports/`, and `logs/` automatically
- Playwright runs in headless mode by default; no browser window is visible
- LLM API calls are made server-side; your Meesho data is sent to Anthropic/OpenAI for analysis

---

## 📄 License

MIT License – see LICENSE file.
