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
    card_data = driver.execute_script("""
        const sel = "a[href*='/settings/indexing/repositories/']";
        const nameSel = ".text-text-primary.text-13.truncate";
        const ownerSel = ".text-text-secondary.text-13.truncate";
        return Array.from(document.querySelectorAll(sel)).map(card => {
            const nameEl  = card.querySelector(nameSel);
            const ownerEl = card.querySelector(ownerSel);
            const text    = card.innerText || "";
            return {
                href:        card.href,
                name:        nameEl  ? nameEl.innerText.trim()  : "",
                owner:       ownerEl ? ownerEl.innerText.trim() : "",
                has_indexed: text.includes("branch indexed") && !text.includes("Not indexed")
            };
        });
    """) or []

    repositories = []
    for data in card_data:
        if data.get("name") and data.get("href"):
            repositories.append({
                "name":                 data["name"],
                "owner":                data["owner"],
                "url":                  data["href"],
                "has_indexed_branches": data["has_indexed"],
            })
    logger.debug(f"Extracted {len(repositories)} repositories from page")
    return repositories


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
