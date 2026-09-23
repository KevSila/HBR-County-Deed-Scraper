# HBR County Deed Scraper

Python-based deed/closing scraper project for Home Builders Research.

## Current Phase
Greenville County discovery and proof of concept.

Target document type: **SPECIAL WARRANTY DEED**

Initial historical target: **2026 onward**

## Project Principles
- One reusable scraper framework with county-specific modules.
- Preserve county and source attribution on every record.
- Keep raw, processed, and review outputs separate.
- Validate and flag duplicates before export/import.
- Keep credentials, keys, and scraped data out of Git.
- Validate locally before HBR/Upstate integration.

## First Checkpoint
1. Greenville portal discovery notes.
2. Small manually validated sample.
3. Source-to-HBR field mapping.
4. Validation and QC findings.
5. Technical blockers or limitations.

Production/database/EC2 integration will follow only after the local Greenville workflow is validated.
