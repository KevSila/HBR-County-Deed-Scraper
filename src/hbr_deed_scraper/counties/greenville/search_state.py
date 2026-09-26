
"""Identify the state of a Greenville PublicSearch results page."""

import re
from enum import Enum
from urllib.parse import urlsplit


class SearchPageState(str, Enum):
    """Recognized Greenville search-page states."""

    RESULTS = "results"
    SIGN_IN = "sign_in"
    FORBIDDEN = "forbidden"
    NO_RESULTS = "no_results"
    LOADING = "loading"


def extract_result_count(body_text: str) -> int | None:
    """Read the total count from a Greenville results heading.

    Examples:
        1-50 of 106 results
        1-1,000 of 1,234 results

    Returns None if no results heading is present.
    """

    match = re.search(
        r"\b\d[\d,]*\s*-\s*\d[\d,]*\s+of\s+([\d,]+)\s+results\b",
        body_text,
        re.IGNORECASE,
    )

    if match is None:
        return None

    return int(match.group(1).replace(",", ""))


def classify_search_page(
    current_url: str,
    body_text: str,
) -> SearchPageState:
    """Classify a page without opening a browser or making requests.

    Forbidden is checked before sign-in because Greenville's
    Forbidden page can itself contain a sign-in link.
    """

    text = " ".join(body_text.casefold().split())
    path = urlsplit(current_url).path.casefold()

    if (
        text.startswith("forbidden")
        or "you don't have permission to view this resource" in text
    ):
        return SearchPageState.FORBIDDEN

    if (
        "/signin" in path
        or (
            "forgot your password?" in text
            and "sign in" in text
        )
    ):
        return SearchPageState.SIGN_IN

    if "no results found" in text:
        return SearchPageState.NO_RESULTS

    if extract_result_count(body_text) is not None:
        return SearchPageState.RESULTS

    return SearchPageState.LOADING
