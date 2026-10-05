import logging
import re

from playwright.sync_api import Page

from scraper.parser import clean_text


LOGGER = logging.getLogger(__name__)


def _body_text(page: Page) -> str:
    return clean_text(page.locator("body").inner_text())


def _extract_section(
    page: Page,
    heading_names: list[str],
) -> str:

    for heading_name in heading_names:
        heading = page.get_by_text(
            heading_name,
            exact=True,
        ).first

        if heading.count() == 0:
            continue

        try:
            section = heading.locator("xpath=following-sibling::*[1]")

            text = clean_text(section.inner_text())

            if text:
                return text

        except Exception:
            continue

    return ""


def _extract_labeled_value(
    page: Page,
    labels: list[str],
) -> str:

    for label in labels:
        locator = page.get_by_text(
            re.compile(
                rf"^{re.escape(label)}$",
                re.IGNORECASE,
            )
        ).first

        if locator.count() == 0:
            continue

        try:
            parent = locator.locator("xpath=..")

            text = clean_text(parent.inner_text())

            if text and text.lower() != label.lower():
                return re.sub(
                    rf"^{re.escape(label)}\s*[:\-]?\s*",
                    "",
                    text,
                    flags=re.IGNORECASE,
                ).strip()

        except Exception:
            continue

    return ""


def extract_description(page: Page) -> str:

    description = _extract_section(
        page,
        [
            "Job Description",
            "Job description",
            "Description",
            "Responsibilities",
            "About the role",
        ],
    )

    if description:
        return description

    # Fallback: collect meaningful paragraph/list text
    # while avoiding navigation/buttons.
    elements = page.locator("main p, main li")

    parts = []

    for i in range(elements.count()):
        text = clean_text(elements.nth(i).inner_text())

        if len(text) >= 20:
            parts.append(text)

    return "\n".join(parts)


def extract_work_auth(page: Page) -> str:

    value = _extract_labeled_value(
        page,
        [
            "Work Authorization",
            "Work authorization",
            "Visa Sponsorship",
            "Visa sponsorship",
        ],
    )

    if value:
        return value

    body = _body_text(page)

    patterns = [
        r"(H-?1B[^.\n]{0,200})",
        r"(visa sponsorship[^.\n]{0,200})",
        r"(sponsorship[^.\n]{0,200})",
        r"(authorized to work[^.\n]{0,200})",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            body,
            re.IGNORECASE,
        )

        if match:
            return clean_text(match.group(1))

    return ""


def extract_employment_type(page: Page) -> str:

    return _extract_labeled_value(
        page,
        [
            "Employment Type",
            "Employment type",
            "Job Type",
            "Job type",
        ],
    )


def extract_job_status(page: Page) -> str:

    body = _body_text(page).lower()

    inactive_terms = [
        "job is no longer available",
        "position is no longer available",
        "no longer accepting applications",
        "job has been closed",
        "position has been closed",
    ]

    for term in inactive_terms:
        if term in body:
            return "Inactive"

    apply_buttons = page.get_by_role(
        "button",
        name=re.compile(
            r"apply|easy apply",
            re.IGNORECASE,
        ),
    )

    if apply_buttons.count() > 0:
        return "Active"

    apply_links = page.get_by_role(
        "link",
        name=re.compile(
            r"apply",
            re.IGNORECASE,
        ),
    )

    if apply_links.count() > 0:
        return "Active"

    return "Unknown"


def extract_detail_fields(
    page: Page,
) -> dict:

    return {
        "description": extract_description(page),
        "work_auth": extract_work_auth(page),
        "employment_type": extract_employment_type(page),
        "job_status": extract_job_status(page),
    }


def enrich_job(
    page: Page,
    job,
) -> object:

    page.goto(
        job.link,
        wait_until="domcontentloaded",
    )

    try:
        page.wait_for_load_state(
            "networkidle",
            timeout=10_000,
        )
    except Exception:
        pass

    fields = extract_detail_fields(page)

    job.description = fields["description"]
    job.work_auth = fields["work_auth"]
    job.employment_type = fields["employment_type"]
    job.job_status = fields["job_status"]

    return job
