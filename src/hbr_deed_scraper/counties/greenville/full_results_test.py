
"""Controlled end-to-end regression for Greenville deed collection.

This is a development test, not the production scraper.
It reuses the previously validated result-table parser.
"""

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from hbr_deed_scraper.core.browser import create_chrome_driver
from hbr_deed_scraper.counties.greenville.collection import (
    collect_result_pages,
)
from hbr_deed_scraper.counties.greenville.extract_results_test import (
    extract_rows,
)
from hbr_deed_scraper.counties.greenville.pagination import (
    PageRange,
    PaginationError,
    wait_for_page_range,
)
from hbr_deed_scraper.counties.greenville.search_state import (
    SearchPageState,
)
from hbr_deed_scraper.counties.greenville.search_test import (
    EXPECTED_TOTAL,
    RESULTS_URL,
    TARGET_INSTRUMENT,
    wait_for_search_state,
)


def extract_visible_page(driver):
    """Wait for the expected table size before parsing its rows."""

    page = wait_for_page_range(driver)

    def table_ready(current_driver):
        try:
            tables = current_driver.find_elements(
                By.TAG_NAME,
                "table",
            )

            for table in tables:
                header_text = table.text.upper()

                if not all(
                    name in header_text
                    for name in ("BOOK", "PAGE", "GRANTOR", "GRANTEE")
                ):
                    continue

                rows = table.find_elements(
                    By.CSS_SELECTOR,
                    "tbody tr",
                )

                if len(rows) == page.count:
                    return True

        except StaleElementReferenceException:
            return False

        return False

    try:
        WebDriverWait(driver, 25).until(table_ready)

    except TimeoutException as exc:
        raise PaginationError(
            "The result table did not display the expected "
            f"{page.count} rows for range "
            f"{page.start}-{page.end}."
        ) from exc

    return extract_rows(driver)


def main():
    """Validate complete collection of the historical test dataset."""

    print("GREENVILLE COMPLETE-RESULTS REGRESSION")
    print(f"Expected total: {EXPECTED_TOTAL}")
    print(f"Control instrument: {TARGET_INSTRUMENT}")

    driver = create_chrome_driver()

    try:
        driver.get(RESULTS_URL)

        state = wait_for_search_state(driver)

        if state == SearchPageState.SIGN_IN:
            print("Please sign in manually in Chrome.")

            input(
                "After login completes, press ENTER here..."
            )

            driver.get(RESULTS_URL)
            state = wait_for_search_state(driver)

        if state != SearchPageState.RESULTS:
            raise RuntimeError(
                "Greenville did not return a valid results page. "
                f"Detected state: {state.value}."
            )

        initial = wait_for_page_range(driver)

        print(
            f"Initial range: "
            f"{initial.start}-{initial.end} of {initial.total}"
        )

        print()
        print(
            "In Chrome, select 50 Results Per Page if necessary."
        )
        print(
            "Wait until the heading displays 1-50 of 106."
        )

        input("Then press ENTER here to begin collection...")

        first_page = wait_for_page_range(driver)

        if first_page != PageRange(1, 50, EXPECTED_TOTAL):
            raise PaginationError(
                "The controlled test requires the first 50-row "
                f"page. Actual range: {first_page}."
            )

        records = collect_result_pages(
            driver,
            extract_visible_page,
            max_pages=10,
        )

        target = next(
            (
                record
                for record in records
                if record["instrument_number"] == TARGET_INSTRUMENT
            ),
            None,
        )

        if target is None:
            raise AssertionError(
                "The control instrument was absent from the "
                "complete extracted dataset."
            )

        if target["book"] != "2803" or target["page"] != "704":
            raise AssertionError(
                "The control instrument's book/page did not "
                "match the historical fixture."
            )

        print()
        print("=" * 60)
        print("COMPLETE-RESULTS VALIDATION: PASS")
        print("=" * 60)
        print(f"Extracted records: {len(records)}")
        print(f"Unique instruments: {len(records)}")
        print(f"Control instrument: {TARGET_INSTRUMENT}")
        print(f"Book/page: {target['book']}/{target['page']}")

        input(
            "\nPress ENTER to close the test browser..."
        )

    except Exception as exc:
        print()
        print(
            f"INTEGRATION STOPPED: "
            f"{type(exc).__name__}: {exc}"
        )
        raise

    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    main()
