
"""Controlled regression test for Greenville deed discovery."""

from datetime import date

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from hbr_deed_scraper.core.browser import create_chrome_driver
from hbr_deed_scraper.core.config import BrowserConfig, LOG_DIR
from hbr_deed_scraper.counties.greenville.search_config import (
    GreenvilleSearchConfig,
    build_results_url,
)
from hbr_deed_scraper.counties.greenville.search_state import (
    SearchPageState,
    classify_search_page,
    extract_result_count,
)


# ---------------------------------------------------------
# Project / browser configuration
# ---------------------------------------------------------

CHROME_PROFILE = BrowserConfig().profile_dir

LOG_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOT_PATH = LOG_DIR / "greenville_step7_search.png"
HTML_PATH = LOG_DIR / "greenville_step7_search.html"


# ---------------------------------------------------------
# Historical regression fixture
# ---------------------------------------------------------

# These values validate a known record set.
# They are not production filtering or business rules.
TEST_DATE = date(2026, 9, 21)
EXPECTED_TOTAL = 106
TARGET_INSTRUMENT = "2026064314"

SEARCH_CONFIG = GreenvilleSearchConfig(
    start_date=TEST_DATE,
    end_date=TEST_DATE,
)

RESULTS_URL = build_results_url(SEARCH_CONFIG)


def get_body_text(driver):
    """Return the visible text from the current browser page."""

    return driver.find_element(By.TAG_NAME, "body").text


def wait_for_search_state(driver):
    """Wait for Greenville to reach a recognizable page state.

    Refresh once only when the page remains in a loading state.
    Authentication errors, Forbidden responses and genuine
    no-results pages must not be treated as loading failures.
    """

    def terminal_state(current_driver):
        state = classify_search_page(
            current_driver.current_url,
            get_body_text(current_driver),
        )

        if state == SearchPageState.LOADING:
            return False

        return state

    for attempt in range(1, 3):
        print(
            f"Waiting for search state — attempt {attempt}/2..."
        )

        try:
            return WebDriverWait(driver, 35).until(
                terminal_state
            )

        except TimeoutException as exc:
            if attempt == 1:
                print(
                    "Search did not reach a recognized state. "
                    "Refreshing once..."
                )
                driver.refresh()
            else:
                raise TimeoutError(
                    "Greenville remained in an unrecognized or "
                    "loading state after two bounded waits."
                ) from exc

    raise RuntimeError(
        "Greenville search-state detection ended unexpectedly."
    )


def main():
    """Run the controlled Greenville search regression."""

    print("Starting Greenville Step 7 search test...")
    print(f"Chrome profile: {CHROME_PROFILE}")
    print(f"Test date: {TEST_DATE}")
    print(f"Target instrument: {TARGET_INSTRUMENT}")
    print()

    driver = create_chrome_driver()

    try:
        print("Opening controlled DEED search...")
        driver.get(RESULTS_URL)

        state = wait_for_search_state(driver)

        # -------------------------------------------------
        # Handle expired authentication
        # -------------------------------------------------

        if state == SearchPageState.SIGN_IN:
            print()
            print("The Greenville session requires authentication.")
            print(
                "Please sign in manually in the opened Chrome window."
            )
            print(
                "Do NOT put credentials in the script or terminal."
            )

            input(
                "\nOnce login has completed, press ENTER "
                "here to continue..."
            )

            print("Reopening the controlled DEED search...")
            driver.get(RESULTS_URL)

            state = wait_for_search_state(driver)

        # -------------------------------------------------
        # Explicitly handle unsuccessful portal states
        # -------------------------------------------------

        if state == SearchPageState.FORBIDDEN:
            raise PermissionError(
                "Greenville returned Forbidden. Check the "
                "authenticated session and approved outbound "
                "network route. No records were extracted."
            )

        if state == SearchPageState.SIGN_IN:
            raise RuntimeError(
                "Greenville still requires authentication "
                "after the manual sign-in attempt."
            )

        if state == SearchPageState.NO_RESULTS:
            raise RuntimeError(
                "Greenville returned No Results Found for the "
                "controlled search. This is unexpected for the "
                "known 106-record fixture and must be reviewed."
            )

        if state != SearchPageState.RESULTS:
            raise RuntimeError(
                f"Unexpected Greenville page state: {state}"
            )

        # -------------------------------------------------
        # Validate the known result set
        # -------------------------------------------------

        body_text = get_body_text(driver)

        total_results = extract_result_count(body_text)

        print()
        print("------------------------------------------")
        print("GREENVILLE STEP 7 RESULTS")
        print("------------------------------------------")

        print(f"Current URL: {driver.current_url}")
        print(f"Detected result count: {total_results}")

        if total_results != EXPECTED_TOTAL:
            raise AssertionError(
                "Greenville result-count mismatch: "
                f"expected {EXPECTED_TOTAL}, got {total_results}."
            )

        print(
            f"Result-count check: PASS "
            f"(expected {EXPECTED_TOTAL})"
        )

        # -------------------------------------------------
        # Check the currently visible page
        # -------------------------------------------------

        if TARGET_INSTRUMENT in body_text:
            print(
                f"Target instrument {TARGET_INSTRUMENT}: FOUND"
            )

            position = body_text.find(TARGET_INSTRUMENT)

            start = max(position - 150, 0)
            end = min(position + 400, len(body_text))

            print()
            print("Text around target record:")
            print("------------------------------------------")
            print(body_text[start:end])
            print("------------------------------------------")

        else:
            print(
                f"Target instrument {TARGET_INSTRUMENT}: "
                "not visible on the currently loaded results page."
            )
            print(
                "This is not a full-dataset failure. "
                "Additional pages must be checked."
            )

        # -------------------------------------------------
        # Save successful-search evidence locally
        # -------------------------------------------------

        driver.save_screenshot(str(SCREENSHOT_PATH))

        HTML_PATH.write_text(
            driver.page_source,
            encoding="utf-8",
        )

        print()
        print(f"Screenshot saved: {SCREENSHOT_PATH}")
        print(f"HTML saved: {HTML_PATH}")

        print()
        print("Browser will remain open for inspection.")

        input(
            "Press ENTER when you are ready "
            "to close the Selenium browser..."
        )

    finally:
        driver.quit()
        print("Browser test complete.")


if __name__ == "__main__":
    main()
