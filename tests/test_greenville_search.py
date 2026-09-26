
"""Tests for the verified Greenville Advanced Search URL."""

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

    def test_same_day_advanced_deed_search(self):
        params = parse_qs(
            urlsplit(build_results_url(self.config)).query
        )

        self.assertEqual(
            params["recordedDateRange"],
            ["20260921,20260921"],
        )
        self.assertEqual(params["docTypes"], ["DEED"])
        self.assertEqual(params["department"], ["RP"])
        self.assertEqual(
            params["searchType"],
            ["advancedSearch"],
        )

    def test_url_points_to_greenville_results(self):
        parsed = urlsplit(build_results_url(self.config))

        self.assertEqual(
            parsed.netloc,
            "greenville.sc.publicsearch.us",
        )
        self.assertEqual(parsed.path, "/results")

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

    def test_dates_are_zero_padded(self):
        config = GreenvilleSearchConfig(
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 9),
        )

        params = parse_qs(
            urlsplit(build_results_url(config)).query
        )

        self.assertEqual(
            params["recordedDateRange"],
            ["20260102,20260109"],
        )

    def test_unverified_pagination_parameters_are_excluded(self):
        params = parse_qs(
            urlsplit(build_results_url(self.config)).query
        )

        self.assertNotIn("limit", params)
        self.assertNotIn("offset", params)
        self.assertNotIn("_docTypes", params)

    def test_reversed_date_range_is_rejected(self):
        with self.assertRaises(ValueError):
            GreenvilleSearchConfig(
                start_date=date(2026, 9, 30),
                end_date=date(2026, 9, 1),
            )


if __name__ == "__main__":
    unittest.main()
