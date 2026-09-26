"""Reusable Selenium Chrome browser setup."""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver

from .config import BrowserConfig


def build_chrome_options(
    config: BrowserConfig | None = None,
) -> Options:
    """Build Chrome options using a dedicated automation profile."""

    settings = config or BrowserConfig()

    options = Options()

    # Keep the automation session separate from the user's
    # normal Chrome profile. Login cookies stay local to this path.
    options.add_argument(
        f"--user-data-dir={settings.profile_dir.resolve()}"
    )

    if settings.headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,900")
    else:
        options.add_argument("--start-maximized")

    return options


def create_chrome_driver(
    config: BrowserConfig | None = None,
) -> WebDriver:
    """Start Chrome with the configured automation profile."""

    options = build_chrome_options(config)

    return webdriver.Chrome(options=options)
