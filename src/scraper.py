"""Asynchronous dynamic web scraper powered by Playwright."""

from __future__ import annotations

import logging
from typing import List, Optional
from urllib.parse import urljoin

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from src.models import ScrapedProduct

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL: str = "https://books.toscrape.com/"
DEFAULT_USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT_MS: int = 10000  # 10s explicit timeout


class DynamicScraper:
    """Production-grade asynchronous web scraper using Playwright Chromium."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        headless: bool = True,
    ) -> None:
        """Initialize scraper settings.

        Args:
            base_url: Entry point URL for scraping.
            user_agent: Believable user-agent header string.
            timeout_ms: Explicit timeout in milliseconds for operations.
            headless: Whether to run Chromium in headless mode.
        """
        self.base_url: str = base_url
        self.user_agent: str = user_agent
        self.timeout_ms: int = timeout_ms
        self.headless: bool = headless

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def __aenter__(self) -> DynamicScraper:
        """Asynchronous context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        """Asynchronous context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Launch Playwright instance, Chromium browser, and isolated context."""
        logger.info("Initializing Playwright Chromium browser (headless=%s)...", self.headless)
        self._playwright = await async_playwright().start()

        launch_kwargs = {
            "headless": self.headless,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"],
        }

        try:
            self._browser = await self._playwright.chromium.launch(**launch_kwargs)
        except Exception as err:
            err_summary = str(err).splitlines()[0] if str(err) else "Driver not available"
            logger.info("Standard Chromium driver not found (%s). Falling back to system Chrome...", err_summary)
            try:
                self._browser = await self._playwright.chromium.launch(channel="chrome", **launch_kwargs)
            except Exception as chrome_err:
                chrome_summary = str(chrome_err).splitlines()[0] if str(chrome_err) else "Chrome not available"
                logger.info("System Chrome launch failed (%s). Falling back to Microsoft Edge...", chrome_summary)
                self._browser = await self._playwright.chromium.launch(channel="msedge", **launch_kwargs)

        self._context = await self._browser.new_context(
            user_agent=self.user_agent,
            viewport={"width": 1280, "height": 800},
        )
        self._context.set_default_timeout(self.timeout_ms)
        self._context.set_default_navigation_timeout(self.timeout_ms)
        logger.info("Browser session initialized successfully.")

    async def close(self) -> None:
        """Gracefully terminate context, browser, and Playwright instances."""
        logger.info("Closing browser resources...")
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Scraper closed.")

    async def _extract_product(self, card_locator, page_url: str) -> Optional[ScrapedProduct]:
        """Extract and validate single product data safely from an element locator."""
        try:
            # Title & Product Link
            title_node = card_locator.locator("h3 a")
            raw_title = await title_node.get_attribute("title", timeout=2000)
            if not raw_title:
                raw_title = await title_node.inner_text(timeout=2000)

            href = await title_node.get_attribute("href", timeout=2000)
            full_product_url = urljoin(page_url, href) if href else None

            # Price
            price_node = card_locator.locator(".product_price .price_color")
            raw_price = await price_node.inner_text(timeout=2000)

            # Rating from CSS class (e.g., 'star-rating Three')
            rating_node = card_locator.locator("p.star-rating")
            rating_class = await rating_node.get_attribute("class", timeout=2000)
            raw_rating: Optional[str] = None
            if rating_class:
                classes = rating_class.split()
                if len(classes) > 1:
                    raw_rating = classes[1]

            # Availability
            avail_node = card_locator.locator(".product_price .instock.availability")
            raw_avail = await avail_node.inner_text(timeout=2000) if await avail_node.count() > 0 else "In stock"

            # Parse through Pydantic v2 schema
            return ScrapedProduct(
                title=raw_title,
                price=raw_price,
                rating=raw_rating,
                availability=raw_avail,
                product_url=full_product_url,
            )
        except Exception as exc:
            logger.warning("Error parsing product card on %s: %s", page_url, exc)
            return None

    async def scrape(self, max_pages: int = 2) -> List[ScrapedProduct]:
        """Scrape products iteratively handling pagination up to max_pages.

        Args:
            max_pages: Maximum number of pages to crawl (>= 1).

        Returns:
            List of validated ScrapedProduct instances.
        """
        if not self._context:
            await self.start()

        assert self._context is not None, "Browser context not active."
        page: Page = await self._context.new_page()

        scraped_products: List[ScrapedProduct] = []
        current_url: Optional[str] = self.base_url
        page_counter: int = 0

        try:
            while current_url and page_counter < max_pages:
                page_counter += 1
                logger.info(
                    "Navigating to page %d/%d: %s",
                    page_counter,
                    max_pages,
                    current_url,
                )

                try:
                    response = await page.goto(
                        current_url,
                        wait_until="commit",
                        timeout=self.timeout_ms,
                    )
                    if not response or response.status >= 400:
                        logger.error(
                            "Failed to load page %s with HTTP status %s",
                            current_url,
                            response.status if response else "NO_RESPONSE",
                        )
                        break

                    # Wait for product container to appear
                    await page.wait_for_selector("article.product_pod", timeout=self.timeout_ms)
                except Exception as nav_err:
                    logger.error("Navigation timeout or error on %s: %s", current_url, nav_err)
                    break

                # Locate product cards
                product_cards = page.locator("article.product_pod")
                card_count = await product_cards.count()
                logger.info("Found %d product elements on page %d.", card_count, page_counter)

                page_extracted = 0
                for idx in range(card_count):
                    card = product_cards.nth(idx)
                    product = await self._extract_product(card, current_url)
                    if product:
                        scraped_products.append(product)
                        page_extracted += 1

                logger.info(
                    "Extracted %d valid products from page %d (total so far: %d).",
                    page_extracted,
                    page_counter,
                    len(scraped_products),
                )

                # Pagination: look for next button
                next_btn = page.locator("li.next a")
                if page_counter < max_pages and await next_btn.count() > 0:
                    next_href = await next_btn.get_attribute("href")
                    if next_href:
                        current_url = urljoin(page.url, next_href)
                    else:
                        logger.info("Next button has no href attribute. Stopping pagination.")
                        current_url = None
                else:
                    logger.info("Reached end of pagination or max_pages limit (%d).", max_pages)
                    current_url = None

        finally:
            await page.close()

        logger.info(
            "Scraping completed. Extracted %d total products across %d page(s).",
            len(scraped_products),
            page_counter,
        )
        return scraped_products
