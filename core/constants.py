"""Jobright scraper constants."""

BASE_URL = "https://jobright.ai"
JOBS_URL = f"{BASE_URL}/jobs/recommend"

SOURCE_NAME = "jobright"

# ---------------------------------------------------------------------------
# Job list
# ---------------------------------------------------------------------------

JOB_CARD_SELECTOR = '[data-tut="jobs-card-match-score"]'
JOB_LINK_SELECTOR = 'a[href^="/jobs/info/"]'
JOB_TITLE_SELECTOR = "h2"

SEARCH_INPUT_SELECTOR = (
    'input[placeholder="Search by title or company"]'
)

# Jobright currently uses a virtualized list.
JOB_LIST_SELECTOR = ".index_jobs-list-scrollable__oMkUx"

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

FILTER_DROPDOWN_SELECTOR = ".index_filter-dropdown__O2Gxc"

COUNTRY_FILTER = "country"
JOB_TYPE_FILTER = "jobTypes"
SENIORITY_FILTER = "seniority"
WORK_MODEL_FILTER = "workModel"

FILTER_SELECTOR_TEMPLATE = (
    '[data-preference-key="{preference_key}"] '
    'button[data-topbar-kind="selector"]'
)

ALL_FILTERS_BUTTON_SELECTOR = (
    'button[data-tut="jobs-card-edit-button"]'
)

# ---------------------------------------------------------------------------
# Job-card metadata icons
# ---------------------------------------------------------------------------

POSITION_ICON = "position"
SALARY_ICON = "money"
JOB_TYPE_ICON = "time"
WORK_MODEL_ICON = "remote"
SENIORITY_ICON = "seniority"
DATE_ICON = "date"

# ---------------------------------------------------------------------------
# Detail pages
# ---------------------------------------------------------------------------

DETAIL_URL_PREFIX = f"{BASE_URL}/jobs/info/"

# ---------------------------------------------------------------------------
# Scraping defaults
# ---------------------------------------------------------------------------

DEFAULT_MAX_JOBS = 500
DEFAULT_SCROLL_STEP = 700
DEFAULT_SCROLL_WAIT_MS = 3000
DEFAULT_MAX_NO_NEW_ROUNDS = 4

DEFAULT_TIMEOUT_MS = 30000
DEFAULT_HEADLESS = False