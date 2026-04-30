import json
import logging
import os
import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

logger = logging.getLogger("devin_indexer.session")

_LOGIN_CHECK_SELECTORS = [
    "a[href*='/settings/indexing']",
    "nav",
    "[data-testid='user-menu']",
]


def save_session(driver: webdriver.Edge, filepath: str) -> None:
    cookies = driver.get_cookies()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)
    os.chmod(filepath, 0o600)
    logger.info(f"Session saved to {filepath} ({len(cookies)} cookies)")


def load_session(driver: webdriver.Edge, filepath: str, base_url: str) -> bool:
    if not os.path.exists(filepath):
        logger.debug("No session file found")
        return False

    try:
        with open(filepath, encoding="utf-8") as f:
            cookies = json.load(f)

        driver.get(base_url)
        time.sleep(1)

        for cookie in cookies:
            cookie.pop("sameSite", None)
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.debug(f"Skipped cookie {cookie.get('name')}: {e}")

        driver.refresh()
        time.sleep(2)
        logger.info(f"Session loaded from {filepath}")
        return True
    except Exception as e:
        logger.warning(f"Failed to load session: {e}")
        return False


def is_logged_in(driver: webdriver.Edge) -> bool:
    current_url = driver.current_url
    if "login" in current_url or "auth" in current_url or "signin" in current_url:
        return False
    for selector in _LOGIN_CHECK_SELECTORS:
        try:
            elements = driver.find_elements("css selector", selector)
            if elements:
                return True
        except WebDriverException:
            continue
    return False


def wait_for_login(
    driver: webdriver.Edge,
    target_url: str,
    timeout: int = 300,
    check_interval: int = 3,
) -> bool:
    logger.info("Waiting for manual login... (press Ctrl+C to cancel)")
    elapsed = 0
    while elapsed < timeout:
        if is_logged_in(driver):
            logger.info("Login detected")
            return True
        time.sleep(check_interval)
        elapsed += check_interval
        if elapsed % 30 == 0:
            remaining = timeout - elapsed
            logger.info(f"Still waiting for login... ({remaining}s remaining)")
    logger.error("Login timeout exceeded")
    return False
