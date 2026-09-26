
"""Tests for Greenville search-page state detection."""

import unittest

from hbr_deed_scraper.counties.greenville.search_state import (
    SearchPageState,
    classify_search_page,
    extract_result_count,
)


RESULTS_URL = "https://greenville.sc.publicsearch.us/results"


class GreenvilleSearchStateTests(unittest.TestCase):

    def test_result_count_is_extracted(self):
        self.assertEqual(
            extract_result_count("1-50 of 106 results"),
            106,
        )

    def test_large_result_count_with_commas(self):
        self.assertEqual(
            extract_result_count("1-1,000 of 1,234 results"),
            1234,
        )

    def test_results_page_is_recognized(self):
        state = classify_search_page(
            RESULTS_URL,
            "1-50 of 106 results",
        )

        self.assertEqual(state, SearchPageState.RESULTS)

    def test_forbidden_page_is_not_mistaken_for_sign_in(self):
        state = classify_search_page(
            RESULTS_URL,
            (
                "Forbidden\n"
                "You don't have permission to view this resource.\n"
                "Perhaps you need to sign in?"
            ),
        )

        self.assertEqual(state, SearchPageState.FORBIDDEN)

    def test_sign_in_redirect_is_recognized(self):
        state = classify_search_page(
            "https://greenville.sc.publicsearch.us/signin",
            "Sign In",
        )

        self.assertEqual(state, SearchPageState.SIGN_IN)

    def test_sign_in_form_is_recognized(self):
        state = classify_search_page(
            RESULTS_URL,
            "Sign In Email Password Forgot your password?",
        )

        self.assertEqual(state, SearchPageState.SIGN_IN)

    def test_no_results_page_is_recognized(self):
        state = classify_search_page(
            RESULTS_URL,
            (
                "No Results Found\n"
                'Your search for "09/21/2026-09/21/2026" '
                "returned no results."
            ),
        )

        self.assertEqual(state, SearchPageState.NO_RESULTS)

    def test_loading_page_is_recognized(self):
        state = classify_search_page(
            RESULTS_URL,
            "Loading Search Results...",
        )

        self.assertEqual(state, SearchPageState.LOADING)

    def test_backend_timeout_takes_precedence_over_no_results(self):
        state = classify_search_page(
            RESULTS_URL,
            (
                "No Results Found\n"
                'Your search for "09/21/2026-09/21/2026" '
                "returned no results.\n"
                "Error While Running Search:\n"
                "The request timed out. Please try again."
            ),
        )

        self.assertEqual(
            state,
            SearchPageState.SEARCH_ERROR,
        )

    def test_search_error_without_no_results_heading(self):
        state = classify_search_page(
            RESULTS_URL,
            "Error While Running Search: The request timed out.",
        )

        self.assertEqual(
            state,
            SearchPageState.SEARCH_ERROR,
        )
if __name__ == "__main__":
    unittest.main()
