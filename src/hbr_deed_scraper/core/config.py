"""Shared configuration for the HBR county deed scrapers."""

from dataclasses import dataclass
from pathlib import Path


# Resolve paths relative to the repository, not the terminal's
# current working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
REVIEW_DATA_DIR = PROJECT_ROOT / "data" / "review"
LOG_DIR = PROJECT_ROOT / "logs"


@dataclass(frozen=True, slots=True)
class BrowserConfig:
    """Configuration for an isolated Selenium Chrome session."""

    profile_dir: Path = PROJECT_ROOT / ".chrome-profile"
    headless: bool = False
