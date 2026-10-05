"""Jobright data models."""

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class JobListing:
    """Normalized job listing."""

    title: str = ""
    company: str = ""
    location: str = ""

    link: str = ""
    link_hash: str = ""

    source: str = "jobright"

    description: str = ""
    salary_range: str = ""

    job_type: str = ""
    employment_type: str = ""

    work_model: str = ""

    work_auth: str = ""
    
    search_keyword: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert the model to a dictionary."""
        return asdict(self)