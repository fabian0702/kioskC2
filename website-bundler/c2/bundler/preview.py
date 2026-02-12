from playwright.async_api import async_playwright

async def preview_page(url: str) -> bytes:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto(url, wait_until="networkidle")

    screenshot = await page.screenshot()

    await browser.close()
    await playwright.stop()

    return screenshot