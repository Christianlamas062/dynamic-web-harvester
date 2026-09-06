"""Data models and validation schemas using Pydantic v2."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

RATING_MAP: Dict[str, float] = {
    "zero": 0.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
}


class ScrapedProduct(BaseModel):
    """Product model scraped from web targets with strict validation."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="ignore",
        validate_assignment=True,
    )

    title: str = Field(..., description="Title or name of the product")
    price: float = Field(..., ge=0.0, description="Product price in floating point (must be >= 0.0)")
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0, description="Product rating score (0.0 to 5.0)")
    availability: bool = Field(default=True, description="Flag indicating product in-stock availability")
    product_url: Optional[str] = Field(default=None, description="Absolute canonical URL to the product page")

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v: Any) -> str:
        """Strip whitespaces and ensure title is a non-empty string."""
        if v is None:
            raise ValueError("Product title cannot be None")
        cleaned = str(v).strip()
        if not cleaned:
            raise ValueError("Product title cannot be empty")
        return cleaned

    @field_validator("price", mode="before")
    @classmethod
    def validate_and_clean_price(cls, v: Any) -> float:
        """Parse price from string or number, strip currency symbols, and enforce price >= 0.0."""
        if v is None:
            raise ValueError("Price cannot be None")

        if isinstance(v, (int, float)):
            parsed_price = float(v)
        elif isinstance(v, str):
            cleaned = v.strip()
            # Match first floating-point or integer number in string
            match = re.search(r"[-+]?\d+(?:\.\d+)?", cleaned.replace(",", ""))
            if not match:
                raise ValueError(f"Could not parse numeric price from string: '{v}'")
            parsed_price = float(match.group())
        else:
            raise ValueError(f"Unsupported type for price: {type(v).__name__}")

        if parsed_price < 0.0:
            raise ValueError(f"Price must be greater than or equal to 0.0, got {parsed_price}")

        return round(parsed_price, 2)

    @field_validator("rating", mode="before")
    @classmethod
    def validate_and_map_rating(cls, v: Any) -> Optional[float]:
        """Convert string ratings (e.g., 'Three', 'four') or numeric values to float."""
        if v is None or v == "":
            return None

        if isinstance(v, (int, float)):
            val = float(v)
            if not (0.0 <= val <= 5.0):
                raise ValueError(f"Rating must be between 0.0 and 5.0, got {val}")
            return val

        if isinstance(v, str):
            cleaned = v.strip().lower()
            if cleaned in RATING_MAP:
                return RATING_MAP[cleaned]
            # Try numeric parse if string contains a number
            match = re.search(r"\d+(?:\.\d+)?", cleaned)
            if match:
                val = float(match.group())
                if 0.0 <= val <= 5.0:
                    return val
                raise ValueError(f"Rating must be between 0.0 and 5.0, got {val}")

        logger.warning("Unrecognized rating format '%s', setting rating to None", v)
        return None

    @field_validator("availability", mode="before")
    @classmethod
    def validate_availability(cls, v: Any) -> bool:
        """Convert string availability representations to boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            cleaned = v.strip().lower()
            if (
                "out of stock" in cleaned
                or "unavailable" in cleaned
                or cleaned in ("false", "0", "no")
            ):
                return False
            if (
                "in stock" in cleaned
                or "available" in cleaned
                or cleaned in ("true", "1", "yes")
            ):
                return True
            return False
        return bool(v)

    @field_validator("product_url", mode="before")
    @classmethod
    def validate_product_url(cls, v: Any) -> Optional[str]:
        """Strip whitespace and return None if string is empty."""
        if v is None:
            return None
        cleaned = str(v).strip()
        return cleaned if cleaned else None
