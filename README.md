# Jobright Scraper

A configurable Playwright-based scraper for collecting Jobright job listings.

## Setup

From `D:\Jobright-scraper`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
```

Set `JOBRIGHT_EMAIL` and `JOBRIGHT_PASSWORD` in `.env`, or run `python -m auth.setup_session`
with a visible browser to save a reusable session. Do not commit `.env` or
`auth/auth_state.json`.

## Run

```powershell
python main.py
```

Results are written to `output/jobs.json`. Search settings are controlled with
the environment variables in `.env.example`.

Jobright may change its markup or authentication flow. If that happens, update
the selectors in `auth/login.py` and `scraper/parser.py`.

