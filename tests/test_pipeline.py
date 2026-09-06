"""Unit tests for DataPipeline data transformations and exports."""

from pathlib import Path
from typing import List

import pandas as pd
import pytest

from src.models import ScrapedProduct
from src.pipeline import DataPipeline


@pytest.fixture
def sample_products() -> List[ScrapedProduct]:
    """Sample list of ScrapedProduct instances with duplicates and varied prices."""
    return [
        ScrapedProduct(
            title="Book Alpha",
            price=45.00,
            rating=4.0,
            availability=True,
            product_url="https://example.com/alpha",
        ),
        ScrapedProduct(
            title="Book Beta",
            price=15.50,
            rating=2.0,
            availability=True,
            product_url="https://example.com/beta",
        ),
        ScrapedProduct(
            title="Book Alpha",  # Duplicate title with different price
            price=40.00,
            rating=5.0,
            availability=False,
            product_url="https://example.com/alpha-alt",
        ),
        ScrapedProduct(
            title="Book Gamma",
            price=29.99,
            rating=3.0,
            availability=False,
            product_url="https://example.com/gamma",
        ),
    ]


class TestDataPipeline:
    """Test suite for DataPipeline transformations and file exports."""

    def test_deduplication_by_title(self, sample_products: List[ScrapedProduct], tmp_path: Path) -> None:
        """Verify pipeline drops duplicate entries by title and keeps first occurrence."""
        pipeline = DataPipeline(output_dir=tmp_path)
        df = pipeline.process_products(sample_products, sort_by="title", ascending=True)

        assert len(df) == 3
        assert list(df["title"]) == ["Book Alpha", "Book Beta", "Book Gamma"]
        # Ensure first occurrence was retained (price 45.00)
        alpha_row = df[df["title"] == "Book Alpha"].iloc[0]
        assert alpha_row["price"] == 45.00
        assert alpha_row["rating"] == 4.0

    def test_sorting_by_price_ascending(self, sample_products: List[ScrapedProduct], tmp_path: Path) -> None:
        """Verify sorting records by price ascending."""
        pipeline = DataPipeline(output_dir=tmp_path)
        df = pipeline.process_products(sample_products, sort_by="price", ascending=True)

        prices = list(df["price"])
        assert prices == sorted(prices)
        assert df.iloc[0]["title"] == "Book Beta"
        assert df.iloc[0]["price"] == 15.50

    def test_sorting_by_price_descending(self, sample_products: List[ScrapedProduct], tmp_path: Path) -> None:
        """Verify sorting records by price descending."""
        pipeline = DataPipeline(output_dir=tmp_path)
        df = pipeline.process_products(sample_products, sort_by="price", ascending=False)

        prices = list(df["price"])
        assert prices == sorted(prices, reverse=True)
        assert df.iloc[0]["title"] == "Book Alpha"
        assert df.iloc[0]["price"] == 45.00

    def test_empty_products_handling(self, tmp_path: Path) -> None:
        """Verify processing an empty list returns empty DataFrame with expected columns."""
        pipeline = DataPipeline(output_dir=tmp_path)
        df = pipeline.process_products([])

        assert df.empty
        assert list(df.columns) == ["title", "price", "rating", "availability", "product_url"]

    def test_export_to_csv(self, sample_products: List[ScrapedProduct], tmp_path: Path) -> None:
        """Verify exporting to CSV generates valid file readable by Pandas."""
        pipeline = DataPipeline(output_dir=tmp_path)
        df = pipeline.process_products(sample_products)
        output_file = pipeline.export(df, export_format="csv", filename_prefix="test_export", timestamped=False)

        assert output_file.exists()
        assert output_file.suffix == ".csv"
        assert output_file.name == "test_export.csv"

        # Read back and assert integrity
        df_read = pd.read_csv(output_file)
        assert len(df_read) == 3
        assert set(df_read.columns) == {"title", "price", "rating", "availability", "product_url"}

    def test_export_to_excel(self, sample_products: List[ScrapedProduct], tmp_path: Path) -> None:
        """Verify exporting to Excel generates valid .xlsx file readable by Pandas."""
        pipeline = DataPipeline(output_dir=tmp_path)
        df = pipeline.process_products(sample_products)
        output_file = pipeline.export(df, export_format="excel", filename_prefix="test_export", timestamped=False)

        assert output_file.exists()
        assert output_file.suffix == ".xlsx"
        assert output_file.name == "test_export.xlsx"

        # Read back and assert integrity
        df_read = pd.read_excel(output_file, engine="openpyxl")
        assert len(df_read) == 3
        assert set(df_read.columns) == {"title", "price", "rating", "availability", "product_url"}

    def test_unsupported_export_format_raises_error(self, sample_products: List[ScrapedProduct], tmp_path: Path) -> None:
        """Verify passing an unsupported format raises a ValueError."""
        pipeline = DataPipeline(output_dir=tmp_path)
        df = pipeline.process_products(sample_products)

        with pytest.raises(ValueError) as exc_info:
            pipeline.export(df, export_format="json")  # type: ignore[arg-type]
        assert "Unsupported export format 'json'" in str(exc_info.value)
