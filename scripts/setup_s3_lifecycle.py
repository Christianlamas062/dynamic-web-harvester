#!/usr/bin/env python3
"""Script to configure lifecycle policies on Amazon S3 bucket for data retention."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.storage import S3DataSink

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("setup_s3_lifecycle")


def main() -> None:
    sink = S3DataSink()
    logger.info("Applying lifecycle configuration to bucket '%s'...", sink.bucket_name)
    try:
        sink.configure_lifecycle_policy(
            prefix="raw/",
            transition_days=30,
            expiration_days=90,
            storage_class="GLACIER",
        )
        logger.info("S3 Lifecycle Configuration completed successfully.")
    except Exception as exc:
        logger.error("Failed to apply S3 lifecycle configuration: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
