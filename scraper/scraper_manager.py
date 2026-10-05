"""Jobright scraping orchestration."""

import logging

from playwright.async_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from core.config import ScraperConfig
from core.constants import (
    COUNTRY_FILTER,
    FILTER_DROPDOWN_SELECTOR,
    FILTER_SELECTOR_TEMPLATE,
    JOB_CARD_SELECTOR,
    JOB_TYPE_FILTER,
    SEARCH_INPUT_SELECTOR,
    SENIORITY_FILTER,
    WORK_MODEL_FILTER,
)
from core.models import JobListing

from scraper.parser import parse_job_card
from scraper.url_builder import URLBuilder


LOGGER = logging.getLogger(__name__)


class ScraperManager:
    """Coordinate the complete Jobright scraping workflow."""

    def __init__(
        self,
        page: Page,
        config: ScraperConfig,
    ):
        self.page = page
        self.config = config

        self.url_builder = URLBuilder(
            config.base_url,
            config.jobs_url,
        )

    # ==================================================================
    # Navigation
    # ==================================================================

    async def open_jobs_page(self) -> None:
        """Open the Jobright jobs page and dismiss blocking UI."""

        await self.page.goto(
            self.url_builder.jobs_page(),
            wait_until="domcontentloaded",
        )

        # Give Jobright time to render its client-side UI.
        await self.page.wait_for_timeout(2500)

        if "/jobs/" not in self.page.url:
            raise RuntimeError("Jobright authentication appears to have failed.")

        await self.dismiss_popups()

        LOGGER.info("Jobright jobs page opened.")

    # ==================================================================
    # Popup handling
    # ==================================================================

    async def dismiss_popups(self) -> None:
        """
        Dismiss Jobright promotional/modal overlays.

        Jobright may show Product Updates or other dialogs immediately
        after loading the jobs page. These overlays can prevent filter
        buttons from being clicked.
        """

        # --------------------------------------------------------------
        # First attempt: Escape
        # --------------------------------------------------------------

        try:
            await self.page.keyboard.press("Escape")
            await self.page.wait_for_timeout(300)
        except Exception:
            pass

        # --------------------------------------------------------------
        # Standard dialogs
        # --------------------------------------------------------------

        dialogs = self.page.locator('[role="dialog"]')
        dialog_count = await dialogs.count()

        for index in range(
            dialog_count - 1,
            -1,
            -1,
        ):
            dialog = dialogs.nth(index)

            try:
                if not await dialog.is_visible():
                    continue

                # ------------------------------------------------------
                # Explicit close buttons
                # ------------------------------------------------------

                close_buttons = dialog.locator(
                    'button[aria-label*="close" i], '
                    'button[title*="close" i], '
                    '[data-testid*="close" i]'
                )

                close_count = await close_buttons.count()

                if close_count > 0:
                    for close_index in range(
                        close_count - 1,
                        -1,
                        -1,
                    ):
                        button = close_buttons.nth(close_index)

                        try:
                            if await button.is_visible():
                                await button.click(timeout=3000)
                                await self.page.wait_for_timeout(500)
                                break
                        except Exception:
                            continue

                    continue

                # ------------------------------------------------------
                # Product Updates fallback
                # ------------------------------------------------------

                buttons = dialog.locator("button")
                button_count = await buttons.count()

                if button_count > 0:
                    button = buttons.first

                    try:
                        if await button.is_visible():
                            await button.click(timeout=3000)
                            await self.page.wait_for_timeout(500)
                    except Exception:
                        pass

            except Exception as exc:
                LOGGER.debug(
                    "Could not dismiss dialog %d: %s",
                    index,
                    exc,
                )

        # --------------------------------------------------------------
        # Additional generic overlays
        # --------------------------------------------------------------

        overlay_selectors = [
            '[data-testid*="modal" i]',
            '[data-testid*="dialog" i]',
            '[class*="modal" i]',
            '[class*="dialog" i]',
        ]

        for selector in overlay_selectors:
            try:
                elements = self.page.locator(selector)
                count = await elements.count()

                for index in range(count - 1, -1, -1):
                    element = elements.nth(index)

                    try:
                        if not await element.is_visible():
                            continue

                        close_button = element.locator(
                            'button[aria-label*="close" i], button[title*="close" i]'
                        ).first

                        if await close_button.count() > 0:
                            if await close_button.is_visible():
                                await close_button.click(timeout=2000)
                                await self.page.wait_for_timeout(300)

                    except Exception:
                        continue

            except Exception:
                continue

        # --------------------------------------------------------------
        # Final Escape
        # --------------------------------------------------------------

        try:
            await self.page.keyboard.press("Escape")
        except Exception:
            pass

        await self.page.wait_for_timeout(300)

    # ==================================================================
    # Filter diagnostics
    # ==================================================================

    async def _log_filter_diagnostics(
        self,
        preference_key: str,
    ) -> None:
        """
        Log the current Jobright filter DOM.

        This is intentionally diagnostic. Jobright frequently changes
        its React-rendered filter elements, so this gives us useful
        information instead of another unexplained timeout.
        """

        LOGGER.warning(
            "Running diagnostics for Jobright filter: %s",
            preference_key,
        )

        try:
            elements = self.page.locator("[data-preference-key]")

            count = await elements.count()

            LOGGER.warning(
                "Found %d [data-preference-key] elements.",
                count,
            )

            for index in range(count):
                element = elements.nth(index)

                try:
                    key = await element.get_attribute("data-preference-key")

                    text = (await element.inner_text()).strip()

                    LOGGER.warning(
                        "Preference[%d] key=%r text=%r",
                        index,
                        key,
                        text[:250],
                    )

                except Exception:
                    continue

        except Exception as exc:
            LOGGER.warning(
                "Could not inspect preference elements: %s",
                exc,
            )

        # --------------------------------------------------------------
        # Inspect the requested preference element specifically
        # --------------------------------------------------------------

        try:
            preference = self.page.locator(
                f'[data-preference-key="{preference_key}"]'
            ).first

            if await preference.count() > 0:
                LOGGER.warning(
                    "Requested preference '%s' exists.",
                    preference_key,
                )

                try:
                    html = await preference.evaluate("(element) => element.outerHTML")

                    LOGGER.warning(
                        "Preference '%s' HTML:\n%s",
                        preference_key,
                        html[:12000],
                    )

                except Exception as exc:
                    LOGGER.warning(
                        "Could not read preference HTML: %s",
                        exc,
                    )

            else:
                LOGGER.warning(
                    "Requested preference '%s' does NOT exist in the current DOM.",
                    preference_key,
                )

        except Exception as exc:
            LOGGER.warning(
                "Could not inspect requested preference: %s",
                exc,
            )

        # --------------------------------------------------------------
        # Inspect dropdown candidates
        # --------------------------------------------------------------

        dropdown_selectors = [
            FILTER_DROPDOWN_SELECTOR,
            '[class*="filter-dropdown"]',
            '[role="dialog"]',
        ]

        for selector in dropdown_selectors:
            try:
                candidates = self.page.locator(selector)
                count = await candidates.count()

                if count == 0:
                    continue

                LOGGER.warning(
                    "Selector %r matched %d element(s).",
                    selector,
                    count,
                )

                for index in range(count):
                    candidate = candidates.nth(index)

                    try:
                        if not await candidate.is_visible():
                            continue

                        text = (await candidate.inner_text()).strip()

                        LOGGER.warning(
                            "Visible candidate %d text:\n%s",
                            index,
                            text[:3000],
                        )

                    except Exception:
                        continue

            except Exception:
                continue

    # ==================================================================
    # Filter handling
    # ==================================================================

    async def _get_filter_button(
        self,
        preference_key: str,
    ):
        """
        Locate a Jobright filter button.

        Primary selector:
            [data-preference-key="..."]
            button[data-topbar-kind="selector"]

        Fallback:
            Any visible button inside the preference element.

        The fallback is important because Jobright has changed the
        internal button attributes while keeping data-preference-key.
        """

        # --------------------------------------------------------------
        # Primary selector
        # --------------------------------------------------------------

        selector = FILTER_SELECTOR_TEMPLATE.format(preference_key=preference_key)

        button = self.page.locator(selector).first

        if await button.count() > 0:
            try:
                if await button.is_visible():
                    return button
            except Exception:
                pass

        # --------------------------------------------------------------
        # Fallback selector
        # --------------------------------------------------------------

        preference = self.page.locator(
            f'[data-preference-key="{preference_key}"]'
        ).first

        if await preference.count() == 0:
            return None

        buttons = preference.locator("button")
        button_count = await buttons.count()

        for index in range(button_count):
            candidate = buttons.nth(index)

            try:
                if await candidate.is_visible():
                    return candidate
            except Exception:
                continue

        return None

    async def _find_filter_dropdown(self):
        """Locate the currently visible Jobright filter dropdown."""
        selectors = [
            'div[class*="filter-dropdown"]:not([class*="filter-dropdown-title"])',
            FILTER_DROPDOWN_SELECTOR,
        ]

        for selector in selectors:
            locator = self.page.locator(selector)
            count = await locator.count()

            for index in range(count - 1, -1, -1):
                candidate = locator.nth(index)
                try:
                    if not await candidate.is_visible():
                        continue
                    controls = candidate.locator(
                        'input[type="checkbox"], input[type="radio"], '
                        'button:has-text("Confirm")'
                    )
                    if await controls.count() > 0:
                        return candidate
                except Exception:
                    continue
        return None

    async def open_filter(
        self,
        preference_key: str,
    ):
        """
        Open one Jobright top-bar filter.

        Jobright re-renders the filter UI dynamically. Therefore:

        1. Popups are dismissed.
        2. The button is located again for every attempt.
        3. The dropdown is located after the click.
        4. If opening fails, DOM diagnostics are logged.
        """

        LOGGER.info(
            "Opening Jobright filter: %s",
            preference_key,
        )

        await self.dismiss_popups()

        for attempt in range(1, 4):
            try:
                # ------------------------------------------------------
                # Reacquire button
                # ------------------------------------------------------

                button = await self._get_filter_button(preference_key)

                if button is None:
                    LOGGER.warning(
                        "Could not locate filter button for '%s' (attempt %d/3).",
                        preference_key,
                        attempt,
                    )

                    await self.page.wait_for_timeout(500)
                    continue

                # ------------------------------------------------------
                # Scroll button into view
                # ------------------------------------------------------

                try:
                    await button.scroll_into_view_if_needed(timeout=3000)
                except Exception:
                    pass

                # ------------------------------------------------------
                # Click
                # ------------------------------------------------------

                LOGGER.debug(
                    "Clicking filter '%s' (attempt %d/3).",
                    preference_key,
                    attempt,
                )

                try:
                    await button.click(timeout=5000)

                except Exception:
                    # React can replace the element between locating
                    # and clicking. Reacquire it and try once more.
                    LOGGER.debug(
                        "Normal click failed for '%s'; reacquiring button.",
                        preference_key,
                    )

                    button = await self._get_filter_button(preference_key)

                    if button is None:
                        raise RuntimeError("Filter button disappeared during click.")

                    await button.click(
                        timeout=5000,
                        force=True,
                    )

                # ------------------------------------------------------
                # Wait for dropdown
                # ------------------------------------------------------

                await self.page.wait_for_timeout(300)

                for _ in range(10):
                    dropdown = await self._find_filter_dropdown()

                    if dropdown is not None:
                        LOGGER.info(
                            "Successfully opened filter: %s",
                            preference_key,
                        )

                        return dropdown

                    await self.page.wait_for_timeout(300)

                raise RuntimeError("Filter button clicked, but no dropdown appeared.")

            except Exception as exc:
                LOGGER.warning(
                    "Opening filter '%s' failed (attempt %d/3): %s",
                    preference_key,
                    attempt,
                    exc,
                )

                await self.dismiss_popups()
                await self.page.wait_for_timeout(700)

        # --------------------------------------------------------------
        # We have exhausted retries.
        # --------------------------------------------------------------

        await self._log_filter_diagnostics(preference_key)

        raise RuntimeError(f"Could not open Jobright filter: {preference_key}")

    async def confirm_filter(self) -> None:
        """Confirm the currently open Jobright filter."""

        selectors = [
            f'{FILTER_DROPDOWN_SELECTOR} button:has-text("Confirm")',
            '[class*="filter-dropdown"] button:has-text("Confirm")',
            'button:has-text("Confirm")',
        ]

        for attempt in range(1, 4):
            for selector in selectors:
                try:
                    buttons = self.page.locator(selector)
                    count = await buttons.count()

                    for index in range(
                        count - 1,
                        -1,
                        -1,
                    ):
                        button = buttons.nth(index)

                        try:
                            if not await button.is_visible():
                                continue

                            await button.click(timeout=3000)

                            await self.page.wait_for_timeout(700)

                            LOGGER.debug("Filter confirmed.")

                            return

                        except Exception:
                            continue

                except Exception:
                    continue

            await self.page.wait_for_timeout(500)

        raise RuntimeError("Could not confirm Jobright filter.")

    async def select_country(
        self,
        country_code: str,
    ) -> None:
        """Select the Jobright country."""

        await self.open_filter(COUNTRY_FILTER)

        dropdown = await self._find_filter_dropdown()

        if dropdown is None:
            raise RuntimeError("Country dropdown disappeared after opening.")

        radio = dropdown.locator(f'input[type="radio"][value="{country_code}"]')

        if await radio.count() == 0:
            raise RuntimeError(f"Country '{country_code}' was not found.")

        try:
            await radio.check()
        except Exception:
            # Reacquire after React re-render.
            radio = self.page.locator(
                f"{FILTER_DROPDOWN_SELECTOR} "
                f'input[type="radio"][value="{country_code}"]'
            ).last

            await radio.check()

        await self.confirm_filter()

        LOGGER.info(
            "Country selected: %s",
            country_code,
        )

    async def select_filter_values(
        self,
        preference_key: str,
        values: list[str],
    ) -> None:
        """Set the requested values for a Jobright checkbox filter.

        Jobright uses Ant Design checkbox inputs inside a stable
        ``index_filter-dropdown__...`` container. React may re-render the
        checkbox immediately after a click, so labels are used for the click
        target and the DOM is reacquired after every change.
        """

        if not values:
            LOGGER.debug("Skipping empty filter: %s", preference_key)
            return

        await self.open_filter(preference_key)

        label_aliases = {
            "remote": "Remote anywhere in the US",
        }

        def normalize(value: str) -> str:
            return " ".join(value.split()).casefold()

        requested = {
            normalize(label_aliases.get(value.strip().casefold(), value.strip()))
            for value in values
            if value.strip()
        }

        dropdown = await self._find_filter_dropdown()
        if dropdown is None:
            raise RuntimeError(
                f"Could not locate dropdown for filter '{preference_key}'."
            )

        # Read the options once. The labels are the stable user-facing
        # controls; checkbox inputs can be replaced by React after a click.
        labels = dropdown.locator("label.ant-checkbox-wrapper")
        label_count = await labels.count()

        if label_count == 0:
            # Fallback for a possible future class-name change.
            labels = dropdown.locator('input[type="checkbox"]').locator(
                "xpath=ancestor::label[1]"
            )
            label_count = await labels.count()

        if label_count == 0:
            LOGGER.warning(
                "No checkbox options found for filter '%s'.",
                preference_key,
            )
            try:
                html = await dropdown.evaluate("element => element.outerHTML")
                LOGGER.warning(
                    "Filter '%s' dropdown HTML:\n%s",
                    preference_key,
                    html[:10000],
                )
            except Exception:
                pass
            await self.confirm_filter()
            return

        found_requested: set[str] = set()

        for index in range(label_count):
            # Reacquire the current label because React may have replaced it.
            dropdown = await self._find_filter_dropdown()
            if dropdown is None:
                raise RuntimeError(
                    f"Dropdown disappeared while applying '{preference_key}'."
                )

            labels = dropdown.locator("label.ant-checkbox-wrapper")
            if await labels.count() == 0:
                labels = dropdown.locator('input[type="checkbox"]').locator(
                    "xpath=ancestor::label[1]"
                )

            if index >= await labels.count():
                continue

            label = labels.nth(index)
            try:
                option_text = " ".join((await label.inner_text()).split())
                normalized_option = normalize(option_text)
                if not normalized_option:
                    continue

                desired = normalized_option in requested
                checkbox = label.locator('input[type="checkbox"]').first

                if await checkbox.count() == 0:
                    continue

                currently_checked = await checkbox.is_checked()

                if desired:
                    found_requested.add(normalized_option)

                if desired and not currently_checked:
                    # Click the label rather than the hidden/native input.
                    # This is how the Ant Design control is intended to be
                    # toggled and avoids React state races.
                    await label.click(timeout=3000)
                    LOGGER.info(
                        "Checked %s option: %s",
                        preference_key,
                        option_text,
                    )

                elif not desired and currently_checked:
                    await label.click(timeout=3000)
                    LOGGER.info(
                        "Unchecked %s option: %s",
                        preference_key,
                        option_text,
                    )

                # Give React a moment to commit the checkbox state before the
                # next label is reacquired.
                await self.page.wait_for_timeout(150)

            except Exception as exc:
                LOGGER.warning(
                    "Could not update checkbox %d for '%s': %s",
                    index,
                    preference_key,
                    exc,
                )

        missing = requested - found_requested
        for value in sorted(missing):
            LOGGER.warning(
                "Configured filter option '%s' was not found for '%s'.",
                value,
                preference_key,
            )

        await self.confirm_filter()

        LOGGER.info(
            "Applied %s: %s",
            preference_key,
            ", ".join(values),
        )

    async def apply_filters(
        self,
        country_code: str,
    ) -> None:
        """Apply configured Jobright filters for one country."""

        await self.dismiss_popups()

        # --------------------------------------------------------------
        # Country
        # --------------------------------------------------------------

        await self.select_country(country_code)

        await self.dismiss_popups()

        # --------------------------------------------------------------
        # Job type
        # --------------------------------------------------------------

        await self.select_filter_values(
            JOB_TYPE_FILTER,
            self.config.job_types,
        )

        await self.dismiss_popups()

        # --------------------------------------------------------------
        # Seniority
        # --------------------------------------------------------------

        await self.select_filter_values(
            SENIORITY_FILTER,
            self.config.seniority,
        )

        await self.dismiss_popups()

        # --------------------------------------------------------------
        # Work model
        # --------------------------------------------------------------

        await self.select_filter_values(
            WORK_MODEL_FILTER,
            self.config.work_models,
        )

        await self.page.wait_for_timeout(1000)

        LOGGER.info("All configured filters applied.")

    # ==================================================================
    # Search
    # ==================================================================

    async def search_keyword(
        self,
        keyword: str,
    ) -> None:
        """Search Jobright for one keyword."""

        await self.dismiss_popups()

        search = self.page.locator(SEARCH_INPUT_SELECTOR).first

        await search.wait_for(state="visible")

        await search.fill("")

        await search.fill(keyword)

        await search.press("Enter")

        LOGGER.info(
            "Searching keyword: %s",
            keyword,
        )

        await self.page.wait_for_timeout(self.config.scroll_wait_ms)

    # ==================================================================
    # Job-card collection
    # ==================================================================

    async def collect_visible_jobs(
        self,
        keyword: str,
        jobs: dict[str, JobListing],
        max_jobs: int | None = None,
    ) -> int:
        """Parse currently rendered Jobright cards without exceeding the limit."""

        cards = self.page.locator(JOB_CARD_SELECTOR)

        count = await cards.count()

        added = 0

        if max_jobs is None:
            max_jobs = self.config.max_jobs_per_keyword

        if len(jobs) >= max_jobs:
            return 0

        for index in range(count):
            if len(jobs) >= max_jobs:
                break
            card = cards.nth(index)

            try:
                job = await parse_job_card(
                    card,
                    keyword,
                )

                if not job.link_hash:
                    continue

                if job.link_hash not in jobs:
                    if len(jobs) >= max_jobs:
                        break

                    jobs[job.link_hash] = job
                    added += 1

                    LOGGER.debug(
                        "Collected: %s | %s",
                        job.title,
                        job.company,
                    )

            except Exception as exc:
                LOGGER.debug(
                    "Could not parse job card %d: %s",
                    index,
                    exc,
                )

        return added

    # ==================================================================
    # Virtualized scrolling
    # ==================================================================

    async def scroll_job_list(
        self,
    ) -> bool:
        """
        Scroll the actual Jobright virtualized job list.

        The method finds the nearest scrollable ancestor of a rendered
        job card rather than relying entirely on Jobright's generated
        CSS class names.
        """

        scroll_step = self.config.scroll_step

        result = await self.page.evaluate(
            """
            (scrollStep) => {

                const cards = Array.from(
                    document.querySelectorAll(
                        '[data-tut="jobs-card-match-score"]'
                    )
                );

                if (!cards.length) {
                    return false;
                }

                let element = cards[0].parentElement;

                while (element) {

                    const style =
                        window.getComputedStyle(element);

                    const scrollable =
                        element.scrollHeight >
                        element.clientHeight &&
                        (
                            style.overflowY === 'auto' ||
                            style.overflowY === 'scroll'
                        );

                    if (scrollable) {

                        const before =
                            element.scrollTop;

                        const maximum =
                            element.scrollHeight -
                            element.clientHeight;

                        const target =
                            Math.min(
                                before + scrollStep,
                                maximum
                            );

                        element.scrollTop = target;

                        element.dispatchEvent(
                            new Event(
                                'scroll',
                                {
                                    bubbles: true
                                }
                            )
                        );

                        return (
                            element.scrollTop !== before
                        );
                    }

                    element = element.parentElement;
                }

                return false;
            }
            """,
            scroll_step,
        )

        if result:
            return True

        # --------------------------------------------------------------
        # Fallback: mouse wheel
        # --------------------------------------------------------------

        try:
            await self.page.mouse.wheel(
                0,
                scroll_step,
            )

            return True

        except Exception as exc:
            LOGGER.debug(
                "Fallback mouse scroll failed: %s",
                exc,
            )

            return False

    # ==================================================================
    # Keyword scraping
    # ==================================================================

    async def scrape_keyword(
        self,
        keyword: str,
    ) -> list[JobListing]:
        """Scrape jobs for one keyword across all configured countries."""

        all_country_jobs: dict[str, JobListing] = {}

        for country_code in self.config.countries:
            LOGGER.info(
                "Starting keyword: %s | country: %s",
                keyword,
                country_code,
            )

            # Reload the jobs page for each country so filters start clean.
            await self.open_jobs_page()

            await self.apply_filters(country_code)
            await self.search_keyword(keyword)

            country_jobs: dict[str, JobListing] = {}
            no_new_rounds = 0

            while len(country_jobs) < self.config.max_jobs_per_keyword:
                before = len(country_jobs)

                added = await self.collect_visible_jobs(
                    keyword,
                    country_jobs,
                    max_jobs=self.config.max_jobs_per_keyword,
                )

                after = len(country_jobs)

                LOGGER.info(
                    "Keyword '%s' | country '%s': %d/%d jobs (+%d this round)",
                    keyword,
                    country_code,
                    after,
                    self.config.max_jobs_per_keyword,
                    added,
                )

                if after >= self.config.max_jobs_per_keyword:
                    break

                if after == before:
                    no_new_rounds += 1
                else:
                    no_new_rounds = 0

                if no_new_rounds >= self.config.max_no_new_rounds:
                    LOGGER.info(
                        "No new jobs after %d rounds. "
                        "Stopping keyword '%s' for country '%s'.",
                        no_new_rounds,
                        keyword,
                        country_code,
                    )
                    break

                scrolled = await self.scroll_job_list()

                if not scrolled:
                    LOGGER.info(
                        "Could not scroll further. "
                        "Stopping keyword '%s' for country '%s'.",
                        keyword,
                        country_code,
                    )
                    break

                await self.page.wait_for_timeout(self.config.scroll_wait_ms)

            # Merge country results by link_hash. The same job can appear
            # in multiple countries, especially for remote roles.
            for job in country_jobs.values():
                existing = all_country_jobs.get(job.link_hash)

                if existing:
                    existing_keywords = set(
                        filter(
                            None,
                            existing.search_keyword.split(" | "),
                        )
                    )

                    if job.search_keyword:
                        existing_keywords.add(job.search_keyword)

                    existing.search_keyword = " | ".join(sorted(existing_keywords))
                else:
                    all_country_jobs[job.link_hash] = job

            LOGGER.info(
                "Keyword '%s' | country '%s': finished with %d jobs.",
                keyword,
                country_code,
                len(country_jobs),
            )

        LOGGER.info(
            "Keyword '%s': collected %d unique jobs across countries.",
            keyword,
            len(all_country_jobs),
        )

        return list(all_country_jobs.values())

    async def enrich_job(
        self,
        job: JobListing,
    ) -> JobListing:
        """
        Open a job detail page and enrich the listing.

        The detail parser currently uses rendered page text rather
        than relying on unverified internal Jobright class names.
        """

        from scraper.parser import parse_detail_text

        detail_page = await self.page.context.new_page()

        try:
            await detail_page.goto(
                job.link,
                wait_until="domcontentloaded",
                timeout=self.config.timeout_ms,
            )

            await detail_page.wait_for_timeout(1500)

            body = detail_page.locator("body")

            text = await body.inner_text()

            job = parse_detail_text(
                text,
                job,
            )

        except PlaywrightTimeoutError:
            LOGGER.warning(
                "Timeout loading detail page: %s",
                job.link,
            )

        except Exception as exc:
            LOGGER.warning(
                "Detail extraction failed for %s: %s",
                job.link,
                exc,
            )

        finally:
            await detail_page.close()

        return job

    async def enrich_jobs(
        self,
        jobs: list[JobListing],
    ) -> list[JobListing]:
        """Enrich collected jobs with detail-page information."""

        total = len(jobs)

        LOGGER.info(
            "Starting detail extraction for %d jobs.",
            total,
        )

        enriched: list[JobListing] = []

        for index, job in enumerate(
            jobs,
            start=1,
        ):
            LOGGER.info(
                "Detail %d/%d: %s | %s",
                index,
                total,
                job.title,
                job.company,
            )

            enriched_job = await self.enrich_job(job)

            enriched.append(enriched_job)

        return enriched

    # ==================================================================
    # Full scrape
    # ==================================================================

    async def scrape(
        self,
    ) -> list[JobListing]:
        """Run the complete configured Jobright scrape."""

        all_jobs: dict[str, JobListing] = {}

        # --------------------------------------------------------------
        # Open page
        # --------------------------------------------------------------

        await self.open_jobs_page()

        # --------------------------------------------------------------
        # Search each keyword
        # --------------------------------------------------------------

        for keyword in self.config.keywords:
            jobs = await self.scrape_keyword(keyword)

            for job in jobs:
                existing = all_jobs.get(job.link_hash)

                # ------------------------------------------------------
                # Same job found under multiple keywords
                # ------------------------------------------------------

                if existing:
                    existing_keywords = set(
                        filter(
                            None,
                            existing.search_keyword.split(" | "),
                        )
                    )

                    if job.search_keyword:
                        existing_keywords.add(job.search_keyword)

                    existing.search_keyword = " | ".join(sorted(existing_keywords))

                else:
                    all_jobs[job.link_hash] = job

            LOGGER.info(
                "Total unique jobs after '%s': %d",
                keyword,
                len(all_jobs),
            )

        jobs = list(all_jobs.values())

        LOGGER.info(
            "Collected %d unique jobs.",
            len(jobs),
        )

        # --------------------------------------------------------------
        # Detail extraction
        # --------------------------------------------------------------

        if jobs:
            jobs = await self.enrich_jobs(jobs)

        return jobs
