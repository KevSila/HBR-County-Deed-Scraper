# Greenville County Deed Scraper - Discovery Notes

## Purpose

Document the Greenville County Register of Deeds portal behaviour,
data availability, access requirements, automation constraints, and
validated scraper behaviour.

These notes describe observed portal behaviour and are intended to
support development and eventual deployment of the HBR county deed
scraper.

---

## Current Portal

### Greenville County Cloud Search

Portal:

https://greenville.sc.publicsearch.us/

Department:

Real Property

### Authentication

The portal supports authenticated user sessions.

The scraper does not store usernames or passwords in source code.
Authentication is currently performed manually in the scraper's
persistent Chrome profile, after which the browser session/cookies can
be reused.

Credentials and browser-profile data must never be committed to Git.

---

## Network / Geographic Access

Access behaviour varies between Greenville County entry points.

During development from the current location, the Greenville County
Register of Deeds entry route could return an HTTP 403 response without
a VPN, while access succeeded when routed through a US VPN endpoint.

The scraper itself should not contain Windscribe-specific or other
vendor-specific VPN logic.

Network routing, proxies, VPN access, or deployment-region requirements
should instead be treated as infrastructure/deployment configuration.

The application should therefore remain portable between developer,
server, container, or cloud environments.

---

## Portal Systems Evaluated

### Legacy Register of Deeds Viewer

The legacy Greenville County records viewer was manually inspected.

Observed functionality included:

- recorded-date searching
- document-type filtering
- grantor and grantee information
- instrument number
- book and page
- legal description
- consideration on applicable documents
- scanned document images

No separate `SPECIAL WARRANTY DEED` search filter was identified during
manual inspection.

Documents indexed as `DEED` may contain more specific deed terminology
inside the recorded document itself.

### New Cloud Search Portal

The newer Cloud Search portal was selected for the current automation
prototype because it provides a more structured search-results interface
and predictable document-detail routes.

Observed search-result fields include:

- Instrument Number
- Book
- Page
- Recorded Date
- Document Type
- Grantor
- Grantee
- Legal Description
- Satisfied status where applicable

Observed detail-page fields include:

- Instrument Number
- Recorded Date
- Book
- Page
- Consideration
- Number of Pages
- Grantor / Grantee parties
- document image
- legal-description information
- marginal-reference information where available

Some fields such as parcel/TMS number, property address, and exact deed
subtype may require document-level enrichment rather than relying only
on the search-results table.

---

## SPECIAL WARRANTY DEED Observation

Neither the legacy viewer nor the new Cloud Search portal exposed
`SPECIAL WARRANTY DEED` as a distinct search filter during discovery.

The portal exposes the broader `DEED` document classification.

More specific deed types may instead appear in the recorded document
text or document image.

For that reason, the current scraper searches the indexed `DEED`
category and preserves the document-detail route so that deed subtype
classification can be added at the document-enrichment stage if HBR
requires it.

This avoids incorrectly assuming that `SPECIAL WARRANTY DEED` is a
portal-level searchable document type.

---

## Search Behaviour

The Cloud Search portal supports date-based searching and document-type
filtering.

During testing, portal responsiveness was inconsistent. Some searches
initially remained in a loading state or timed out and subsequently
worked after retry/refresh.

Automation should therefore use explicit waits and bounded retry logic
instead of assuming that navigation or results are immediately ready.

The scraper must also not depend on a user's manually selected
"Results Per Page" preference.

Pagination/page-size handling must remain inside the scraper logic so
the same implementation works when a browser or account defaults to
50, 250, or another supported result count.

---

## Controlled Validation Sample

### Search-result validation

Test date:

09/21/2026

Document category:

DEED

Expected result count:

106

Observed scraper result:

106 structured records extracted successfully.

Known instrument used for validation:

2026064314

Search-level values:

- Instrument Number: 2026064314
- Book: 2803
- Page: 704
- Recorded Date: 09/21/2026
- Document Type: DEED
- Grantor: D R HORTON INC
- Grantee: BATES TRICIA ANNE
- Legal Description: Subdivision: ADAMS GLEN

This record was selected only as a deterministic development fixture
for validating the scraper. It is not a business-rule threshold or an
HBR-selected transaction.

---

## Detail-Page Validation

The scraper successfully followed instrument `2026064314` from the
search-results table to its document-detail page.

Validated detail values:

- Instrument Number: 2026064314
- Consideration: $365,000.00
- Book: 2803
- Page: 704
- Number of Pages: 2
- Expected Grantor Present: Yes
- Expected Grantee Present: Yes

The $365,000 value is a test fixture used to verify that detail-page
consideration extraction works correctly. It should not be interpreted
as an HBR filtering rule.

The detail-page test also saves local evidence for debugging:

- structured JSON
- screenshot
- rendered HTML

These generated artifacts are intentionally excluded from Git.

---

## Search Export Observation

The Cloud Search interface provides an `Export all Results` workflow.

During manual testing, the export behaved like a zero-dollar order and
generated a PDF through the account order-history workflow.

Because this is PDF-oriented rather than a clean tabular data export,
the current scraper extracts structured values directly from the
rendered search-results table rather than depending on the portal's
export feature.

---

## Current Automation Architecture

The Greenville prototype currently separates discovery/testing into:

- `browser_test.py`
  - validates Chrome startup and persistent browser-profile behaviour

- `search_test.py`
  - validates authenticated Greenville search access and known result sets

- `extract_results_test.py`
  - extracts structured search-result rows and validates record counts

- `detail_test.py`
  - follows a known result to the document page and validates
    document-detail fields such as consideration

Generated data is stored only in ignored local directories.

The persistent Chrome profile is also ignored from Git.

---

## Git / Security Rules

The repository excludes:

- `.venv/`
- `.env`
- `.env.*`
- `.chrome-profile/`
- Python cache files
- scraped raw data
- processed data
- review data
- runtime logs
- screenshots
- rendered HTML evidence
- private key files

No Greenville username or password should be placed in source code,
documentation, commits, screenshots intended for sharing, or repository
configuration.

---

## Deployment Considerations

The current implementation proves the data-acquisition workflow but is
not yet the final production scraper.

Before deployment, the Greenville implementation should be refactored
from controlled test scripts into reusable county modules with:

- configuration-driven date ranges
- reusable browser/session handling
- pagination independent of browser preferences
- bounded retries and explicit waits
- structured logging
- validation rules
- deterministic output schemas
- failure handling
- resumability where practical
- automated tests
- deployment/network-access documentation

VPN or proxy requirements should remain an infrastructure concern rather
than being hard-coded to a specific VPN provider.

---

## Current Status

Validated:

- Chrome automation
- persistent authenticated session
- Greenville Cloud Search access
- DEED date filtering
- search-result discovery
- full 106-record extraction for the controlled test date
- structured CSV output
- known-record lookup
- detail-page navigation
- consideration extraction
- book/page extraction
- grantor/grantee validation
- JSON / HTML / screenshot evidence generation
- Git exclusions for local browser state and generated data

Next development stage:

Convert the proven Greenville test workflow into reusable scraper
components, expand document/detail extraction as required by HBR's
target schema, and validate the workflow across additional dates and
record volumes before production integration.

---

## Verified Results Navigation — 2026-09-26

The authenticated Greenville Advanced Search uses:

`department=RP&docTypes=DEED&recordedDateRange=YYYYMMDD%2CYYYYMMDD&searchType=advancedSearch`

For the controlled 2026-09-21 DEED search, the portal reported 106 results.

Observed navigation behavior:

| Action | Displayed range | URL parameters |
|---|---|---|
| Initial search | 1–50 of 106 | No limit or offset |
| Select 250 through the UI | 1–106 of 106 | limit=250 |
| Select 50 through the UI | 1–50 of 106 | limit=50 |
| Next page | 51–100 of 106 | limit=50, offset=50 |
| Final page | 101–106 of 106 | limit=50, offset=100 |

The known control instrument 2026064314 was present in the
complete 250-row view.

Previously, manually constructing a URL with limit=250 and offset=0
produced No Results Found. The precise cause has not been established.
Do not assume that manually supplied pagination parameters behave
identically to navigation generated by the portal interface.

Production navigation should use verified portal controls, check
the displayed result range, and guard against duplicate or missing
records.

The refactored search now also distinguishes results, sign-in,
Forbidden, no-results, and loading states. Its live regression
successfully detected the 106-record total.

These observations are specific to Greenville PublicSearch and
should not be assumed to apply to the other county portals.

---

## Complete Results Regression — 2026-09-26

The refactored Greenville workflow successfully collected all
106 DEED records for the historical 2026-09-21 test date.

Verified live navigation:
- Page 1: records 1–50
- Page 2: records 51–100
- Page 3: records 101–106

The collection returned 106 unique instrument numbers and found
control instrument 2026064314, book 2803, page 704.

The regression reused the original dynamic table-column parser.
It did not create or overwrite a CSV file.

Offline validation: 37 unit tests passed.

Remaining work:
- Extract the table parser into a standalone Greenville module.
- Add focused tests for field mapping and malformed rows.
- Validate the complete record schema.
- Implement safe CSV export.
- Broaden live testing beyond the historical fixture.
- Finalize authentication and deployment/network requirements.
