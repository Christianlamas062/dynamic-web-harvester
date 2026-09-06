"""Unit tests for DynamicScraper logic without real network calls."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.scraper import DynamicScraper


class TestDynamicScraperUnit:
    """Test suite for DynamicScraper extraction logic with mocked Playwright locators."""

    def test_scraper_initialization(self) -> None:
        """Test default and custom initialization properties."""
        scraper = DynamicScraper(
            base_url="https://books.toscrape.com/",
            timeout_ms=10000,
            headless=True,
        )
        assert scraper.base_url == "https://books.toscrape.com/"
        assert scraper.timeout_ms == 10000
        assert scraper.headless is True
        assert "Mozilla/5.0" in scraper.user_agent

    @pytest.mark.asyncio
    async def test_extract_product_success(self) -> None:
        """Test _extract_product correctly extracts and validates product from mocked locator."""
        scraper = DynamicScraper()

        # Mock card locator
        card = MagicMock()

        # Mock title node
        title_node = MagicMock()
        title_node.get_attribute = AsyncMock(side_effect=lambda attr, timeout=None: "A Light in the Attic" if attr == "title" else "catalogue/a-light-in-the-attic_1000/index.html")
        title_node.inner_text = AsyncMock(return_value="A Light in the Attic")

        # Mock price node
        price_node = MagicMock()
        price_node.inner_text = AsyncMock(return_value="£51.77")

        # Mock rating node
        rating_node = MagicMock()
        rating_node.get_attribute = AsyncMock(return_value="star-rating Three")

        # Mock availability node
        avail_node = MagicMock()
        avail_node.count = AsyncMock(return_value=1)
        avail_node.inner_text = AsyncMock(return_value="In stock (22 available)")

        def locator_router(selector: str):
            if "h3 a" in selector:
                return title_node
            if "price_color" in selector:
                return price_node
            if "star-rating" in selector:
                return rating_node
            if "instock" in selector:
                return avail_node
            return MagicMock()

        card.locator = MagicMock(side_effect=locator_router)

        product = await scraper._extract_product(card, "https://books.toscrape.com/index.html")

        assert product is not None
        assert product.title == "A Light in the Attic"
        assert product.price == 51.77
        assert product.rating == 3.0
        assert product.availability is True
        assert product.product_url == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"

    @pytest.mark.asyncio
    async def test_extract_product_graceful_on_missing_elements(self) -> None:
        """Test that missing required fields return None gracefully without raising unhandled exceptions."""
        scraper = DynamicScraper()
        card = MagicMock()

        # Title node fails or returns empty
        title_node = MagicMock()
        title_node.get_attribute = AsyncMock(return_value=None)
        title_node.inner_text = AsyncMock(return_value="")

        price_node = MagicMock()
        price_node.inner_text = AsyncMock(return_value="£10.00")

        def locator_router(selector: str):
            if "h3 a" in selector:
                return title_node
            if "price_color" in selector:
                return price_node
            return MagicMock()

        card.locator = MagicMock(side_effect=locator_router)

        # Empty title fails Pydantic validation -> _extract_product catches it and returns None
        product = await scraper._extract_product(card, "https://books.toscrape.com/")
        assert product is None
