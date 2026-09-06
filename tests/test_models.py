"""Unit tests for ScrapedProduct Pydantic schema and validators."""

import pytest
from pydantic import ValidationError

from src.models import ScrapedProduct


class TestScrapedProductModel:
    """Test suite for data validation and schema integrity in ScrapedProduct."""

    def test_valid_product_creation(self) -> None:
        """Test instantiation with perfectly formatted valid data."""
        product = ScrapedProduct(
            title="A Light in the Attic",
            price=51.77,
            rating=3.0,
            availability=True,
            product_url="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        )
        assert product.title == "A Light in the Attic"
        assert product.price == 51.77
        assert product.rating == 3.0
        assert product.availability is True
        assert product.product_url == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"

    def test_whitespace_stripping(self) -> None:
        """Test that title, price strings, and URLs have surrounding whitespace stripped."""
        product = ScrapedProduct(
            title="   Tipping the Velvet \n  ",
            price="  £53.74  ",
            rating="Two",
            availability="  In stock  ",
            product_url="   https://books.toscrape.com/product/123   ",
        )
        assert product.title == "Tipping the Velvet"
        assert product.price == 53.74
        assert product.rating == 2.0
        assert product.availability is True
        assert product.product_url == "https://books.toscrape.com/product/123"

    def test_price_string_with_currency_symbols(self) -> None:
        """Test numeric price extraction from currency strings."""
        product = ScrapedProduct(
            title="Book Title",
            price="£23.99",
        )
        assert product.price == 23.99

        product_usd = ScrapedProduct(title="Book Title", price="$1,299.50")
        assert product_usd.price == 1299.50

    def test_price_must_be_positive_or_zero(self) -> None:
        """Test that negative prices trigger a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScrapedProduct(title="Negative Book", price="-10.50")
        assert "Price must be greater than or equal to 0.0" in str(exc_info.value)

        with pytest.raises(ValidationError):
            ScrapedProduct(title="Negative Book", price=-5.0)

        # Zero is valid
        product_free = ScrapedProduct(title="Free Book", price=0.0)
        assert product_free.price == 0.0

    def test_corrupt_price_string(self) -> None:
        """Test non-numeric price string triggers ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScrapedProduct(title="Corrupt Book", price="NotANumber")
        assert "Could not parse numeric price" in str(exc_info.value)

    def test_empty_or_none_title_raises_validation_error(self) -> None:
        """Test missing or whitespace-only title raises ValidationError."""
        with pytest.raises(ValidationError):
            ScrapedProduct(title="   ", price=10.0)

        with pytest.raises(ValidationError):
            ScrapedProduct(title=None, price=10.0)  # type: ignore[arg-type]

    def test_rating_text_mapping(self) -> None:
        """Test textual star rating mapping to float scores."""
        test_cases = [
            ("One", 1.0),
            ("Two", 2.0),
            ("Three", 3.0),
            ("Four", 4.0),
            ("Five", 5.0),
            (4.5, 4.5),
            (None, None),
            ("", None),
        ]
        for raw, expected in test_cases:
            prod = ScrapedProduct(title="Test", price=1.0, rating=raw)
            assert prod.rating == expected

    def test_rating_out_of_bounds_raises_error(self) -> None:
        """Test that ratings outside 0.0 - 5.0 raise ValidationError."""
        with pytest.raises(ValidationError):
            ScrapedProduct(title="Test", price=1.0, rating=6.0)

        with pytest.raises(ValidationError):
            ScrapedProduct(title="Test", price=1.0, rating=-0.5)

    def test_availability_parsing(self) -> None:
        """Test conversion of availability strings to boolean."""
        in_stock_samples = ["In stock (22 available)", "Available", "true", "yes", True]
        for sample in in_stock_samples:
            prod = ScrapedProduct(title="Test", price=10.0, availability=sample)
            assert prod.availability is True

        out_of_stock_samples = ["Out of stock", "Unavailable", "false", "no", False]
        for sample in out_of_stock_samples:
            prod = ScrapedProduct(title="Test", price=10.0, availability=sample)
            assert prod.availability is False
