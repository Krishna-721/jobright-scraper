"""Playwright browser client for Jobright."""

import logging
from contextlib import asynccontextmanager

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)

from core.config import ScraperConfig
from core.state_manager import StateManager


LOGGER = logging.getLogger(__name__)


class BrowserClient:
    """Manage Playwright browser and authenticated context."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.state_manager = StateManager(config)

        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def start(self) -> Page:
        """Start the browser and return an authenticated page."""

        self.state_manager.validate()

        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo_ms,
        )

        self.context = await self.browser.new_context(
            storage_state=str(self.config.storage_state_path),
            viewport={
                "width": 1440,
                "height": 900,
            },
        )

        self.context.set_default_timeout(self.config.timeout_ms)

        self.page = await self.context.new_page()

        LOGGER.info("Browser started.")

        return self.page

    async def close(self) -> None:
        """Close browser resources."""

        if self.context:
            await self.context.close()

        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

        LOGGER.info("Browser closed.")

    @asynccontextmanager
    async def session(self):
        """Provide an authenticated browser session."""

        page = await self.start()

        try:
            yield page
        finally:
            await self.close()
