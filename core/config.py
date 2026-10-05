"""Application configuration for the Jobright scraper."""

from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def csv_list(value: str | None) -> list[str]:
    """Convert a comma-separated environment variable to a list."""
    if not value:
        return []

    return [item.strip() for item in value.split(",") if item.strip()]


def as_bool(
    value: str | None,
    default: bool = False,
) -> bool:
    """Parse a boolean environment variable."""
    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass(frozen=True)
class ScraperConfig:
    """Complete Jobright scraper configuration."""

    # ------------------------------------------------------------------
    # Platform
    # ------------------------------------------------------------------

    base_url: str = "https://jobright.ai"
    jobs_url: str = "https://jobright.ai/jobs/recommend"

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    keywords: list[str] = field(
        default_factory=lambda: [
            "Software Engineer",
            "Backend Engineer",
            "Full Stack Engineer",
        ]
    )

    max_jobs_per_keyword: int = 500

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    countries: list[str] = field(
        default_factory=lambda: [
            "US",
        ]
    )

    job_types: list[str] = field(
        default_factory=lambda: [
            "Full-time",
            "Internship",
        ]
    )

    seniority: list[str] = field(
        default_factory=lambda: [
            "Intern/New Grad",
        ]
    )

    work_models: list[str] = field(
        default_factory=lambda: [
            "Remote",
            "Hybrid",
            "Onsite",
        ]
    )

    # ------------------------------------------------------------------
    # Browser
    # ------------------------------------------------------------------

    headless: bool = False
    slow_mo_ms: int = 0
    timeout_ms: int = 30_000

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------

    scroll_step: int = 700
    scroll_wait_ms: int = 3000
    max_no_new_rounds: int = 4

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    output_path: Path = BASE_DIR / "output" / "jobs.csv"

    storage_state_path: Path = BASE_DIR / "config" / "auth_state.json"

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "ScraperConfig":
        """Build configuration from environment variables."""

        keywords = csv_list(os.getenv("JOBRIGHT_KEYWORDS"))

        if not keywords:
            keywords = [
                "Software Engineer",
                "Backend Engineer",
                "Full Stack Engineer",
            ]

        job_types = csv_list(os.getenv("JOBRIGHT_JOB_TYPES"))

        if not job_types:
            job_types = [
                "Full-time",
                "Internship",
            ]

        seniority = csv_list(os.getenv("JOBRIGHT_SENIORITY"))

        if not seniority:
            seniority = [
                "Intern/New Grad",
            ]

        countries = csv_list(os.getenv("JOBRIGHT_COUNTRIES"))

        if not countries:
            # Backward compatibility with the old single-country setting.
            legacy_country = os.getenv("JOBRIGHT_COUNTRY")
            countries = csv_list(legacy_country)

        if not countries:
            countries = [
                "US",
            ]

        work_models = csv_list(os.getenv("JOBRIGHT_WORK_MODELS"))

        if not work_models:
            work_models = [
                "Remote",
                "Hybrid",
                "Onsite",
            ]

        return cls(
            base_url=os.getenv(
                "JOBRIGHT_BASE_URL",
                cls.base_url,
            ),
            jobs_url=os.getenv(
                "JOBRIGHT_JOBS_URL",
                cls.jobs_url,
            ),
            keywords=keywords,
            max_jobs_per_keyword=int(
                os.getenv(
                    "JOBRIGHT_MAX_JOBS",
                    cls.max_jobs_per_keyword,
                )
            ),
            countries=countries,
            job_types=job_types,
            seniority=seniority,
            work_models=work_models,
            headless=as_bool(
                os.getenv("JOBRIGHT_HEADLESS"),
                cls.headless,
            ),
            slow_mo_ms=int(
                os.getenv(
                    "JOBRIGHT_SLOW_MO_MS",
                    cls.slow_mo_ms,
                )
            ),
            timeout_ms=int(
                os.getenv(
                    "JOBRIGHT_TIMEOUT_MS",
                    cls.timeout_ms,
                )
            ),
            scroll_step=int(
                os.getenv(
                    "JOBRIGHT_SCROLL_STEP",
                    cls.scroll_step,
                )
            ),
            scroll_wait_ms=int(
                os.getenv(
                    "JOBRIGHT_SCROLL_WAIT_MS",
                    cls.scroll_wait_ms,
                )
            ),
            max_no_new_rounds=int(
                os.getenv(
                    "JOBRIGHT_MAX_NO_NEW_ROUNDS",
                    cls.max_no_new_rounds,
                )
            ),
            output_path=Path(
                os.getenv(
                    "JOBRIGHT_OUTPUT",
                    str(cls.output_path),
                )
            ),
            storage_state_path=Path(
                os.getenv(
                    "JOBRIGHT_STORAGE_STATE",
                    str(cls.storage_state_path),
                )
            ),
            log_level=os.getenv(
                "JOBRIGHT_LOG_LEVEL",
                cls.log_level,
            ).upper(),
        )
