from pathlib import Path
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException


# ---------------------------------------------------------
# Project / browser configuration
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

CHROME_PROFILE = PROJECT_ROOT / ".chrome-profile"

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOT_PATH = LOG_DIR / "greenville_step7_search.png"
HTML_PATH = LOG_DIR / "greenville_step7_search.html"


# ---------------------------------------------------------
# Controlled Greenville test
# ---------------------------------------------------------

TEST_DATE = "20260921"
EXPECTED_TOTAL = 106
TARGET_INSTRUMENT = "2026064314"

RESULTS_URL = (
    "https://greenville.sc.publicsearch.us/results"
    "?_docTypes=DEED"
    "&department=RP"
    "&keywordSearch=false"
    "&limit=250"
    "&offset=0"
    f"&recordedDateRange={TEST_DATE}%2C{TEST_DATE}"
    "&searchOrText=false"
    "&searchType=quickSearch"
)


def get_body_text(driver):
    return driver.find_element(By.TAG_NAME, "body").text


def extract_result_count(text):
    """
    Looks for portal text such as:

        1-106 of 106 results

    Returns 106 if found.
    """
    match = re.search(
        r"\d[\d,]*-\d[\d,]*\s+of\s+([\d,]+)\s+results",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return int(match.group(1).replace(",", ""))


def wait_for_results(driver):
    """
    Greenville PublicSearch can occasionally stall.

    Wait once, refresh once if necessary, then wait again.
    """

    for attempt in range(1, 3):

        print(f"Waiting for results — attempt {attempt}/2...")

        try:
            WebDriverWait(driver, 35).until(
                lambda d: extract_result_count(get_body_text(d)) is not None
            )

            return get_body_text(driver)

        except TimeoutException:

            if attempt == 1:
                print("Results did not finish loading.")
                print("Refreshing once because this portal has shown intermittent stalls...")
                driver.refresh()

            else:
                raise


def main():

    print("Starting Greenville Step 7 search test...")
    print(f"Chrome profile: {CHROME_PROFILE}")
    print(f"Test date: {TEST_DATE}")
    print(f"Target instrument: {TARGET_INSTRUMENT}")
    print()

    options = Options()

    options.add_argument(
        f"--user-data-dir={CHROME_PROFILE}"
    )

    options.add_argument("--profile-directory=Default")
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    try:

        print("Opening controlled DEED search...")
        driver.get(RESULTS_URL)

        body_text = get_body_text(driver)

        # -------------------------------------------------
        # Detect authentication state
        # -------------------------------------------------

        if "/signin" in driver.current_url.lower():

            print()
            print("The Greenville session is not currently authenticated.")
            print("Please sign in manually in the opened Chrome window.")
            print("Do NOT put the username/password in this script.")

            input(
                "\nAfter you are signed in, press ENTER here to continue..."
            )

            print("Reopening controlled DEED search...")
            driver.get(RESULTS_URL)

        # -------------------------------------------------
        # Wait for search results
        # -------------------------------------------------

        body_text = wait_for_results(driver)

        total_results = extract_result_count(body_text)

        print()
        print("------------------------------------------")
        print("GREENVILLE STEP 7 RESULTS")
        print("------------------------------------------")

        print(f"Current URL: {driver.current_url}")
        print(f"Detected result count: {total_results}")

        if total_results == EXPECTED_TOTAL:
            print(
                f"Result-count check: PASS "
                f"(expected {EXPECTED_TOTAL})"
            )
        else:
            print(
                f"Result-count check: REVIEW "
                f"(expected {EXPECTED_TOTAL}, got {total_results})"
            )

        # -------------------------------------------------
        # Verify known Greenville record
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
                f"Target instrument {TARGET_INSTRUMENT}: NOT FOUND"
            )

        # -------------------------------------------------
        # Save debugging evidence
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
            "Press ENTER when you are ready to close the Selenium browser..."
        )

    finally:

        driver.quit()
        print("Browser test complete.")


if __name__ == "__main__":
    main()