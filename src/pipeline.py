"""Data cleaning, deduplication, sorting, and export pipeline using Pandas."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

import pandas as pd

from src.models import ScrapedProduct

logger = logging.getLogger(__name__)

ExportFormat = Literal["csv", "excel"]


class DataPipeline:
    """Processing pipeline for cleaning, deduplicating, and exporting scraped product data."""

    def __init__(self, output_dir: Optional[Path | str] = None) -> None:
        """Initialize pipeline with target output directory.

        Args:
            output_dir: Target directory path for processed files. Defaults to 'data/processed'.
        """
        self.output_dir: Path = Path(output_dir) if output_dir else Path("data/processed")

    def process_products(
        self,
        products: List[ScrapedProduct],
        sort_by: str = "price",
        ascending: bool = True,
    ) -> pd.DataFrame:
        """Transform list of ScrapedProduct into cleaned, deduplicated, and sorted DataFrame.

        Args:
            products: List of validated ScrapedProduct instances.
            sort_by: Column name to sort by. Defaults to 'price'.
            ascending: Sort order direction. Defaults to True (ascending).

        Returns:
            Cleaned and deduplicated pandas DataFrame.
        """
        if not products:
            logger.warning("No products provided to pipeline. Creating empty DataFrame.")
            return pd.DataFrame(
                columns=["title", "price", "rating", "availability", "product_url"]
            )

        logger.info("Ingesting %d products into data processing pipeline.", len(products))
        # Convert Pydantic models to list of dictionaries
        data = [prod.model_dump() for prod in products]
        df = pd.DataFrame(data)

        initial_count = len(df)
        # Deduplicate by title
        df = df.drop_duplicates(subset=["title"], keep="first")
        dropped_count = initial_count - len(df)
        if dropped_count > 0:
            logger.info("Deduplication removed %d duplicate product(s) by title.", dropped_count)
        else:
            logger.info("No duplicate products found.")

        # Sort values
        if sort_by in df.columns:
            logger.info("Sorting %d records by '%s' (ascending=%s).", len(df), sort_by, ascending)
            df = df.sort_values(by=sort_by, ascending=ascending)
        else:
            logger.warning("Sort column '%s' not present in DataFrame. Skipping sort.", sort_by)

        df = df.reset_index(drop=True)
        logger.info("Pipeline transformation finished with %d valid record(s).", len(df))
        return df

    def export(
        self,
        df: pd.DataFrame,
        export_format: ExportFormat = "csv",
        filename_prefix: str = "scraped_products",
        timestamped: bool = True,
    ) -> Path:
        """Export DataFrame to CSV or Excel in the configured output directory.

        Args:
            df: Cleaned pandas DataFrame to export.
            export_format: Target format ('csv' or 'excel').
            filename_prefix: Base filename for output file.
            timestamped: Whether to append timestamp to filename.

        Returns:
            Path object pointing to the generated file.

        Raises:
            ValueError: If an unsupported export format is specified.
        """
        # Ensure output directory exists using pathlib
        self.output_dir.mkdir(parents=True, exist_ok=True)

        normalized_format = export_format.lower().strip()
        timestamp_str = f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}" if timestamped else ""

        if normalized_format == "csv":
            file_path = self.output_dir / f"{filename_prefix}{timestamp_str}.csv"
            logger.info("Exporting %d row(s) to CSV at: %s", len(df), file_path)
            df.to_csv(file_path, index=False, encoding="utf-8")
        elif normalized_format in ("excel", "xlsx"):
            file_path = self.output_dir / f"{filename_prefix}{timestamp_str}.xlsx"
            logger.info("Exporting %d row(s) to Excel at: %s", len(df), file_path)
            df.to_excel(file_path, index=False, engine="openpyxl")
        else:
            raise ValueError(f"Unsupported export format '{export_format}'. Choose 'csv' or 'excel'.")

        file_size_bytes = file_path.stat().st_size
        logger.info(
            "Export complete: '%s' written successfully (Size: %d bytes).",
            file_path.name,
            file_size_bytes,
        )
        return file_path
