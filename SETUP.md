# 🔧 Setup Guide – Meesho Supplier AI Agent

Complete step-by-step instructions for setting up the agent on your local PC (Windows, macOS, Linux).

---

## Prerequisites

Before starting, make sure you have:

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.11+ | `python --version` |
| Git | Any | `git --version` |
| pip | Latest | `pip --version` |

---

## Step 1 – Install Python 3.11+

### Windows
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.11 or 3.12
3. ✅ Check **"Add Python to PATH"** during installation
4. Verify: open Command Prompt → `python --version`

### macOS
```bash
# Using Homebrew (recommended)
brew install python@3.11

# Or download from python.org
```

### Ubuntu / Debian Linux
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip -y
```

---

## Step 2 – Install Poetry

Poetry is the dependency manager used by this project.

```bash
# macOS / Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

After installation, add Poetry to your PATH:

```bash
# macOS / Linux – add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# Then reload shell
source ~/.bashrc   # or source ~/.zshrc
```

Verify: `poetry --version`

---

## Step 3 – Clone / Download the Project

```bash
# If you have git
git clone <your-repo-url>
cd meesho_agent

# Or download ZIP and extract, then:
cd meesho_agent
```

---

## Step 4 – Install Python Dependencies

```bash
# This installs everything from pyproject.toml into a virtual environment
make setup

# OR manually:
poetry install
poetry run playwright install chromium
poetry run playwright install-deps chromium   # Linux only (installs system libs)
```

> ⚠️ On **Ubuntu/Debian**, if `playwright install-deps` fails, run:
> ```bash
> sudo apt install -y libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 \
>   libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2
> ```

---

## Step 5 – Configure Your Credentials

```bash
# Copy the example config
cp .env.example .env

# Open and edit with your details
nano .env          # Linux/macOS
notepad .env       # Windows
```

### Required Fields

```env
# ── Meesho ────────────────────────────────────────
MEESHO_EMAIL=your_supplier_email@gmail.com
MEESHO_PASSWORD=your_meesho_password

# ── LLM (choose one) ──────────────────────────────
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...

# OR
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# ── Email (Gmail recommended) ─────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_gmail@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx    # Gmail App Password (NOT regular password)
REPORT_RECIPIENT_EMAIL=you@gmail.com
```

### Getting Your API Key

**Anthropic (Claude) – Recommended:**
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Settings → API Keys → Create Key
3. Copy the `sk-ant-...` key into `.env`

**OpenAI (GPT-4):**
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create new secret key
3. Copy the `sk-...` key into `.env`

### Getting Gmail App Password

1. Make sure **2-Factor Authentication** is enabled on your Google account
2. Go to: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Select **"Mail"** → **"Other (Custom name)"** → type `Meesho Agent`
4. Click **Generate**
5. Copy the 16-character password (shown once) into `SMTP_PASSWORD`

> ⚠️ **Do NOT use your regular Gmail password** – Google blocks it for SMTP. You must use an App Password.

---

## Step 6 – Verify Configuration

```bash
make check
# or
poetry run meesho-agent check
```

You should see all green ✅ checkmarks. Fix any ❌ items in `.env`.

---

## Step 7 – Test Run (No Email)

Run once with email disabled to verify everything works:

```bash
make run-no-email
# or
poetry run meesho-agent run --skip-email
```

Watch the terminal output. The agent will:
1. Launch a headless Chromium browser
2. Log into supplier.meesho.com
3. Scrape dashboard, products, orders, payments
4. Call Claude/GPT-4 for analysis
5. Generate an HTML + PDF report in `reports/downloads/`

Open `reports/downloads/meesho_report_YYYY-MM-DD.html` in your browser to verify the report looks correct.

---

## Step 8 – Full Run (With Email)

```bash
make run
# or
poetry run meesho-agent run
```

Check your inbox for the report email.

---

## Step 9 – Schedule Daily Reports

To run automatically every day at 8:00 AM IST:

```bash
make schedule
```

Or set a custom time:
```bash
poetry run meesho-agent schedule --time 09:30
```

### Keep the scheduler running 24/7

**Linux / macOS – using `screen` or `nohup`:**
```bash
# Option A: screen (recommended)
screen -S meesho-agent
make schedule
# Detach with Ctrl+A then D
# Reattach with: screen -r meesho-agent

# Option B: nohup
nohup poetry run meesho-agent schedule > logs/scheduler.log 2>&1 &
```

**Linux – using systemd (production):**

Create `/etc/systemd/system/meesho-agent.service`:
```ini
[Unit]
Description=Meesho Supplier Agent
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/meesho_agent
ExecStart=/path/to/meesho_agent/.venv/bin/meesho-agent schedule
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable meesho-agent
sudo systemctl start meesho-agent
sudo systemctl status meesho-agent
```

**Windows – Task Scheduler:**
1. Open Task Scheduler → Create Basic Task
2. Trigger: Daily at 8:00 AM
3. Action: Start a Program
   - Program: `C:\Users\YOU\AppData\Local\pypoetry\venv\Scripts\meesho-agent.exe`
   - Arguments: `run`
   - Start in: `C:\path\to\meesho_agent`

---

## Troubleshooting

### ❌ "Browser not found" / Playwright errors
```bash
poetry run playwright install chromium
# Linux: also run:
poetry run playwright install-deps chromium
```

### ❌ Login fails / "Page timed out"
1. Run with `--debug` flag to see the browser: `make run-debug`
2. Check your Meesho credentials in `.env`
3. Meesho may require OTP verification – check if your account has extra security enabled
4. Try increasing timeout: set `BROWSER_TIMEOUT=120000` in `.env`

### ❌ "API key invalid" / LLM errors
- Verify your API key at the provider's dashboard
- Make sure you have sufficient credits/balance
- Confirm `LLM_PROVIDER` matches which key you've set

### ❌ Email not sending
- Verify you're using a **Gmail App Password**, not your regular password
- Check that 2FA is enabled on your Gmail account
- Try: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`
- Check spam/junk folder for the first email

### ❌ "WeasyPrint" errors (PDF generation)
WeasyPrint requires system libraries. On Linux:
```bash
sudo apt install -y python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0
```

On macOS:
```bash
brew install pango
```

If PDF still fails, the agent falls back to a basic ReportLab PDF and the full report is in the HTML attachment.

### ❌ No product data extracted
The Meesho portal may have changed its UI. The LLM-based parser should adapt, but:
1. Run with `--debug` to see what the browser sees
2. Check `logs/meesho_agent_YYYY-MM-DD.log` for extraction details
3. The agent stores raw HTML in the snapshot – check logs for "Extracted N products"

---

## Directory Structure After Setup

```
meesho_agent/
├── .env                    ← Your credentials (never commit!)
├── reports/
│   └── downloads/
│       ├── meesho_report_2024-06-01.html
│       └── meesho_report_2024-06-01.pdf
└── logs/
    └── meesho_agent_2024-06-01.log
```

---

## Updating the Project

```bash
git pull
poetry install          # Install any new dependencies
make check              # Verify config still valid
```

---

## Running Tests

```bash
make test               # Run all tests
make test-cov           # Tests + HTML coverage report
```

---

## Getting Help

1. Check `logs/meesho_agent_YYYY-MM-DD.log` for detailed errors
2. Run `make run-debug` to see exactly what the browser sees
3. Run `make check` to validate your configuration
4. Set `LOG_LEVEL=DEBUG` in `.env` for verbose output
