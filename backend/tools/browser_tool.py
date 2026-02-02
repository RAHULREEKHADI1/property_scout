from playwright.async_api import async_playwright
import asyncio
import os

class BrowserTool:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
    
    async def start(self, headless=True):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
        await self.page.set_viewport_size({"width": 1280, "height": 720})
    
    async def navigate(self, url: str):
        if not self.page:
            await self.start()
        await self.page.goto(url, wait_until="networkidle")
        await asyncio.sleep(1)
    
    async def type_text(self, selector: str, text: str):
        if not self.page:
            return False
        try:
            await self.page.wait_for_selector(selector, timeout=5000)
            await self.page.fill(selector, text)
            return True
        except:
            return False
    
    async def click(self, selector: str):
        if not self.page:
            return False
        try:
            await self.page.wait_for_selector(selector, timeout=5000)
            await self.page.click(selector)
            await asyncio.sleep(2)
            return True
        except:
            return False
    
    async def screenshot(self, filename: str):
        if not self.page:
            return False
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            await self.page.screenshot(path=filename, full_page=False)
            return True
        except Exception as e:
            print(f"Screenshot error: {e}")
            return False
    
    async def close(self):
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.page = None
        self.browser = None
        self.playwright = None
