from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


GREENVILLE_URL = "https://greenville.sc.publicsearch.us/"

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CHROME_PROFILE = PROJECT_ROOT / ".chrome-profile"


def main():
    options = Options()

    options.binary_location = (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    )

    # Dedicated Chrome profile for HBR automation.
    options.add_argument(
        f"--user-data-dir={CHROME_PROFILE}"
    )

    options.add_argument("--start-maximized")

    print("Starting HBR automation Chrome...")
    print(f"Profile: {CHROME_PROFILE}")

    driver = webdriver.Chrome(options=options)

    try:
        print(f"Opening {GREENVILLE_URL}")
        driver.get(GREENVILLE_URL)

        print("Page title:", driver.title)
        print("Current URL:", driver.current_url)

        input(
            "\nBrowser will remain open for setup/testing.\n"
            "Press ENTER here when you want to close it..."
        )

    finally:
        driver.quit()
        print("Browser test complete.")


if __name__ == "__main__":
    main()