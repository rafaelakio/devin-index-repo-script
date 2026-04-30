import logging
import time
from datetime import datetime, timezone

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.scraper.extractor import extract_branch_list, take_screenshot

logger = logging.getLogger("devin_indexer.indexer")

_VALID_BRANCHES = {"main", "develop"}
_INDEXING_CONFIRMATION_TIMEOUT = 20


def process_repository(
    driver: webdriver.Edge,
    repo: dict,
    rate_limiter,
    max_retries: int = 3,
) -> dict:
    name = repo["name"]
    owner = repo["owner"]
    repo_url = repo["url"]

    logger.info(f"Processing {owner}/{name}")
    result = {
        "name": name,
        "owner": owner,
        "url": repo_url,
        "branches_found": [],
        "branches_processed": [],
        "results": [],
    }

    try:
        driver.get(repo_url)
        time.sleep(2)

        branches = extract_branch_list(driver)
        all_branch_names = [b["name"] for b in branches]
        result["branches_found"] = all_branch_names
        logger.debug(f"Branches found: {all_branch_names}")

        valid = [b for b in branches if b["name"].lower() in _VALID_BRANCHES]
        if not valid:
            logger.info(f"No main/develop branches found for {owner}/{name}, skipping")
            return result

        for branch in valid:
            rate_limiter.wait()
            branch_result = _index_branch(driver, name, branch, max_retries)
            result["branches_processed"].append(branch["name"])
            result["results"].append(branch_result)
            if branch_result["status"] == "success":
                rate_limiter.decrease()
            else:
                rate_limiter.increase()

    except Exception as e:
        logger.error(f"Failed to process {owner}/{name}: {e}")
        take_screenshot(driver, f"error_{name}.png")

    return result


def _index_branch(
    driver: webdriver.Edge,
    repo_name: str,
    branch: dict,
    max_retries: int,
) -> dict:
    branch_name = branch["name"]
    timestamp = datetime.now(timezone.utc).isoformat()

    if branch.get("indexed"):
        logger.info(f"  {branch_name}: already indexed, skipping")
        return {"branch": branch_name, "status": "already_indexed", "indexed_at": timestamp}

    button = branch.get("button")
    if button is None:
        logger.warning(f"  {branch_name}: no index control found")
        return {
            "branch": branch_name,
            "status": "error",
            "indexed_at": timestamp,
            "error": "Index control not found",
        }

    for attempt in range(1, max_retries + 1):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
            time.sleep(0.5)
            button.click()
            _wait_for_indexing_confirmation(driver, branch_name)
            logger.info(f"  {branch_name}: indexed successfully")
            return {"branch": branch_name, "status": "success", "indexed_at": datetime.now(timezone.utc).isoformat()}
        except StaleElementReferenceException:
            logger.debug(f"  {branch_name}: stale element, retrying ({attempt}/{max_retries})")
            time.sleep(2)
        except (ElementClickInterceptedException, ElementNotInteractableException) as e:
            logger.warning(f"  {branch_name}: click failed attempt {attempt}: {e}")
            time.sleep(2)
        except TimeoutException:
            logger.warning(f"  {branch_name}: confirmation timeout attempt {attempt}/{max_retries}")
            time.sleep(2)

    return {
        "branch": branch_name,
        "status": "error",
        "indexed_at": timestamp,
        "error": f"Failed after {max_retries} attempts",
    }


def _wait_for_indexing_confirmation(driver: webdriver.Edge, branch_name: str) -> None:
    try:
        WebDriverWait(driver, _INDEXING_CONFIRMATION_TIMEOUT).until(
            lambda d: _detect_indexing_feedback(d, branch_name)
        )
    except TimeoutException:
        # Not all UIs show explicit confirmation; treat as success if no error appeared
        error_indicators = driver.find_elements(By.CSS_SELECTOR, "[role='alert'], .error, [data-error]")
        if error_indicators:
            raise TimeoutException(f"Error indicator detected after clicking index for {branch_name}")
        logger.debug(f"No explicit confirmation for {branch_name}, assuming success")


def _detect_indexing_feedback(driver: webdriver.Edge, branch_name: str) -> bool:
    feedback_selectors = [
        "[role='status']",
        "[aria-live]",
        ".toast",
        "[data-testid*='success']",
        "[data-testid*='indexed']",
    ]
    for selector in feedback_selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for el in elements:
            if el.text and ("index" in el.text.lower() or "success" in el.text.lower()):
                return True
    return False
