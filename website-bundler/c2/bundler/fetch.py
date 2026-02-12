import os

from playwright.async_api import async_playwright

from c2.bundler.cors_bypass import handle_route

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SINGLE_FILE_PATH = os.path.join(SCRIPT_DIR, "single-file.js")

async def fetch_page(url: str) -> tuple[str, str]:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()

    await page.route("**/*", handle_route)

    await page.goto(url, wait_until="networkidle")

    with open(SINGLE_FILE_PATH, "r") as f:
        single_file_script = f.read()

    await page.evaluate(single_file_script)

    content = await page.evaluate("singlefile.getPageData()")

    await browser.close()
    await playwright.stop()

    return content['content']