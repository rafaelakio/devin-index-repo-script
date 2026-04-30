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
            if name and url:
                repositories.append({"name": name, "owner": owner, "url": url})
        except NoSuchElementException as e:
            logger.debug(f"Skipping malformed card: {e}")
    logger.debug(f"Extracted {len(repositories)} repositories from page")
    return repositories


def extract_branch_list(driver: webdriver.Edge) -> list[dict]:
    """
    Extracts branches from a repository detail page.
    Returns list of dicts: {name, element, indexed}
    """
    branches = []

    # Primary: look for rows that contain branch names alongside index controls
    try:
        WebDriverWait(driver, _WAIT_TIMEOUT).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "[data-branch], [data-testid*='branch']")) > 0
            or len(d.find_elements(By.XPATH, "//tr[contains(@class,'branch') or contains(@data-testid,'branch')]")) > 0
            or len(d.find_elements(By.CSS_SELECTOR, "button[aria-label*='Index'], button[aria-label*='index']")) > 0
        )
    except TimeoutException:
        logger.debug("Timed out waiting for branch-specific elements, proceeding with generic extraction")

    time.sleep(1)

    # Strategy 1: data-branch attribute
    branch_elements = driver.find_elements(By.CSS_SELECTOR, "[data-branch]")
    for el in branch_elements:
        branch_name = el.get_attribute("data-branch") or ""
        if branch_name:
            indexed = _is_element_indexed(el)
            index_btn = _find_index_button_near(driver, el)
            branches.append({"name": branch_name, "element": el, "indexed": indexed, "button": index_btn})

    if branches:
        return branches

    # Strategy 2: table rows with branch text and a toggle/button
    rows = driver.find_elements(By.CSS_SELECTOR, "tr, [role='row']")
    for row in rows:
        try:
            text = row.text.strip()
            if not text:
                continue
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            branch_name = lines[0] if lines else ""
            if not branch_name or "/" in branch_name or branch_name.lower() in ("branch", "name", "status"):
                continue
            indexed = _is_element_indexed(row)
            index_btn = _find_index_button_near(driver, row)
            if index_btn or indexed:
                branches.append({"name": branch_name, "element": row, "indexed": indexed, "button": index_btn})
        except Exception as e:
            logger.debug(f"Row parse error: {e}")

    if branches:
        return branches

    # Strategy 3: any element with branch-like text next to an index button
    index_buttons = driver.find_elements(
        By.CSS_SELECTOR,
        "button[aria-label*='Index'], button[aria-label*='index'], "
        "button[aria-label*='Reindex'], button[aria-label*='reindex']",
    )
    for btn in index_buttons:
        try:
            parent = btn.find_element(By.XPATH, "..")
            branch_name = _extract_branch_name_from_element(parent)
            if branch_name:
                branches.append({"name": branch_name, "element": parent, "indexed": False, "button": btn})
        except Exception:
            pass

    logger.debug(f"Extracted {len(branches)} branches")
    return branches


def _is_element_indexed(element) -> bool:
    try:
        aria = (element.get_attribute("aria-checked") or "").lower()
        if aria == "true":
            return True
        text = element.text.lower()
        return "indexed" in text and "not indexed" not in text and "reindex" not in text
    except Exception:
        return False


def _find_index_button_near(driver, element):
    for selector in [
        "button[aria-label*='Index']",
        "button[aria-label*='index']",
        "button[aria-label*='Reindex']",
        "[role='switch']",
        "input[type='checkbox']",
    ]:
        try:
            btn = element.find_element(By.CSS_SELECTOR, selector)
            return btn
        except NoSuchElementException:
            pass
    return None


def _extract_branch_name_from_element(element) -> str:
    for selector in [
        ".text-text-primary",
        "span:first-child",
        "td:first-child",
        "[data-branch]",
    ]:
        try:
            text = element.find_element(By.CSS_SELECTOR, selector).text.strip()
            if text and len(text) < 100:
                return text
        except NoSuchElementException:
            pass
    text = element.text.strip().splitlines()
    return text[0].strip() if text else ""


def take_screenshot(driver: webdriver.Edge, filename: str) -> None:
    try:
        driver.save_screenshot(filename)
        logger.info(f"Screenshot saved: {filename}")
    except Exception as e:
        logger.debug(f"Screenshot failed: {e}")
