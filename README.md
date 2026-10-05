# Jobright Scraper

A Python-based job scraper built for Jobright using Playwright for browser automation. The scraper searches Jobright using configurable keywords, locations, and filters, extracts job listings and detailed job information, and exports the results as structured CSV data.

---

## What This Does

- Searches Jobright for jobs based on configurable keywords such as "Software Engineer", "Backend Developer", etc.
- Applies filters like country, job type, experience level, and work model
- Handles Jobright's virtualized job list using automated scrolling
- Collects job listings while avoiding duplicate URLs
- Opens individual job pages to extract additional information
- Extracts company, location, salary, job type, experience level, work model, work authorization, and description
- Exports all scraped jobs to a CSV file in the `output/` folder
- Reuses an authenticated browser session so login is not required for every run

---

## Project Structure

```text
Jobright-scraper/
├── auth/
│   └── login.py              # Manual login flow — saves authenticated session
│
├── config/
│   ├── config.py             # Environment-based scraper configuration
│   ├── constants.py          # Jobright URLs and scraper constants
│   └── auth_state.json       # Saved browser authentication state (local only)
│
├── core/
│   ├── models.py             # JobListing dataclass
│   └── state_manager.py      # Scraper state and progress tracking
│
├── scraper/
│   ├── browser_client.py     # Playwright browser management
│   ├── detail_scraper.py     # Job detail page handling
│   ├── parser.py             # Job card and detail-page parsing
│   ├── scraper_manager.py    # Main scraping workflow
│   └── url_builder.py        # Jobright URL construction
│
├── exporter/
│   └── data_exporter.py      # CSV export
│
├── logs/                     # Scraper logs
├── output/                   # Generated CSV files
├── main.py                   # Entry point
├── requirements.txt
├── .gitignore
└── README.md
```

> **Note:** `config/auth_state.json` contains authentication data and should never be committed to GitHub.

---

## How It Works

### Discovery Phase

The first step was inspecting Jobright's job listing page and understanding how the jobs are rendered.

Jobright uses a React-based interface with a **virtualized job list**. This means only a portion of the jobs are present in the DOM at a time.

Because of this, simply reading the page HTML does not provide all available jobs.

The scraper therefore uses Playwright to interact with the page and progressively scroll through the job list.

---

### How Scraping Works

The scraping process works in the following stages:

1. Browser opens the Jobright jobs page
2. Configured country and job filters are applied
3. The search keyword is entered
4. The scraper identifies the virtualized job-list container
5. The container is progressively scrolled
6. Job cards currently present in the DOM are parsed
7. Unique job URLs are stored
8. Scraping continues until the configured `max_jobs` limit is reached
9. Each collected job page is opened for detailed information
10. The extracted information is parsed into a `JobListing`
11. Jobs are exported to CSV

---

### Virtualized Job List

Jobright does not expose all jobs in the DOM simultaneously.

The scraper therefore:

1. Finds the nearest scrollable job-list container
2. Scrolls the container using Playwright
3. Waits for newly rendered job cards
4. Extracts unique job URLs
5. Keeps track of jobs already collected
6. Stops when the requested number of jobs has been reached or no new jobs appear

This allows the scraper to collect jobs beyond the initially visible cards.

---

### Job Card Parsing

Each visible Jobright card is parsed to extract fields such as:

```text
title
company
location
link
link_hash
job_type
salary_range
employment_type
work_model
search_keyword
```

The `parser.py` module maps these values into the `JobListing` model.

---

### Detail Page Extraction

After collecting the job cards, the scraper opens each job's detail page.

The detail page is used to extract additional information such as:

```text
company
salary_range
job_type
employment_type
work_model
work_auth
description
```

The company name is extracted from Jobright's detail-page text, for example:

```text
Original Job Post Capital One · Reposted ...
```

which is parsed as:

```text
Capital One
```

This provides a more reliable company value when the company is not available directly from the job card.

---

## Filters

The scraper supports Jobright filters including:

- Country
- Job Type
- Experience Level
- Work Model

Example configuration:

```env
JOBRIGHT_KEYWORDS=Software Engineer
JOBRIGHT_MAX_JOBS=20

JOBRIGHT_COUNTRIES=US

JOBRIGHT_JOB_TYPES=Full-time
JOBRIGHT_SENIORITY=Senior Level
JOBRIGHT_WORK_MODELS=Remote,Hybrid,Onsite
```

Multiple values can be provided where supported.

---

## Data Fields Collected

| Field | Status | Notes |
|---|---|---|
| `title` | ✅ Populated | Job title |
| `company` | ✅ Populated | Company name |
| `location` | ✅ Populated | Job location |
| `link` | ✅ Populated | Direct Jobright job URL |
| `link_hash` | ✅ Populated | SHA-256 hash of the job URL |
| `source` | ✅ Populated | Always `jobright` |
| `description` | ✅ Populated | Full detail-page text |
| `salary_range` | ✅ Populated | Salary information when available |
| `job_type` | ✅ Populated | Full-time / Part-time / Contract / Internship |
| `employment_type` | ✅ Populated | Intern/New Grad / Entry Level / Mid Level / Senior Level etc. |
| `work_model` | ✅ Populated | Remote / Hybrid / Onsite |
| `work_auth` | ✅ Populated | Work authorization information when available |
| `search_keyword` | ✅ Populated | Keyword used for the search |

---

## Authentication

Jobright requires an authenticated browser session for the scraper workflow.

Run:

```bash
python auth/login.py
```

The login script opens the browser and allows you to log in manually.

After authentication, the session is saved to:

```text
config/auth_state.json
```

The scraper reuses this authentication state on subsequent runs.

**Important:** Never commit `auth_state.json` to GitHub.

---

## Setup and Running

### Requirements

- Python 3.11+
- Playwright
- A Jobright account

### Installation

```bash
# Clone or download the project
cd Jobright-scraper

# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

---

### Running

First authenticate:

```bash
python auth/login.py
```

Then run the scraper:

```bash
python main.py
```

---

## Configuration

Configuration is controlled through the `.env` file.

Example:

```env
JOBRIGHT_BASE_URL=https://jobright.ai
JOBRIGHT_JOBS_URL=https://jobright.ai/jobs/recommend

JOBRIGHT_KEYWORDS=Software Engineer
JOBRIGHT_MAX_JOBS=20

JOBRIGHT_COUNTRIES=US

JOBRIGHT_JOB_TYPES=Full-time
JOBRIGHT_SENIORITY=Senior Level
JOBRIGHT_WORK_MODELS=Remote,Hybrid,Onsite

JOBRIGHT_HEADLESS=false
JOBRIGHT_SLOW_MO_MS=0
JOBRIGHT_TIMEOUT_MS=30000
JOBRIGHT_SCROLL_STEP=700
JOBRIGHT_SCROLL_WAIT_MS=3000
JOBRIGHT_MAX_NO_NEW_ROUNDS=4

JOBRIGHT_OUTPUT=output/jobright_jobs.csv
JOBRIGHT_STORAGE_STATE=config/auth_state.json
JOBRIGHT_LOG_LEVEL=INFO
```

---

## Output

Scraped jobs are saved to:

```text
output/
└── jobright_jobs.csv
```

The CSV contains the structured job information collected during the run.

Example:

```text
title,company,location,link,link_hash,source,description,salary_range,job_type,employment_type,work_model,work_auth,search_keyword
```

---

## Tech Stack

- **Python 3.11+**
- **Playwright** — browser automation
- **Python-dotenv** — environment configuration
- **CSV** — structured job output
- **Jobright** — job listing source

---

## Known Limitations

- Jobright uses a virtualized job list, so scraping depends on correctly identifying and scrolling the list container.
- Some jobs may not provide salary information.
- Work authorization information may not be available for every job.
- Jobright's UI and DOM structure may change, which can require selector updates.
- Authentication state must remain valid for authenticated scraping.

---

## References

- [Jobright](https://jobright.ai)
- [Playwright Python Documentation](https://playwright.dev/python/)