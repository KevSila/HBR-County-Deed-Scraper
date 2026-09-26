
"""Verified pagination navigation for Greenville PublicSearch."""

import re
from dataclasses import dataclass

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .search_state import SearchPageState, classify_search_page


# Observed in Greenville's saved, rendered search-results HTML.
NEXT_PAGE_SELECTOR = 'button[aria-label="next page"]'

PAGE_RANGE_PATTERN = re.compile(
    r"\b(\d[\d,]*)\s*[-–]\s*(\d[\d,]*)"
    r"\s+of\s+(\d[\d,]*)\s+results\b",
    re.IGNORECASE,
)


class PaginationError(RuntimeError):
    """Raised when Greenville pagination cannot be validated."""


@dataclass(frozen=True, slots=True)
class PageRange:
    """The displayed range and total reported by the portal."""

    start: int
    end: int
    total: int

    def __post_init__(self) -> None:
        if not 1 <= self.start <= self.end <= self.total:
            raise PaginationError(
                "Invalid Greenville results range: "
                f"{self.start}-{self.end} of {self.total}."
            )

    @property
    def count(self) -> int:
        return self.end - self.start + 1

    @property
    def is_last(self) -> bool:
        return self.end == self.total


def parse_page_range(body_text: str) -> PageRange | None:
    """Parse headings such as '51-100 of 106 results'."""

    match = PAGE_RANGE_PATTERN.search(body_text)

    if match is None:
        return None

    values = [
        int(value.replace(",", ""))
        for value in match.groups()
    ]

    return PageRange(*values)


def wait_for_page_range(
    driver,
    *,
    expected_start: int | None = None,
    expected_total: int | None = None,
    timeout: float = 35,
) -> PageRange:
    """Wait for a valid result range and reject portal errors.

    When navigating, expected_start prevents the previous page's
    still-visible heading from being mistaken for the new page.
    """

    def inspect(current_driver):
        body_text = current_driver.find_element(
            By.TAG_NAME,
            "body",
        ).text

        state = classify_search_page(
            current_driver.current_url,
            body_text,
        )

        if state in {
            SearchPageState.FORBIDDEN,
            SearchPageState.SIGN_IN,
            SearchPageState.SEARCH_ERROR,
            SearchPageState.NO_RESULTS,
        }:
            raise PaginationError(
                f"Greenville pagination stopped: {state.value}."
            )

        if state != SearchPageState.RESULTS:
            return False

        page = parse_page_range(body_text)

        if page is None:
            return False

        if (
            expected_total is not None
            and page.total != expected_total
        ):
            raise PaginationError(
                "Greenville result total changed during pagination: "
                f"expected {expected_total}, got {page.total}."
            )

        if (
            expected_start is not None
            and page.start != expected_start
        ):
            return False

        return page

    try:
        return WebDriverWait(driver, timeout).until(inspect)

    except TimeoutException as exc:
        raise PaginationError(
            "Greenville did not display the expected result range "
            f"within {timeout} seconds. "
            f"Expected start: {expected_start}."
        ) from exc


def advance_to_next_page(
    driver,
    current: PageRange,
    *,
    timeout: float = 35,
) -> PageRange | None:
    """Click Greenville's verified Next button and await advancement.

    Returns None when the current range already reaches the total.
    """

    if current.is_last:
        return None

    try:
        button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, NEXT_PAGE_SELECTOR)
            )
        )

    except TimeoutException as exc:
        raise PaginationError(
            "Greenville's Next Page button was not clickable."
        ) from exc

    button.click()

    next_page = wait_for_page_range(
        driver,
        expected_start=current.end + 1,
        expected_total=current.total,
        timeout=timeout,
    )

    if next_page.end <= current.end:
        raise PaginationError(
            "Greenville did not advance beyond the previous page."
        )

    return next_page
