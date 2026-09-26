
"""Tests for Greenville search configuration and URL construction."""

import unittest
from datetime import date
from urllib.parse import parse_qs, urlsplit

from hbr_deed_scraper.counties.greenville.search_config import (
    GreenvilleSearchConfig,
    build_results_url,
)


class GreenvilleSearchTests(unittest.TestCase):

    def setUp(self):
        self.config = GreenvilleSearchConfig(
            start_date=date(2026, 9, 21),
            end_date=date(2026, 9, 21),
        )

    def test_same_day_search_uses_exact_deed_filter(self):
        url = build_results_url(self.config)

        parsed = urlsplit(url)
        params = parse_qs(parsed.query)

        self.assertEqual(
            parsed.netloc,
            "greenville.sc.publicsearch.us",
        )

        self.assertEqual(
            params["_docTypes"],
            ["DEED"],
        )

        self.assertEqual(
            params["recordedDateRange"],
            ["20260921,20260921"],
        )

        self.assertEqual(
            params["department"],
            ["RP"],
        )

        self.assertEqual(
            params["limit"],
            ["250"],
        )

        self.assertIn(
            "recordedDateRange=20260921%2C20260921",
            url,
        )

    def test_date_range_can_span_multiple_days(self):
        config = GreenvilleSearchConfig(
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
        )

        params = parse_qs(
            urlsplit(build_results_url(config)).query
        )

        self.assertEqual(
            params["recordedDateRange"],
            ["20260901,20260930"],
        )

    def test_page_size_and_offset_are_explicit(self):
        config = GreenvilleSearchConfig(
            start_date=date(2026, 9, 21),
            end_date=date(2026, 9, 21),
            page_size=50,
        )

        params = parse_qs(
            urlsplit(
                build_results_url(config, offset=50)
            ).query
        )

        self.assertEqual(params["limit"], ["50"])
        self.assertEqual(params["offset"], ["50"])

    def test_reversed_date_range_is_rejected(self):
        with self.assertRaises(ValueError):
            GreenvilleSearchConfig(
                start_date=date(2026, 9, 30),
                end_date=date(2026, 9, 1),
            )

    def test_invalid_page_sizes_are_rejected(self):
        for page_size in (0, -1, 251):
            with self.subTest(page_size=page_size):
                with self.assertRaises(ValueError):
                    GreenvilleSearchConfig(
                        start_date=date(2026, 9, 21),
                        end_date=date(2026, 9, 21),
                        page_size=page_size,
                    )

    def test_negative_offset_is_rejected(self):
        with self.assertRaises(ValueError):
            build_results_url(
                self.config,
                offset=-1,
            )


if __name__ == "__main__":
    unittest.main()
