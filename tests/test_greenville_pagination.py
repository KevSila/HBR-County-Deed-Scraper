
"""Offline tests for Greenville result-page navigation."""

import unittest
from types import SimpleNamespace

from selenium.webdriver.common.by import By

from hbr_deed_scraper.counties.greenville.pagination import (
    NEXT_PAGE_SELECTOR,
    PageRange,
    PaginationError,
    advance_to_next_page,
    parse_page_range,
    wait_for_page_range,
)


RESULTS_URL = "https://greenville.sc.publicsearch.us/results"


class FakeNextButton:
    def __init__(self, driver):
        self.driver = driver

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def click(self):
        self.driver.clicks += 1

        if self.driver.advance_on_click:
            self.driver.index += 1


class FakeDriver:
    """Small browser substitute; no real Chrome or network access."""

    current_url = RESULTS_URL

    def __init__(self, pages, advance_on_click=True):
        self.pages = pages
        self.index = 0
        self.clicks = 0
        self.advance_on_click = advance_on_click

    def find_element(self, by, value):
        if by == By.TAG_NAME and value == "body":
            return SimpleNamespace(text=self.pages[self.index])

        if by == By.CSS_SELECTOR and value == NEXT_PAGE_SELECTOR:
            return FakeNextButton(self)

        raise AssertionError(
            f"Unexpected locator: {by}, {value}"
        )


class GreenvillePaginationTests(unittest.TestCase):

    def test_first_page_range(self):
        self.assertEqual(
            parse_page_range("1-50 of 106 results"),
            PageRange(1, 50, 106),
        )

    def test_middle_and_final_page_ranges(self):
        cases = [
            ("51-100 of 106 results", PageRange(51, 100, 106)),
            ("101-106 of 106 results", PageRange(101, 106, 106)),
        ]

        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(
                    parse_page_range(text),
                    expected,
                )

    def test_single_page_with_250_setting(self):
        page = parse_page_range("1-106 of 106 results")

        self.assertEqual(page.count, 106)
        self.assertTrue(page.is_last)

    def test_large_counts_with_commas(self):
        self.assertEqual(
            parse_page_range("1-1,000 of 1,234 results"),
            PageRange(1, 1000, 1234),
        )

    def test_missing_heading(self):
        self.assertIsNone(
            parse_page_range("Loading Search Results...")
        )

    def test_invalid_ranges_are_rejected(self):
        for values in [(0, 50, 106), (51, 50, 106), (1, 107, 106)]:
            with self.subTest(values=values):
                with self.assertRaises(PaginationError):
                    PageRange(*values)

    def test_next_button_advances_across_all_three_pages(self):
        driver = FakeDriver(
            [
                "1-50 of 106 results",
                "51-100 of 106 results",
                "101-106 of 106 results",
            ]
        )

        first = wait_for_page_range(driver)

        second = advance_to_next_page(driver, first)
        third = advance_to_next_page(driver, second)
        finished = advance_to_next_page(driver, third)

        self.assertEqual(second, PageRange(51, 100, 106))
        self.assertEqual(third, PageRange(101, 106, 106))
        self.assertIsNone(finished)
        self.assertEqual(driver.clicks, 2)

    def test_complete_250_row_view_needs_no_next_click(self):
        driver = FakeDriver(["1-106 of 106 results"])

        current = wait_for_page_range(driver)
        following = advance_to_next_page(driver, current)

        self.assertIsNone(following)
        self.assertEqual(driver.clicks, 0)

    def test_backend_timeout_is_not_treated_as_empty_data(self):
        driver = FakeDriver(
            [
                "No Results Found. Error While Running Search: "
                "The request timed out. Please try again."
            ]
        )

        with self.assertRaises(PaginationError):
            wait_for_page_range(driver)

    def test_repeated_page_does_not_count_as_advancement(self):
        driver = FakeDriver(
            ["1-50 of 106 results"],
            advance_on_click=False,
        )

        current = wait_for_page_range(driver)

        with self.assertRaises(PaginationError):
            advance_to_next_page(
                driver,
                current,
                timeout=0,
            )


if __name__ == "__main__":
    unittest.main()
