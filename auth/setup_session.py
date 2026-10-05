import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


BASE_DIR = Path(__file__).resolve().parent.parent
AUTH_STATE_PATH = BASE_DIR / "auth" / "auth_state.json"


async def main():
    AUTH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False
        )

        context = await browser.new_context()

        page = await context.new_page()

        await page.goto(
            "https://jobright.ai/jobs/recommend",
            wait_until="domcontentloaded"
        )

        print()
        print("=" * 60)
        print("JOBRIGHT LOGIN")
        print("=" * 60)
        print("Log in using the new account.")
        print("Use the normal email/password login.")
        print()
        print("After you reach the Jobright jobs page,")
        print("come back here and press ENTER.")
        print("=" * 60)

        input("\nPress ENTER after successful login... ")

        await context.storage_state(
            path=str(AUTH_STATE_PATH)
        )

        print()
        print(f"Auth state saved to:")
        print(AUTH_STATE_PATH)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

