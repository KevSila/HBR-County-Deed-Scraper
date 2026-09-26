"""Tests for reusable browser configuration."""

import unittest
from pathlib import Path
from unittest.mock import patch

from hbr_deed_scraper.core.browser import (
    build_chrome_options,
    create_chrome_driver,
)
from hbr_deed_scraper.core.config import (
    BrowserConfig,
    PROJECT_ROOT,
)


class BrowserConfigurationTests(unittest.TestCase):

    def test_default_profile_is_project_local(self):
        config = BrowserConfig()

        self.assertEqual(
            config.profile_dir,
            PROJECT_ROOT / ".chrome-profile",
        )

        self.assertFalse(config.headless)

    def test_browser_uses_configured_profile(self):
        profile = Path("test-automation-profile")

        options = build_chrome_options(
            BrowserConfig(profile_dir=profile)
        )

        self.assertIn(
            f"--user-data-dir={profile.resolve()}",
            options.arguments,
        )

        self.assertIn(
            "--start-maximized",
            options.arguments,
        )

    def test_headless_mode_is_optional(self):
        options = build_chrome_options(
            BrowserConfig(headless=True)
        )

        self.assertIn(
            "--headless=new",
            options.arguments,
        )

        self.assertIn(
            "--window-size=1440,900",
            options.arguments,
        )

    @patch("hbr_deed_scraper.core.browser.webdriver.Chrome")
    def test_driver_factory_uses_chrome_options(self, mock_chrome):
        driver = create_chrome_driver()

        mock_chrome.assert_called_once()

        self.assertIs(
            driver,
            mock_chrome.return_value,
        )


if __name__ == "__main__":
    unittest.main()
