from pathlib import Path
import csv
import re
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

CHROME_PROFILE = PROJECT_ROOT / ".chrome-profile"

LOGS_DIR = PROJECT_ROOT / "logs"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


# Known Greenville test date
TEST_DATE_DISPLAY = "09/21/2026"
TEST_DATE_URL = "20260921"

# Known manually verified record
TARGET_INSTRUMENT = "2026064314"

# We already manually confirmed Greenville has 106 DEED records
# for this test date.
EXPECTED_RESULT_COUNT = 106


# ============================================================
# URL
# ============================================================

RESULTS_URL = (
    "https://greenville.sc.publicsearch.us/results?"
    "_docTypes=DEED"
    "&department=RP"
    "&keywordSearch=false"
    "&limit=250"
    "&offset=0"
    f"&recordedDateRange={TEST_DATE_URL}%2C{TEST_DATE_URL}"
    "&searchOrText=false"
    "&searchType=quickSearch"
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    """
    Normalize whitespace from text extracted from the page.
    """

    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def normalize_header(value):
    """
    Normalize table header names so that slightly different
    Greenville labels can still be matched.
    """

    value = clean_text(value).upper()

    value = value.replace("#", "NUMBER")

    return value


def start_driver():
    """
    Start Chrome using the dedicated HBR automation profile.

    This profile is intentionally separate from the user's normal
    Chrome profile and preserves Greenville login cookies.
    """

    options = Options()

    options.add_argument(
        f"--user-data-dir={CHROME_PROFILE}"
    )

    options.add_argument("--start-maximized")

    # Keep browser visible while developing/testing.
    # Do NOT enable headless mode yet.

    print("Starting Greenville Chrome...")
    print(f"Chrome profile: {CHROME_PROFILE}")

    driver = webdriver.Chrome(options=options)

    return driver


# ============================================================
# RESULT TABLE DISCOVERY
# ============================================================

def find_results_table(driver):
    """
    Find the Greenville result table rather than assuming
    that the first <table> on the page is always the correct one.
    """

    tables = driver.find_elements(By.TAG_NAME, "table")

    print(f"Tables detected on page: {len(tables)}")

    for table in tables:

        text = clean_text(table.text).upper()

        if (
            "BOOK" in text
            and "PAGE" in text
            and "GRANTOR" in text
            and "GRANTEE" in text
        ):
            return table

    raise RuntimeError(
        "Could not identify the Greenville results table."
    )


# ============================================================
# RESULT EXTRACTION
# ============================================================

def extract_rows(driver):
    """
    Extract Greenville search-result rows.

    IMPORTANT:
    We discover column positions from the page headers instead of
    assuming fixed indexes. This prevents the column-shift issue
    seen in the first Step 7B test.
    """

    records = []

    table = find_results_table(driver)

    # --------------------------------------------------------
    # Discover header positions
    # --------------------------------------------------------

    headers = table.find_elements(
        By.CSS_SELECTOR,
        "thead th"
    )

    # Fallback in case the site does not expose a normal thead.
    if not headers:
        headers = table.find_elements(
            By.CSS_SELECTOR,
            "tr th"
        )

    header_map = {}

    print()
    print("=" * 60)
    print("DETECTED GREENVILLE TABLE COLUMNS")
    print("=" * 60)

    for index, header in enumerate(headers):

        header_text = clean_text(header.text)
        normalized = normalize_header(header_text)

        print(
            f"{index:>2}: {repr(header_text)}"
        )

        if normalized:
            header_map[normalized] = index

    print("=" * 60)
    print()

    # --------------------------------------------------------
    # Resolve useful columns
    # --------------------------------------------------------

    def column_index(*possible_names):

        for name in possible_names:

            normalized = normalize_header(name)

            if normalized in header_map:
                return header_map[normalized]

        return None

    instrument_index = column_index(
        "INST NUMBER",
        "INSTRUMENT NUMBER",
        "INSTRUMENT #",
    )

    book_index = column_index(
        "BOOK",
    )

    page_index = column_index(
        "PAGE",
    )

    recorded_date_index = column_index(
        "RECORDED DATE",
        "FILED",
    )

    document_type_index = column_index(
        "DOC TYPE",
        "DOCUMENT",
        "DOCUMENT TYPE",
    )

    grantor_index = column_index(
        "GRANTOR",
    )

    grantee_index = column_index(
        "GRANTEE",
    )

    legal_description_index = column_index(
        "LEGAL DESCRIPTION",
        "LEGAL DESC",
    )

    print("RESOLVED COLUMN POSITIONS")
    print("-" * 60)
    print(f"instrument_number : {instrument_index}")
    print(f"book              : {book_index}")
    print(f"page              : {page_index}")
    print(f"recorded_date     : {recorded_date_index}")
    print(f"document_type     : {document_type_index}")
    print(f"grantor           : {grantor_index}")
    print(f"grantee           : {grantee_index}")
    print(f"legal_description : {legal_description_index}")
    print("-" * 60)
    print()

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    required_columns = {
        "instrument_number": instrument_index,
        "book": book_index,
        "page": page_index,
        "recorded_date": recorded_date_index,
        "document_type": document_type_index,
        "grantor": grantor_index,
        "grantee": grantee_index,
    }

    missing_columns = [
        name
        for name, index in required_columns.items()
        if index is None
    ]

    if missing_columns:

        raise RuntimeError(
            "Could not resolve required Greenville columns: "
            + ", ".join(missing_columns)
        )

    # --------------------------------------------------------
    # Obtain result rows
    # --------------------------------------------------------

    rows = table.find_elements(
        By.CSS_SELECTOR,
        "tbody tr"
    )

    # Fallback
    if not rows:
        rows = table.find_elements(
            By.TAG_NAME,
            "tr"
        )

    print(
        f"HTML result rows detected: {len(rows)}"
    )

    # --------------------------------------------------------
    # Extract each record
    # --------------------------------------------------------

    for row in rows:

        cells = row.find_elements(
            By.TAG_NAME,
            "td"
        )

        if not cells:
            continue

        row_text = clean_text(row.text)

        # Greenville 2026 instrument numbers follow this pattern.
        instrument_match = re.search(
            r"\b20\d{8}\b",
            row_text,
        )

        if not instrument_match:
            continue

        instrument_number = instrument_match.group(0)

        def value_at(index):

            if index is None:
                return ""

            if index >= len(cells):
                return ""

            return clean_text(
                cells[index].text
            )

        # ----------------------------------------------------
        # Attempt to capture detail-page URL
        # ----------------------------------------------------

        source_url = ""

        links = row.find_elements(
            By.TAG_NAME,
            "a"
        )

        for link in links:

            link_text = clean_text(
                link.text
            )

            href = (
                link.get_attribute("href")
                or ""
            )

            if instrument_number in link_text:

                # Only save actual navigable URLs.
                if href.startswith("http"):
                    source_url = href

                break

        record = {
            "instrument_number": instrument_number,
            "book": value_at(book_index),
            "page": value_at(page_index),
            "recorded_date": value_at(recorded_date_index),
            "document_type": value_at(document_type_index),
            "grantor": value_at(grantor_index),
            "grantee": value_at(grantee_index),
            "legal_description": value_at(
                legal_description_index
            ),
            "source_url": source_url,
        }

        records.append(record)

    return records


# ============================================================
# CSV EXPORT
# ============================================================


def save_csv(records):
    """
    Save extracted search-level data to data/raw.

    If the normal output file is currently locked
    (for example, open in Excel), save a timestamped
    alternative instead of crashing the scraper.
    """

    base_output_path = (
        RAW_DATA_DIR
        / "greenville_2026-09-21_deed_results.csv"
    )

    fieldnames = [
        "instrument_number",
        "book",
        "page",
        "recorded_date",
        "document_type",
        "grantor",
        "grantee",
        "legal_description",
        "source_url",
    ]

    def write_file(path):

        with path.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as csv_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
            )

            writer.writeheader()
            writer.writerows(records)

    try:

        write_file(base_output_path)

        print(
            f"CSV written successfully:"
        )
        print(
            base_output_path
        )

        return base_output_path

    except PermissionError:

        timestamp = time.strftime(
            "%Y%m%d_%H%M%S"
        )

        fallback_path = (
            RAW_DATA_DIR
            / (
                "greenville_2026-09-21_deed_results_"
                f"{timestamp}.csv"
            )
        )

        print()
        print(
            "WARNING: Primary CSV is locked."
        )
        print(
            "It may currently be open in Excel."
        )
        print(
            "Saving this run under a new filename instead."
        )

        write_file(fallback_path)

        print(
            f"Fallback CSV written successfully:"
        )
        print(
            fallback_path
        )

        return fallback_path


# ============================================================
# ARTIFACTS
# ============================================================

def save_debug_artifacts(driver):
    """
    Save screenshot and HTML so we can inspect exactly what
    Selenium saw during the run.
    """

    screenshot_path = (
        LOGS_DIR
        / "greenville_step7b_extract.png"
    )

    html_path = (
        LOGS_DIR
        / "greenville_step7b_extract.html"
    )

    driver.save_screenshot(
        str(screenshot_path)
    )

    html_path.write_text(
        driver.page_source,
        encoding="utf-8",
    )

    print()
    print(f"Screenshot saved: {screenshot_path}")
    print(f"HTML saved:       {html_path}")


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print()
    print("=" * 60)
    print("GREENVILLE STEP 7B - SEARCH RESULT EXTRACTION")
    print("=" * 60)

    print(f"Test date:         {TEST_DATE_DISPLAY}")
    print(f"Target instrument: {TARGET_INSTRUMENT}")
    print(f"Expected records:  {EXPECTED_RESULT_COUNT}")
    print()

    driver = start_driver()

    try:

        print("Opening controlled Greenville DEED result set...")
        print(RESULTS_URL)
        print()

        driver.get(
            RESULTS_URL
        )

        wait = WebDriverWait(
            driver,
            40,
        )

        # Wait until known Greenville result content appears.
        wait.until(
            lambda d:
            TARGET_INSTRUMENT in d.page_source
            or "106 results" in d.page_source.lower()
        )

        # Give the dynamic grid a moment to finish rendering.
        time.sleep(3)

        print(
            f"Current URL: {driver.current_url}"
        )

        print(
            f"Page title: {driver.title}"
        )

        print()

        records = extract_rows(
            driver
        )

        print()
        print("=" * 60)
        print("STEP 7B VALIDATION")
        print("=" * 60)

        print(
            f"Structured records extracted: {len(records)}"
        )

        if len(records) == EXPECTED_RESULT_COUNT:

            print(
                f"PASS: extracted all "
                f"{EXPECTED_RESULT_COUNT} records."
            )

        else:

            print(
                f"WARNING: expected "
                f"{EXPECTED_RESULT_COUNT}, "
                f"but extracted {len(records)}."
            )

        # ----------------------------------------------------
        # Validate known instrument
        # ----------------------------------------------------

        target_record = next(
            (
                record
                for record in records
                if record["instrument_number"]
                == TARGET_INSTRUMENT
            ),
            None,
        )

        print()

        if target_record:

            print(
                "Known record successfully parsed:"
            )

            print("-" * 60)

            for key, value in target_record.items():

                print(
                    f"{key}: {value}"
                )

            print("-" * 60)

        else:

            print(
                "FAIL: known test instrument "
                f"{TARGET_INSTRUMENT} was not extracted."
            )

        # ----------------------------------------------------
        # Preview first few records
        # ----------------------------------------------------

        print()
        print("FIRST 5 EXTRACTED RECORDS")
        print("-" * 60)

        for record in records[:5]:

            print(
                record
            )

        print("-" * 60)

        # ----------------------------------------------------
        # Save CSV
        # ----------------------------------------------------

        csv_path = save_csv(
            records
        )

        print()
        print(
            f"CSV saved to:"
        )
        print(
            csv_path
        )

        # ----------------------------------------------------
        # Debug files
        # ----------------------------------------------------

        save_debug_artifacts(
            driver
        )

        print()
        print("=" * 60)
        print("STEP 7B RUN COMPLETE")
        print("=" * 60)

        input(
            "\nPress ENTER when ready to close Chrome..."
        )

    finally:

        driver.quit()

        print(
            "Browser closed."
        )


if __name__ == "__main__":
    main()