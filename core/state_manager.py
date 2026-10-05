"""Jobright session/state management."""

import logging
from pathlib import Path

from core.config import ScraperConfig


LOGGER = logging.getLogger(__name__)


class StateManager:
    """Manage persistent Playwright authentication state."""

    def __init__(self, config: ScraperConfig):
        self.config = config

    @property
    def state_path(self) -> Path:
        return self.config.storage_state_path

    def exists(self) -> bool:
        """Return whether an authentication state exists."""
        return self.state_path.exists()

    def validate(self) -> None:
        """Validate that the auth state exists."""
        if not self.exists():
            raise FileNotFoundError(
                "Jobright authentication state was not found.\n"
                f"Expected: {self.state_path}\n\n"
                "Run:\n"
                "    python auth/login.py"
            )

        LOGGER.info(
            "Using Jobright authentication state: %s",
            self.state_path,
        )
