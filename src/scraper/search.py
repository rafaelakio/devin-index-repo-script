import logging
import time

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.scraper.extractor import extract_repo_list, wait_for_repos

logger = logging.getLogger("devin_indexer.search")

_SEARCH_INPUT_SELECTOR = "input[placeholder='Search repositories...']"
_LOAD_MORE_XPATH = "//button[contains(normalize-space(.), 'Load more')]"


def navigate_to_indexing(driver: webdriver.Edge, indexing_url: str) -> None:
    logger.info(f"Navigating to {indexing_url}")
    driver.get(indexing_url)
    time.sleep(2)


def search_repositories(
    driver: webdriver.Edge,
    indexing_url: str,
    search_term: str,
    rate_limit: float = 1.0,
) -> list[dict]:
    navigate_to_indexing(driver, indexing_url)

    if search_term:
        _apply_search_filter(driver, search_term)
    else:
        wait_for_repos(driver)

    time.sleep(rate_limit)
    _load_all_repositories(driver, rate_limit)

    repositories = extract_repo_list(driver)
    logger.info(f"Found {len(repositories)} repositories matching '{search_term}'")
    return repositories


def _load_all_repositories(driver: webdriver.Edge, rate_limit: float) -> None:
    """Clicks 'Load more' repeatedly until all repositories are visible."""
    page = 1
    while True:
        buttons = driver.find_elements(By.XPATH, _LOAD_MORE_XPATH)
        if not buttons:
            break

        try:
            btn = buttons[0]
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.3)
            btn.click()
            page += 1
            logger.debug(f"Clicked 'Load more' (page {page})")
            time.sleep(max(rate_limit, 1.5))
        except StaleElementReferenceException:
            logger.debug("'Load more' button went stale, re-finding")
            time.sleep(0.5)
            continue
        except Exception as e:
            logger.debug(f"'Load more' click failed, stopping pagination: {e}")
            break


def _apply_search_filter(driver: webdriver.Edge, search_term: str) -> None:
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, _SEARCH_INPUT_SELECTOR))
        )
        search_input = driver.find_element(By.CSS_SELECTOR, _SEARCH_INPUT_SELECTOR)
        search_input.clear()
        search_input.send_keys(search_term)
        time.sleep(2)
        logger.debug(f"Search filter applied: '{search_term}'")
    except TimeoutException:
        logger.warning("Search input not found, loading page as-is")
        wait_for_repos(driver)
