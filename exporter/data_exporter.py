"""Export scraped Jobright jobs to CSV."""

import csv
from pathlib import Path

from core.models import JobListing


CSV_FIELDS = [
    "title",
    "company",
    "location",
    "link",
    "link_hash",
    "source",
    "description",
    "salary_range",
    "job_type",
    "employment_type",
    "work_model",
    "work_auth",
    "search_keyword",
]


def _read_existing_jobs(output_path: Path) -> dict[str, dict]:
    """Read existing jobs and index them by link_hash."""

    if not output_path.exists():
        return {}

    jobs: dict[str, dict] = {}

    with output_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            link_hash = (row.get("link_hash") or "").strip()

            if not link_hash:
                continue

            jobs[link_hash] = {field: row.get(field, "") for field in CSV_FIELDS}

    return jobs


def _merge_job(
    existing: dict[str, dict],
    job: JobListing,
) -> None:
    """Insert or update one job using link_hash as the unique key."""

    data = job.to_dict()

    # Only fields present in CSV_FIELDS are written.
    normalized = {field: data.get(field, "") for field in CSV_FIELDS}

    link_hash = normalized["link_hash"]

    if not link_hash:
        return

    # New scrape data replaces the old record for the same job.
    # This allows changed salary/auth/description data to be refreshed.
    existing[link_hash] = normalized


def export_jobs(
    jobs: list[JobListing],
    output_path: Path,
) -> None:
    """
    Merge scraped jobs into the existing CSV.

    Existing jobs are preserved.
    Jobs with the same link_hash are updated instead of duplicated.
    New jobs are appended to the resulting dataset.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing = _read_existing_jobs(output_path)

    for job in jobs:
        _merge_job(existing, job)

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDS,
            extrasaction="ignore",
        )

        writer.writeheader()

        for row in existing.values():
            writer.writerow(row)
