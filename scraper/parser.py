"""Parsers for Jobright job cards and job detail pages."""

from __future__ import annotations

import hashlib
import re
from typing import Optional

from core.models import JobListing


def normalize_text(value: Optional[str]) -> str:
    """Normalize whitespace in extracted text."""
    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip()


def make_link_hash(link: str) -> str:
    """Create a stable hash for a job URL."""
    return hashlib.sha256(link.encode("utf-8")).hexdigest()


async def parse_job_card(
    card,
    search_keyword: str = "",
) -> Optional[JobListing]:
    """
    Parse a Jobright job card using async Playwright.
    """

    try:
        # ---------------------------------------------------------
        # Title
        # ---------------------------------------------------------
        title_element = card.locator("h2").first

        if await title_element.count() == 0:
            return None

        title = normalize_text(await title_element.inner_text())

        if not title:
            return None

        # ---------------------------------------------------------
        # Job link
        # ---------------------------------------------------------
        link_element = card.locator('a[href^="/jobs/info/"]').first

        if await link_element.count() == 0:
            return None

        href = await link_element.get_attribute("href")

        if not href:
            return None

        href = href.strip()

        if href.startswith("/"):
            link = f"https://jobright.ai{href}"
        else:
            link = href

        link_hash = make_link_hash(link)

        # ---------------------------------------------------------
        # Company
        # ---------------------------------------------------------
        company = ""

        try:
            # First attempt:
            # Try extracting company information from the job card.
            title_parent = title_element.locator("..")

            company_candidates = title_parent.locator("xpath=following-sibling::*[1]")

            if await company_candidates.count() > 0:
                company_text = normalize_text(
                    await company_candidates.first.inner_text()
                )

                if company_text:
                    lines = [
                        normalize_text(line)
                        for line in company_text.split("\n")
                        if normalize_text(line)
                    ]

                    if lines:
                        company = lines[0]

        except Exception:
            pass

        # ---------------------------------------------------------
        # Location
        # ---------------------------------------------------------
        location = ""

        try:
            location_icon = card.locator('svg[aria-label="position"]').first

            if await location_icon.count() > 0:
                location_parent = location_icon.locator("..")

                location_text = normalize_text(await location_parent.inner_text())

                if location_text:
                    location = location_text

        except Exception:
            pass

        # ---------------------------------------------------------
        # Metadata
        # ---------------------------------------------------------
        job_type = ""
        salary_range = ""
        work_model = ""
        employment_type = ""

        # ---------------------------------------------------------
        # Job type
        # ---------------------------------------------------------
        try:
            icon = card.locator('svg[aria-label="time"]').first

            if await icon.count() > 0:
                parent = icon.locator("..")

                job_type = normalize_text(await parent.inner_text())

        except Exception:
            pass

        # ---------------------------------------------------------
        # Salary
        # ---------------------------------------------------------
        try:
            icon = card.locator('svg[aria-label="money"]').first

            if await icon.count() > 0:
                parent = icon.locator("..")

                salary_range = normalize_text(await parent.inner_text())

        except Exception:
            pass

        # ---------------------------------------------------------
        # Work model
        # ---------------------------------------------------------
        try:
            icon = card.locator('svg[aria-label="remote"]').first

            if await icon.count() > 0:
                parent = icon.locator("..")

                work_model = normalize_text(await parent.inner_text())

        except Exception:
            pass

        # ---------------------------------------------------------
        # Experience level
        # ---------------------------------------------------------
        try:
            icon = card.locator('svg[aria-label="seniority"]').first

            if await icon.count() > 0:
                parent = icon.locator("..")

                employment_type = normalize_text(await parent.inner_text())

        except Exception:
            pass

        return JobListing(
            title=title,
            company=company,
            location=location,
            link=link,
            link_hash=link_hash,
            source="jobright",
            description="",
            salary_range=salary_range,
            job_type=job_type,
            employment_type=employment_type,
            work_model=work_model,
            work_auth="",
            search_keyword=search_keyword,
        )

    except Exception:
        return None


def extract_company(text: str) -> str:
    """
    Extract company name from Jobright detail-page text.

    Jobright detail pages contain patterns such as:

        Original Job Post Capital One · Reposted 6 minutes ago

    or:

        Original Job Post Motorola Solutions · Reposted 8 minutes ago
    """

    if not text:
        return ""

    patterns = [
        r"Original Job Post\s+(.+?)\s+·",
        r"Original Job Post\s+(.+?)\s+\u00b7",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            company = normalize_text(match.group(1))

            if company:
                return company

    return ""


def extract_salary(text: str) -> str:
    """Extract a salary range from detail-page text."""

    if not text:
        return ""

    patterns = [
        r"\$[\d,]+(?:\.\d+)?\s*[-–]\s*\$[\d,]+(?:\.\d+)?",
        r"\$[\d,]+(?:\.\d+)?\s*(?:/year|/yr|per year)",
        r"\$[\d,]+(?:\.\d+)?",
        r"[\d,]+(?:\.\d+)?\s*[-–]\s*[\d,]+\s*(?:USD|US\$)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return normalize_text(match.group(0))

    return ""


def extract_job_type(text: str) -> str:
    """Extract normalized job type."""

    if not text:
        return ""

    patterns = [
        ("Full-time", r"\bfull[- ]time\b"),
        ("Part-time", r"\bpart[- ]time\b"),
        ("Contract", r"\bcontract\b"),
        ("Internship", r"\binternship\b"),
    ]

    for label, pattern in patterns:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return label

    return ""


def extract_work_model(text: str) -> str:
    """Extract normalized work model."""

    if not text:
        return ""

    if re.search(
        r"\bremote\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "Remote"

    if re.search(
        r"\bhybrid\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "Hybrid"

    if re.search(
        r"\bonsite\b|\bon-site\b|\bin office\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "Onsite"

    return ""


def extract_employment_type(text: str) -> str:
    """Extract experience level."""

    if not text:
        return ""

    patterns = [
        (
            "Intern/New Grad",
            r"\bintern(?:ship)?\b|\bnew grad(?:uate)?\b",
        ),
        (
            "Entry Level",
            r"\bentry[- ]level\b",
        ),
        (
            "Mid Level",
            r"\bmid[- ]level\b",
        ),
        (
            "Senior Level",
            r"\bsenior[- ]level\b|\bsenior\b",
        ),
        (
            "Lead/Staff",
            r"\blead\b|\bstaff\b",
        ),
        (
            "Director/Executive",
            r"\bdirector\b|\bexecutive\b",
        ),
    ]

    for label, pattern in patterns:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return label

    return ""


def extract_work_authorization(text: str) -> str:
    """Extract work authorization / sponsorship information."""

    if not text:
        return ""

    patterns = [
        (
            "H1B Sponsor Likely",
            r"\bH-?1B Sponsor Likely\b",
        ),
        (
            "No H1B",
            r"\bNo H-?1B\b",
        ),
        (
            "U.S. Citizen Only",
            r"\bU\.?S\.? Citizen Only\b",
        ),
        (
            "Security Clearance Required",
            r"\bSecurity Clearance Required\b",
        ),
        (
            "Visa Sponsorship Available",
            r"\bVisa Sponsorship Available\b",
        ),
        (
            "Visa Sponsorship Not Available",
            r"\bVisa Sponsorship Not Available\b",
        ),
        (
            "Work Authorization Required",
            r"\bWork Authorization Required\b",
        ),
    ]

    for label, pattern in patterns:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return label

    return ""


def parse_detail_text(
    text: str,
    job: JobListing,
) -> JobListing:
    """
    Enrich a JobListing using text extracted from the detail page.
    """

    text = normalize_text(text)

    if not text:
        return job

    # ---------------------------------------------------------
    # Company
    # ---------------------------------------------------------
    company = extract_company(text)

    if company:
        job.company = company

    # ---------------------------------------------------------
    # Salary
    # ---------------------------------------------------------
    salary = extract_salary(text)

    if salary:
        job.salary_range = salary

    # ---------------------------------------------------------
    # Job type
    # ---------------------------------------------------------
    job_type = extract_job_type(text)

    if job_type:
        job.job_type = job_type

    # ---------------------------------------------------------
    # Work model
    # ---------------------------------------------------------
    work_model = extract_work_model(text)

    if work_model:
        job.work_model = work_model

    # ---------------------------------------------------------
    # Experience level
    # ---------------------------------------------------------
    employment_type = extract_employment_type(text)

    if employment_type:
        job.employment_type = employment_type

    # ---------------------------------------------------------
    # Work authorization
    # ---------------------------------------------------------
    work_auth = extract_work_authorization(text)

    if work_auth:
        job.work_auth = work_auth

    # ---------------------------------------------------------
    # Full description
    # ---------------------------------------------------------
    job.description = text

    return job
