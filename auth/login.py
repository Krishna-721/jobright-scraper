"""Create a persistent Jobright authentication session."""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


BASE_DIR = Path(__file__).resolve().parent.parent

AUTH_STATE_PATH = BASE_DIR / "config" / "auth_state.json"

LOGIN_URL = "https://jobright.ai/jobs/recommend"


async def login() -> None:
    """Open Jobright and save the authenticated session."""

    AUTH_STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)

        context = await browser.new_context()

        page = await context.new_page()

        print()
        print("=" * 70)
        print("JOBRIGHT LOGIN")
        print("=" * 70)
        print()
        print("A browser will open.")
        print("Log in to Jobright normally.")
        print()
        print("After you reach the Jobright jobs page,")
        print("return to this terminal and press ENTER.")
        print()
        print("=" * 70)
        print()

        await page.goto(
            LOGIN_URL,
            wait_until="domcontentloaded",
        )

        input("\nPress ENTER after successful login: ")

        await context.storage_state(path=str(AUTH_STATE_PATH))

        print()
        print("Authentication state saved to:")
        print(AUTH_STATE_PATH)
        print()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(login())
