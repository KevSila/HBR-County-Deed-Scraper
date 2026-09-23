from __future__ import annotations

import json
import re
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# ============================================================
# TEST CONFIGURATION
# ============================================================

TEST_DATE = "09/21/2026"
TARGET_INSTRUMENT = "2026064314"

EXPECTED_CONSIDERATION = "$365,000.00"
EXPECTED_BOOK = "2803"
EXPECTED_PAGE = "704"
EXPECTED_GRANTOR = "D R HORTON INC"
EXPECTED_GRANTEE = "BATES TRICIA ANNE"

RESULTS_PAGE_SIZE = 250
MAX_RESULT_PAGES = 20


def build_results_url(
    offset: int = 0,
    limit: int = RESULTS_PAGE_SIZE,
) -> str:
    """
    Build the Greenville DEED results URL explicitly.

    The scraper controls its own page size rather than depending
    on the user's saved Results Per Page browser preference.
    """

    return (
        "https://greenville.sc.publicsearch.us/results"
        "?_docTypes=DEED"
        "&department=RP"
        "&keywordSearch=false"
        f"&limit={limit}"
        f"&offset={offset}"
        "&recordedDateRange=20260921%2C20260921"
        "&searchOrText=false"
        "&searchType=quickSearch"
    )


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

CHROME_PROFILE_DIR = PROJECT_ROOT / ".chrome-profile"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
LOG_DIR = PROJECT_ROOT / "logs"

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# BROWSER
# ============================================================

def build_driver() -> WebDriver:
    """
    Start Selenium Chrome using the dedicated project profile.

    The dedicated profile preserves the Greenville login session
    without coupling the scraper to Kevin's normal Chrome profile.
    """

    options = webdriver.ChromeOptions()

    options.add_argument(
        f"--user-data-dir={CHROME_PROFILE_DIR}"
    )

    options.add_argument("--start-maximized")

    print("Starting Greenville Chrome...")
    print(f"Chrome profile: {CHROME_PROFILE_DIR}")

    return webdriver.Chrome(options=options)


# ============================================================
# SEARCH RESULT NAVIGATION
# ============================================================

def get_result_rows(
    driver: WebDriver,
    wait: WebDriverWait,
):
    """
    Return populated Greenville search-result rows.

    We intentionally do not depend on a particular saved
    Results Per Page browser preference.
    """

    def rows_available(current_driver):
        rows = current_driver.find_elements(
            By.CSS_SELECTOR,
            "table tbody tr",
        )

        populated_rows = [
            row
            for row in rows
            if row.text.strip()
        ]

        return populated_rows or False

    return wait.until(rows_available)


def find_target_row(
    rows,
):
    """
    Find the table row containing the target instrument.

    This is more robust than Selenium LINK_TEXT because the
    Greenville interface may render the instrument number with
    JavaScript-driven markup rather than a normal <a> element.
    """

    for row in rows:

        row_text = row.text.strip()

        if TARGET_INSTRUMENT in row_text:
            return row

    return None


def find_instrument_element(
    row,
):
    """
    Find the element displaying the target instrument inside
    a positively identified result row.
    """

    candidates = row.find_elements(
        By.XPATH,
        f".//*[normalize-space()='{TARGET_INSTRUMENT}']",
    )

    if candidates:
        return candidates[0]

    return None


def save_target_row_debug(
    row,
) -> Path:
    """
    Save the target row's raw HTML if navigation cannot be
    completed. This gives us reproducible DOM evidence rather
    than relying only on screenshots.
    """

    output_path = (
        LOG_DIR
        / f"greenville_step7c_{TARGET_INSTRUMENT}_row.html"
    )

    output_path.write_text(
        row.get_attribute("outerHTML"),
        encoding="utf-8",
    )

    return output_path


def navigate_from_target_row(
    driver: WebDriver,
    wait: WebDriverWait,
    row,
) -> None:
    """
    Navigate from the identified search-result row to its
    document-detail page.

    Preference order:
    1. Use an explicit /doc/ href if the row contains one.
    2. Otherwise click the instrument element normally.
    3. Fall back to a JavaScript click for JS-driven controls.
    """

    # --------------------------------------------------------
    # Strategy 1: discover an actual document URL in the row
    # --------------------------------------------------------

    document_links = row.find_elements(
        By.CSS_SELECTOR,
        "a[href*='/doc/']",
    )

    if document_links:

        href = document_links[0].get_attribute(
            "href"
        )

        if href:

            print(
                f"Document route discovered: {href}"
            )

            driver.get(href)

            wait.until(
                lambda current_driver:
                "/doc/" in current_driver.current_url
            )

            return

    # --------------------------------------------------------
    # Strategy 2: locate the visible instrument element
    # --------------------------------------------------------

    instrument_element = find_instrument_element(
        row
    )

    if instrument_element is None:

        debug_path = save_target_row_debug(
            row
        )

        raise RuntimeError(
            "Target row was found, but the instrument "
            "element could not be identified. "
            f"Row HTML saved to: {debug_path}"
        )

    driver.execute_script(
        """
        arguments[0].scrollIntoView({
            block: 'center',
            inline: 'center'
        });
        """,
        instrument_element,
    )

    previous_url = driver.current_url

    try:

        instrument_element.click()

    except Exception:

        print(
            "Normal click failed; trying "
            "JavaScript click..."
        )

        driver.execute_script(
            "arguments[0].click();",
            instrument_element,
        )

    try:

        wait.until(
            lambda current_driver:
            (
                "/doc/" in current_driver.current_url
                and current_driver.current_url
                != previous_url
            )
        )

        return

    except TimeoutException:

        # Sometimes the click listener is attached to a parent
        # element rather than directly to the visible text.
        parent = instrument_element.find_element(
            By.XPATH,
            "..",
        )

        driver.execute_script(
            "arguments[0].click();",
            parent,
        )

        try:

            wait.until(
                lambda current_driver:
                "/doc/" in current_driver.current_url
            )

            return

        except TimeoutException:

            debug_path = save_target_row_debug(
                row
            )

            raise RuntimeError(
                "Target instrument row was found, "
                "but clicking it did not open the "
                "document detail page. "
                f"Row HTML saved to: {debug_path}"
            )


def locate_target_record(
    driver: WebDriver,
    wait: WebDriverWait,
):
    """
    Locate the target instrument across Greenville result pages.

    This deliberately avoids relying on a user's 50/250 Results
    Per Page preference.

    If Greenville honors limit=250, the known test requires only
    one request. If the portal returns fewer rows, pagination
    continues using the number of rows actually received.
    """

    offset = 0
    seen_page_signatures: set[str] = set()

    for page_number in range(
        1,
        MAX_RESULT_PAGES + 1,
    ):

        results_url = build_results_url(
            offset=offset,
        )

        print()
        print(
            f"Opening result page {page_number}..."
        )

        print(
            f"Requested offset: {offset}"
        )

        print(results_url)

        driver.get(
            results_url
        )

        if "/signin" in driver.current_url.lower():

            raise RuntimeError(
                "Greenville session is not authenticated. "
                "Sign in using the dedicated Selenium "
                "Chrome profile before rerunning."
            )

        try:

            rows = get_result_rows(
                driver,
                wait,
            )

        except TimeoutException:

            print(
                "Results did not load in time. "
                "Refreshing this page once..."
            )

            driver.refresh()

            rows = get_result_rows(
                driver,
                wait,
            )

        print(
            f"Rows returned by portal: {len(rows)}"
        )

        target_row = find_target_row(
            rows
        )

        if target_row is not None:

            print(
                f"Target instrument "
                f"{TARGET_INSTRUMENT}: FOUND"
            )

            return target_row

        # ----------------------------------------------------
        # Loop protection
        # ----------------------------------------------------

        first_row_text = (
            rows[0].text.strip()
            if rows
            else ""
        )

        last_row_text = (
            rows[-1].text.strip()
            if rows
            else ""
        )

        page_signature = (
            f"{first_row_text}|{last_row_text}"
        )

        if page_signature in seen_page_signatures:

            raise RuntimeError(
                "Greenville returned the same result page "
                "again after the offset changed. "
                "Stopping to avoid an infinite pagination loop."
            )

        seen_page_signatures.add(
            page_signature
        )

        if not rows:

            break

        # Advance by what Greenville actually returned,
        # not blindly by 250.
        offset += len(rows)

    raise RuntimeError(
        f"Could not locate instrument "
        f"{TARGET_INSTRUMENT} after scanning "
        f"the available DEED result pages."
    )


def open_detail_page(
    driver: WebDriver,
    wait: WebDriverWait,
) -> str:
    """
    Locate the known deed, navigate to its document-detail route,
    and wait until Greenville has rendered the actual Summary
    content.

    Returns the rendered detail-page body text.
    """

    target_row = locate_target_record(
        driver,
        wait,
    )

    navigate_from_target_row(
        driver,
        wait,
        target_row,
    )

    print()
    print("Detail route reached.")
    print(
        f"Current URL: {driver.current_url}"
    )

    print(
        "Waiting for Greenville detail "
        "content to render..."
    )

    body_text = wait_for_detail_content(
        driver,
        timeout=45,
    )

    print(
        "Detail content rendered successfully."
    )

    return body_text

def wait_for_detail_content(
    driver: WebDriver,
    timeout: int = 45,
) -> str:
    """
    Wait until Greenville has actually rendered the document
    summary after navigation to a /doc/ route.

    The portal is JavaScript-driven, so a URL change alone does
    not mean the detail data has finished loading.

    Returns the rendered body text once the expected document
    summary is available.
    """

    detail_wait = WebDriverWait(
        driver,
        timeout,
    )

    def detail_is_ready(current_driver):
        try:
            body = current_driver.find_element(
                By.TAG_NAME,
                "body",
            )

            body_text = body.text.strip()

            has_instrument = (
                TARGET_INSTRUMENT in body_text
            )

            has_detail_labels = (
                "Instrument Number" in body_text
                and "Consideration" in body_text
                and "Number of Pages" in body_text
            )

            has_party_section = (
                "Parties" in body_text
                or EXPECTED_GRANTOR in body_text
            )

            if (
                has_instrument
                and has_detail_labels
                and has_party_section
            ):
                return body_text

            return False

        except Exception:
            return False

    try:
        return detail_wait.until(
            detail_is_ready
        )

    except TimeoutException:

        debug_html_path = (
            LOG_DIR
            / "greenville_step7c_detail_timeout.html"
        )

        debug_text_path = (
            LOG_DIR
            / "greenville_step7c_detail_timeout.txt"
        )

        debug_html_path.write_text(
            driver.page_source,
            encoding="utf-8",
        )

        try:
            body_text = driver.find_element(
                By.TAG_NAME,
                "body",
            ).text

        except Exception:
            body_text = ""

        debug_text_path.write_text(
            body_text,
            encoding="utf-8",
        )

        raise RuntimeError(
            "Greenville document route opened, but the "
            "detail Summary panel did not finish rendering "
            f"within {timeout} seconds.\n"
            f"HTML saved: {debug_html_path}\n"
            f"Text saved: {debug_text_path}"
        )

# ============================================================
# DETAIL EXTRACTION
# ============================================================

def regex_value(
    text: str,
    pattern: str,
) -> str:
    """
    Return the first captured regex value or an empty string.
    """

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    return match.group(1).strip()

def extract_detail(
    driver: WebDriver,
    body_text: str | None = None,
) -> dict:
    """
    Extract the Greenville document Summary fields.

    The primary source is rendered page text because Greenville's
    new portal uses dynamic JavaScript markup that may change
    implementation details while preserving the visible labels.

    Raw source URL is retained for traceability.
    """

    if body_text is None:

        body_text = driver.find_element(
            By.TAG_NAME,
            "body",
        ).text

    body_text = body_text.strip()

    # Preserve evidence for development/debugging.
    detail_text_path = (
        LOG_DIR
        / f"greenville_step7c_{TARGET_INSTRUMENT}_detail.txt"
    )

    detail_html_path = (
        LOG_DIR
        / f"greenville_step7c_{TARGET_INSTRUMENT}_detail.html"
    )

    detail_text_path.write_text(
        body_text,
        encoding="utf-8",
    )

    detail_html_path.write_text(
        driver.page_source,
        encoding="utf-8",
    )

    def value_after_label(
        label: str,
    ) -> str:
        """
        Extract the visible value immediately following a known
        Summary label.

        Handles both:
            Label: value

        and:
            Label:
            value
        """

        pattern = (
            rf"{re.escape(label)}"
            rf"\s*:?\s*"
            rf"([^\r\n]+)"
        )

        match = re.search(
            pattern,
            body_text,
            flags=re.IGNORECASE,
        )

        if not match:
            return ""

        value = match.group(1).strip()

        # Prevent accidentally treating another known label
        # as the value of an empty field.
        known_labels = {
            "instrument number",
            "recorded date",
            "book",
            "page",
            "consideration",
            "satisfied",
            "number of pages",
            "parties",
            "marginal references",
            "legal description",
        }

        if value.lower().rstrip(":") in known_labels:
            return ""

        return value

    instrument_number = value_after_label(
        "Instrument Number"
    )

    consideration = value_after_label(
        "Consideration"
    )

    book = value_after_label(
        "Book"
    )

    page = value_after_label(
        "Page"
    )

    number_of_pages = value_after_label(
        "Number of Pages"
    )

    expected_grantor_present = (
        EXPECTED_GRANTOR.upper()
        in body_text.upper()
    )

    expected_grantee_present = (
        EXPECTED_GRANTEE.upper()
        in body_text.upper()
    )

    return {
        "instrument_number": instrument_number,
        "consideration": consideration,
        "book": book,
        "page": page,
        "number_of_pages": number_of_pages,
        "source_url": driver.current_url,
        "expected_grantor_present":
            expected_grantor_present,
        "expected_grantee_present":
            expected_grantee_present,
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_detail(
    detail: dict[str, str | bool],
) -> None:
    """
    Validate the automated extraction against the manually
    confirmed Greenville control record.
    """

    errors: list[str] = []

    checks = {
        "instrument_number": (
            TARGET_INSTRUMENT,
            detail["instrument_number"],
        ),
        "consideration": (
            EXPECTED_CONSIDERATION,
            detail["consideration"],
        ),
        "book": (
            EXPECTED_BOOK,
            detail["book"],
        ),
        "page": (
            EXPECTED_PAGE,
            detail["page"],
        ),
        "grantor_present": (
    True,
    detail["expected_grantor_present"],
),
"grantee_present": (
    True,
    detail["expected_grantee_present"],
),
    }

    for field_name, (
        expected,
        actual,
    ) in checks.items():

        if expected != actual:
            errors.append(
                f"{field_name}: "
                f"expected {expected!r}, "
                f"got {actual!r}"
            )

    if errors:
        joined_errors = "\n".join(
            f"- {error}"
            for error in errors
        )

        raise RuntimeError(
            "STEP 7C validation failed:\n"
            f"{joined_errors}"
        )


# ============================================================
# EVIDENCE OUTPUT
# ============================================================

def save_evidence(
    driver: WebDriver,
    detail: dict[str, str | bool],
) -> None:
    """
    Save reproducible evidence from the controlled test.
    """

    json_path = (
        RAW_DATA_DIR
        / f"greenville_{TARGET_INSTRUMENT}_detail.json"
    )

    screenshot_path = (
        LOG_DIR
        / f"greenville_step7c_{TARGET_INSTRUMENT}.png"
    )

    html_path = (
        LOG_DIR
        / f"greenville_step7c_{TARGET_INSTRUMENT}.html"
    )

    json_path.write_text(
        json.dumps(
            detail,
            indent=2,
        ),
        encoding="utf-8",
    )

    driver.save_screenshot(
        str(screenshot_path)
    )

    html_path.write_text(
        driver.page_source,
        encoding="utf-8",
    )

    print()
    print("Evidence saved:")
    print(f"JSON:       {json_path}")
    print(f"Screenshot: {screenshot_path}")
    print(f"HTML:       {html_path}")


# ============================================================
# MAIN TEST
# ============================================================

def main() -> None:

    print()
    print("=" * 60)
    print("GREENVILLE STEP 7C - DETAIL PAGE EXTRACTION")
    print("=" * 60)
    print(f"Test date:         {TEST_DATE}")
    print(f"Target instrument: {TARGET_INSTRUMENT}")
    print(
        f"Expected value:     "
        f"{EXPECTED_CONSIDERATION}"
    )

    driver = build_driver()

    wait = WebDriverWait(
        driver,
        60,
    )

    try:

        detail_body_text = open_detail_page(
    driver,
    wait,
)

        print()
        print("Detail page opened.")
        print(f"Current URL: {driver.current_url}")
        print(f"Page title:  {driver.title}")

        detail = extract_detail(
    driver,
    body_text=detail_body_text,
)

        print()
        print("=" * 60)
        print("EXTRACTED DETAIL")
        print("=" * 60)

        for key, value in detail.items():
            print(
                f"{key:26}: {value}"
            )

        print("=" * 60)

        validate_detail(
            detail
        )

        print()
        print("=" * 60)
        print("STEP 7C VALIDATION")
        print("=" * 60)
        print(
            "PASS: known Greenville deed detail "
            "was extracted correctly."
        )
        print(
            f"PASS: consideration = "
            f"{detail['consideration']}"
        )

        save_evidence(
            driver,
            detail,
        )

        print()
        print("=" * 60)
        print("STEP 7C RUN COMPLETE")
        print("=" * 60)

        input(
            "\nPress ENTER when ready "
            "to close Chrome..."
        )

    except Exception:

        failure_screenshot = (
            LOG_DIR
            / "greenville_step7c_failure.png"
        )

        try:
            driver.save_screenshot(
                str(failure_screenshot)
            )

            print()
            print(
                "Failure screenshot saved:"
            )
            print(
                failure_screenshot
            )

        except Exception:
            pass

        raise

    finally:

        driver.quit()

        print()
        print("Browser closed.")


if __name__ == "__main__":
    main()