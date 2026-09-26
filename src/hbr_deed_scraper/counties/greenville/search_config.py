
"""Configuration and URL construction for Greenville deed searches."""

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode


RESULTS_BASE_URL = "https://greenville.sc.publicsearch.us/results"

# Greenville currently supports up to 250 results per page.
MAX_PAGE_SIZE = 250


@dataclass(frozen=True, slots=True)
class GreenvilleSearchConfig:
    """Date range and pagination settings for a Greenville DEED search."""

    start_date: date
    end_date: date
    page_size: int = 250

    def __post_init__(self) -> None:
        """Reject invalid configurations before opening a browser."""

        if self.start_date > self.end_date:
            raise ValueError(
                "start_date cannot be later than end_date."
            )

        if not 1 <= self.page_size <= MAX_PAGE_SIZE:
            raise ValueError(
                f"page_size must be between 1 and {MAX_PAGE_SIZE}."
            )


def build_results_url(
    config: GreenvilleSearchConfig,
    *,
    offset: int = 0,
) -> str:
    """Build a Greenville exact-DEED search URL.

    The requested page size and offset are explicit, so results do not
    depend on settings saved in an individual browser profile.
    """

    if offset < 0:
        raise ValueError("offset cannot be negative.")

    start = config.start_date.strftime("%Y%m%d")
    end = config.end_date.strftime("%Y%m%d")

    params = {
        "_docTypes": "DEED",
        "department": "RP",
        "keywordSearch": "false",
        "limit": config.page_size,
        "offset": offset,
        "recordedDateRange": f"{start},{end}",
        "searchOrText": "false",
        "searchType": "quickSearch",
    }

    return f"{RESULTS_BASE_URL}?{urlencode(params)}"
