"""Jobright scraper entry point."""

import asyncio
import logging

from core.config import ScraperConfig
from scraper.browser_client import BrowserClient
from scraper.scraper_manager import ScraperManager
from exporter.data_exporter import export_jobs


def configure_logging(
    level: str,
) -> None:
    """Configure application logging."""

    logging.basicConfig(
        level=getattr(
            logging,
            level.upper(),
            logging.INFO,
        ),
        format=("%(asctime)s | %(levelname)s | %(name)s | %(message)s"),
    )


async def main() -> None:
    """Run the Jobright scraper."""

    config = ScraperConfig.from_env()

    configure_logging(config.log_level)

    logger = logging.getLogger("jobright_scraper")

    logger.info("Starting Jobright scraper.")

    logger.info(
        "Keywords: %s",
        config.keywords,
    )

    logger.info(
        "Maximum jobs per keyword: %d",
        config.max_jobs_per_keyword,
    )

    browser = BrowserClient(config)

    async with browser.session() as page:
        manager = ScraperManager(
            page,
            config,
        )

        jobs = await manager.scrape()

    export_jobs(
        jobs,
        config.output_path,
    )

    logger.info("Scraping completed.")

    logger.info(
        "Total unique jobs: %d",
        len(jobs),
    )

    logger.info(
        "Output: %s",
        config.output_path,
    )


if __name__ == "__main__":
    asyncio.run(main())
