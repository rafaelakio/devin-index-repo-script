import logging
import time
from datetime import datetime, timezone

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.scraper.extractor import extract_indexed_branches, take_screenshot

logger = logging.getLogger("devin_indexer.indexer")

_VALID_BRANCHES = {"main", "develop"}
_ADD_BRANCH_BTN_XPATH = "//button[@role='combobox' and @aria-haspopup='dialog']"


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

        indexed = extract_indexed_branches(driver)
        result["branches_found"] = sorted(indexed)
        logger.debug(f"Already indexed: {indexed}")

        for branch_name in sorted(_VALID_BRANCHES):
            rate_limiter.wait()
            timestamp = datetime.now(timezone.utc).isoformat()

            if branch_name in indexed:
                logger.info(f"  {branch_name}: already indexed, skipping")
                result["branches_processed"].append(branch_name)
                result["results"].append({
                    "branch": branch_name,
                    "status": "already_indexed",
                    "indexed_at": timestamp,
                })
                rate_limiter.decrease()
            else:
                branch_result = _add_branch(driver, repo_url, branch_name, max_retries)
                result["branches_processed"].append(branch_name)
                result["results"].append(branch_result)
                if branch_result["status"] == "success":
                    rate_limiter.decrease()
                else:
                    rate_limiter.increase()

    except Exception as e:
        logger.error(f"Failed to process {owner}/{name}: {e}")
        take_screenshot(driver, f"error_{name}.png")

    return result


def _add_branch(
    driver: webdriver.Edge,
    repo_url: str,
    branch_name: str,
    max_retries: int,
) -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()

    for attempt in range(1, max_retries + 1):
        try:
            add_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, _ADD_BRANCH_BTN_XPATH))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_btn)
            time.sleep(0.3)
            add_btn.click()
            logger.debug(f"  {branch_name}: clicked 'Add branch' (attempt {attempt})")

            # Wait for dialog/popover to open
            time.sleep(1)

            option = _find_branch_option(driver, branch_name)

            if option is None:
                logger.info(f"  {branch_name}: not available in dialog (branch may not exist in repo)")
                _dismiss_dialog(driver)
                return {
                    "branch": branch_name,
                    "status": "not_found",
                    "indexed_at": timestamp,
                    "error": "Branch not available in selection dialog",
                }

            option.click()
            logger.info(f"  {branch_name}: submitted")
            return {
                "branch": branch_name,
                "status": "success",
                "indexed_at": datetime.now(timezone.utc).isoformat(),
            }

        except StaleElementReferenceException:
            logger.debug(f"  {branch_name}: stale element, retrying ({attempt}/{max_retries})")
            driver.get(repo_url)
            time.sleep(2)
        except TimeoutException as e:
            logger.warning(f"  {branch_name}: timeout on attempt {attempt}: {e}")
            driver.get(repo_url)
            time.sleep(2)
        except Exception as e:
            logger.warning(f"  {branch_name}: attempt {attempt} failed: {e}")
            driver.get(repo_url)
            time.sleep(2)

    return {
        "branch": branch_name,
        "status": "error",
        "indexed_at": timestamp,
        "error": f"Failed after {max_retries} attempts",
    }


def _find_branch_option(driver: webdriver.Edge, branch_name: str):
    """Find the branch option inside the opened Add branch dialog."""
    # Try typing into a search input if the dialog has one
    try:
        search_input = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//*[@role='dialog' or @role='listbox' or @data-radix-popper-content-wrapper]//input"
                " | //input[@placeholder and not(@aria-hidden)]",
            ))
        )
        search_input.clear()
        search_input.send_keys(branch_name)
        time.sleep(0.8)
        logger.debug(f"  Typed '{branch_name}' in dialog search input")
    except TimeoutException:
        logger.debug("  No search input found in dialog, proceeding without filter")

    # Look for the option matching the branch name with several strategies
    option_xpaths = [
        f"//*[@role='option' and normalize-space(.)='{branch_name}']",
        f"//*[@role='option' and contains(.,'{branch_name}')]",
        f"//*[@role='listitem' and normalize-space(.)='{branch_name}']",
        f"//li[normalize-space(.)='{branch_name}']",
        f"//*[@role='menuitem' and normalize-space(.)='{branch_name}']",
        f"//*[normalize-space(.)='{branch_name}' and (ancestor::*[@role='dialog'] or ancestor::*[@role='listbox'])]",
    ]

    for xpath in option_xpaths:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            if elements:
                logger.debug(f"  Found branch option via: {xpath}")
                return elements[0]
        except Exception:
            pass

    return None


def _dismiss_dialog(driver: webdriver.Edge) -> None:
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.5)
    except Exception:
        pass
