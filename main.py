"""CLI Entrypoint for Dynamic Web Harvester pipeline."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from src.pipeline import DataPipeline, ExportFormat
from src.scraper import DynamicScraper
from src.storage import S3DataSink

logger = logging.getLogger("dynamic_web_harvester")


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured console logging across the application."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command line interface arguments."""
    parser = argparse.ArgumentParser(
        prog="dynamic-web-harvester",
        description="Production-grade asynchronous web scraping pipeline using Playwright and Pandas.",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=2,
        help="Maximum number of pages to scrape (default: 2)",
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["csv", "excel"],
        default="csv",
        help="Target export format: 'csv' or 'excel' (default: 'csv')",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed",
        help="Destination directory for processed output files (default: 'data/processed')",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity level (default: 'INFO')",
    )

    return parser.parse_args()


async def run_pipeline(
    max_pages: int,
    export_format: ExportFormat,
    output_dir: str,
) -> Path:
    """Execute asynchronous end-to-end extraction and processing pipeline.

    Args:
        max_pages: Maximum pagination limit.
        export_format: File format ('csv' or 'excel').
        output_dir: Output directory path.

    Returns:
        Path to the exported data file.
    """
    logger.info(
        "Starting Dynamic Web Harvester (max_pages=%d, format=%s, output_dir=%s)",
        max_pages,
        export_format,
        output_dir,
    )

    scraper = DynamicScraper()
    async with scraper:
        products = await scraper.scrape(max_pages=max_pages)

    # Persist raw records to S3 after Pydantic validation
    records = [prod.model_dump() for prod in products]
    s3_sink = S3DataSink()
    s3_sink.upload_raw_payload(records)

    pipeline = DataPipeline(output_dir=output_dir)
    df = pipeline.process_products(products=products, sort_by="price", ascending=True)

    if df.empty:
        logger.warning("No products were extracted. Empty file will be generated.")

    output_path = pipeline.export(df=df, export_format=export_format)
    logger.info("Pipeline executed successfully. Output saved to: %s", output_path)
    return output_path


def main() -> None:
    """Application main entrypoint."""
    args = parse_arguments()
    setup_logging(log_level=args.log_level)

    try:
        if args.max_pages < 1:
            logger.error("--max-pages must be at least 1, received: %d", args.max_pages)
            sys.exit(1)

        asyncio.run(
            run_pipeline(
                max_pages=args.max_pages,
                export_format=args.format,
                output_dir=args.output_dir,
            )
        )
    except KeyboardInterrupt:
        logger.warning("Scraping execution interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        logger.exception("Fatal error during harvester execution: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
