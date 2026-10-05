"""Jobright URL construction."""

from urllib.parse import urljoin


class URLBuilder:
    """Build Jobright URLs."""

    def __init__(
        self,
        base_url: str,
        jobs_url: str,
    ):
        self.base_url = base_url.rstrip("/")
        self.jobs_url = jobs_url

    def jobs_page(self) -> str:
        """Return the main Jobright jobs page."""
        return self.jobs_url

    def job_detail(self, href: str) -> str:
        """Convert a relative job URL into an absolute URL."""

        return urljoin(
            self.base_url + "/",
            href,
        )
