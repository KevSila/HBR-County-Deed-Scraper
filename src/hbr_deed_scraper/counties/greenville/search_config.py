
"""Configuration and URL construction for Greenville deed searches."""

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode


RESULTS_BASE_URL = "https://greenville.sc.publicsearch.us/results"


@dataclass(frozen=True, slots=True)
class GreenvilleSearchConfig:
    """Date range for Greenville's Advanced DEED search."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        """Reject invalid date ranges before opening the browser."""

        if self.start_date > self.end_date:
            raise ValueError(
                "start_date cannot be later than end_date."
            )


def build_results_url(config: GreenvilleSearchConfig) -> str:
    """Build the observed working Greenville Advanced Search URL.

    Pagination is deliberately excluded. Appending unverified limit
    and offset parameters caused the portal to report no results.
    Pagination will be handled separately using verified controls.
    """

    start = config.start_date.strftime("%Y%m%d")
    end = config.end_date.strftime("%Y%m%d")

    params = {
        "department": "RP",
        "docTypes": "DEED",
        "recordedDateRange": f"{start},{end}",
        "searchType": "advancedSearch",
    }

    return f"{RESULTS_BASE_URL}?{urlencode(params)}"
