
"""Collect complete Greenville search results across portal pages."""

from collections.abc import Callable

from .pagination import (
    PaginationError,
    advance_to_next_page,
    wait_for_page_range,
)


def collect_result_pages(
    driver,
    extract_page: Callable,
    *,
    max_pages: int = 1000,
) -> list[dict]:
    """Collect and validate records from every Greenville results page.

    extract_page is a callback that receives the current driver and
    returns structured records from the currently displayed table.

    No partial dataset is returned if validation fails.
    """

    if max_pages < 1:
        raise ValueError("max_pages must be at least 1.")

    current = wait_for_page_range(driver)

    expected_total = current.total
    records = []
    seen_instruments = set()
    page_number = 0

    while True:
        page_number += 1

        print(
            f"Collecting page {page_number}: "
            f"{current.start}-{current.end} of {current.total}"
        )

        page_records = extract_page(driver)

        if not isinstance(page_records, list):
            raise PaginationError(
                "The page extractor must return a list of records."
            )

        if len(page_records) != current.count:
            raise PaginationError(
                f"Page {page_number} row-count mismatch: "
                f"expected {current.count}, "
                f"extracted {len(page_records)}."
            )

        for record in page_records:
            if not isinstance(record, dict):
                raise PaginationError(
                    "The page extractor returned a non-dictionary record."
                )

            instrument = record.get("instrument_number")

            if not isinstance(instrument, str) or not instrument.strip():
                raise PaginationError(
                    f"Page {page_number} contains a record "
                    "without an instrument number."
                )

            instrument = instrument.strip()

            if instrument in seen_instruments:
                raise PaginationError(
                    "Duplicate instrument encountered during "
                    f"pagination: {instrument}."
                )

            seen_instruments.add(instrument)

        records.extend(page_records)

        if current.is_last:
            break

        if page_number >= max_pages:
            raise PaginationError(
                f"Pagination exceeded the configured limit "
                f"of {max_pages} pages."
            )

        following = advance_to_next_page(driver, current)

        if following is None:
            raise PaginationError(
                "Greenville ended pagination before reaching "
                "the reported result total."
            )

        current = following

    if len(records) != expected_total:
        raise PaginationError(
            "Complete dataset count mismatch: "
            f"portal reported {expected_total}, "
            f"extracted {len(records)}."
        )

    print(
        f"Collection complete: {len(records)} unique records "
        f"across {page_number} page(s)."
    )

    return records
