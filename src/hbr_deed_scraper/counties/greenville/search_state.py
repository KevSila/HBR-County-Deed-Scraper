"""Identify the state of a Greenville PublicSearch results page."""

import re
from enum import Enum
from urllib.parse import urlsplit


class SearchPageState(str, Enum):
    """Recognized Greenville search-page states."""

    RESULTS = "results"
    SIGN_IN = "sign_in"
    FORBIDDEN = "forbidden"
    SEARCH_ERROR = "search_error"
    NO_RESULTS = "no_results"
    LOADING = "loading"


def extract_result_count(body_text: str) -> int | None:
    """Extract the total count from a Greenville results heading."""

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
    """Classify the visible state of a Greenville search page.

    The order matters: an error page may also display the
    generic No Results Found heading.
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

    # Check backend errors BEFORE the generic no-results heading.
    if (
        "error while running search" in text
        or "the request timed out" in text
    ):
        return SearchPageState.SEARCH_ERROR

    if "no results found" in text:
        return SearchPageState.NO_RESULTS

    if extract_result_count(body_text) is not None:
        return SearchPageState.RESULTS

    return SearchPageState.LOADING