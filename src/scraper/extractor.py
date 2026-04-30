import logging
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger("devin_indexer.extractor")

_WAIT_TIMEOUT = 15
_REPO_CARD_SELECTOR = "a[href*='/settings/indexing/repositories/']"
_REPO_NAME_SELECTOR = ".text-text-primary.text-13.truncate"
_REPO_OWNER_SELECTOR = ".text-text-secondary.text-13.truncate"

# Branch list on repository detail page
_ADD_BRANCH_BTN_XPATH = "//button[@role='combobox' and @aria-haspopup='dialog']"
_INDEXED_BRANCH_XPATH = (
    "//div[contains(@class,'flex') and contains(@class,'items-center')"
    " and .//svg[contains(@class,'text-text-green')]]"
    "//span[contains(@class,'text-text-primary') and contains(@class,'mr-auto')]"
)


def wait_for_repos(driver: webdriver.Edge, timeout: int = _WAIT_TIMEOUT) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, _REPO_CARD_SELECTOR))
        )
        return True
    except TimeoutException:
        logger.warning("Repository list did not appear within timeout")
        return False


def extract_repo_list(driver: webdriver.Edge) -> list[dict]:
    cards = driver.find_elements(By.CSS_SELECTOR, _REPO_CARD_SELECTOR)
    repositories = []
    for card in cards:
        try:
            name = card.find_element(By.CSS_SELECTOR, _REPO_NAME_SELECTOR).text.strip()
            owner = card.find_element(By.CSS_SELECTOR, _REPO_OWNER_SELECTOR).text.strip()
            url = card.get_attribute("href") or ""
            if not name or not url:
                continue
            has_indexed = _card_has_indexed_branches(card)
            repositories.append({
                "name": name,
                "owner": owner,
                "url": url,
                "has_indexed_branches": has_indexed,
            })
        except NoSuchElementException as e:
            logger.debug(f"Skipping malformed card: {e}")
    logger.debug(f"Extracted {len(repositories)} repositories from page")
    return repositories


def _card_has_indexed_branches(card) -> bool:
    """Checks if the repo card shows 'N branch indexed' indicator (not 'Not indexed.')."""
    try:
        indicators = card.find_elements(
            By.XPATH, ".//*[contains(., 'branch indexed') and not(contains(., 'Not indexed'))]"
        )
        return bool(indicators)
    except Exception:
        return False


def extract_indexed_branches(driver: webdriver.Edge) -> set[str]:
    """Returns names of branches that already have the green checkmark (indexed)."""
    indexed: set[str] = set()
    try:
        WebDriverWait(driver, _WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, _ADD_BRANCH_BTN_XPATH))
        )
    except TimeoutException:
        logger.warning("Branch section did not appear within timeout")
        return indexed

    time.sleep(1)

    spans = driver.find_elements(By.XPATH, _INDEXED_BRANCH_XPATH)
    for span in spans:
        name = span.text.strip()
        if name:
            indexed.add(name)

    logger.debug(f"Indexed branches: {indexed}")
    return indexed


def take_screenshot(driver: webdriver.Edge, filename: str) -> None:
    try:
        driver.save_screenshot(filename)
        logger.info(f"Screenshot saved: {filename}")
    except Exception as e:
        logger.debug(f"Screenshot failed: {e}")
