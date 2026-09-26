
"""Offline tests for complete Greenville result collection."""

import unittest
from unittest.mock import patch

from hbr_deed_scraper.counties.greenville import collection
from hbr_deed_scraper.counties.greenville.pagination import (
    PageRange,
    PaginationError,
)


def make_records(start, end):
    """Create synthetic instrument records for testing."""

    return [
        {"instrument_number":str(number)}
        for number in range(start, end + 1)
    ]


class FakeDriver:
    """Represent consecutive result pages without opening Chrome."""

    def __init__(self, ranges, pages):
        self.ranges = ranges
        self.pages = pages
        self.index = 0

    def advance(self):
        self.index += 1
        return self.ranges[self.index]


class GreenvilleCollectionTests(unittest.TestCase):

    def collect(self, driver, max_pages=1000):
        """Connect fake navigation to the real collection logic."""

        with (
            patch.object(
                collection,
                "wait_for_page_range",
                side_effect=lambda d: d.ranges[d.index],
            ),
            patch.object(
                collection,
                "advance_to_next_page",
                side_effect=lambda d, current: d.advance(),
            ),
        ):
            return collection.collect_result_pages(
                driver,
                lambda d: d.pages[d.index],
                max_pages=max_pages,
            )

    def test_collects_all_106_records_across_three_pages(self):
        ranges = [
            PageRange(1, 50, 106),
            PageRange(51, 100, 106),
            PageRange(101, 106, 106),
        ]

        pages = [
            make_records(1, 50),
            make_records(51, 100),
            make_records(101, 106),
        ]

        # A synthetic fixture representing the known later-page record.
        pages[1][13]["instrument_number"] = "2026064314"

        driver = FakeDriver(ranges, pages)

        records = self.collect(driver)

        self.assertEqual(len(records), 106)
        self.assertEqual(driver.index, 2)

        instruments = {
            record["instrument_number"]
            for record in records
        }

        self.assertEqual(len(instruments), 106)
        self.assertIn("2026064314", instruments)

    def test_collects_single_250_setting_page(self):
        driver = FakeDriver(
            [PageRange(1, 106, 106)],
            [make_records(1, 106)],
        )

        records = self.collect(driver)

        self.assertEqual(len(records), 106)
        self.assertEqual(driver.index, 0)

    def test_rejects_duplicate_instrument_across_pages(self):
        driver = FakeDriver(
            [
                PageRange(1, 2, 4),
                PageRange(3, 4, 4),
            ],
            [
                [
                    {"instrument_number": "A"},
                    {"instrument_number": "B"},
                ],
                [
                    {"instrument_number": "B"},
                    {"instrument_number": "C"},
                ],
            ],
        )

        with self.assertRaisesRegex(
            PaginationError,
            "Duplicate instrument",
        ):
            self.collect(driver)

    def test_rejects_missing_rows(self):
        driver = FakeDriver(
            [PageRange(1, 2, 2)],
            [[{"instrument_number": "A"}]],
        )

        with self.assertRaisesRegex(
            PaginationError,
            "row-count mismatch",
        ):
            self.collect(driver)

    def test_rejects_blank_instrument_number(self):
        driver = FakeDriver(
            [PageRange(1, 2, 2)],
            [
                [
                    {"instrument_number": "A"},
                    {"instrument_number": ""},
                ]
            ],
        )

        with self.assertRaisesRegex(
            PaginationError,
            "without an instrument number",
        ):
            self.collect(driver)

    def test_respects_maximum_page_limit(self):
        driver = FakeDriver(
            [
                PageRange(1, 2, 4),
                PageRange(3, 4, 4),
            ],
            [
                make_records(1, 2),
                make_records(3, 4),
            ],
        )

        with self.assertRaisesRegex(
            PaginationError,
            "configured limit",
        ):
            self.collect(driver, max_pages=1)

        self.assertEqual(driver.index, 0)

    def test_rejects_invalid_maximum_page_limit(self):
        driver = FakeDriver(
            [PageRange(1, 1, 1)],
            [[{"instrument_number": "A"}]],
        )

        with self.assertRaises(ValueError):
            self.collect(driver, max_pages=0)


if __name__ == "__main__":
    unittest.main()
