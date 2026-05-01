import logging
import re
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
_INDEX_OPTIONS_BTN_XPATH = "//button[@aria-label='Index options']"
_RELEASE_PREFIXES = ("release/", "release-", "releases/", "hotfix/", "hotfix-")


def process_repository(
    driver: webdriver.Edge,
    repo: dict,
    rate_limiter,
    max_retries: int = 3,
    force_update: bool = False,
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

        # Read dialog once to discover available (not-yet-indexed) branches
        available = _read_dialog_branches(driver)
        logger.debug(f"Available to add: {available}")

        # Combine both sets to know all branches present in this repo
        all_known = indexed | set(available)

        # Priority: use main/develop; only fall back to last release if neither exists
        primary_in_repo = all_known & _VALID_BRANCHES
        if primary_in_repo:
            targets = set(_VALID_BRANCHES)
        else:
            last_release = _find_last_release_branch(list(all_known))
            if last_release:
                logger.info(f"  main/develop not found; falling back to last release: {last_release}")
                targets = {last_release}
            else:
                targets = set(_VALID_BRANCHES)

        result["branches_found"] = sorted(indexed)

        for branch_name in sorted(targets):
            rate_limiter.wait()
            timestamp = datetime.now(timezone.utc).isoformat()

            if branch_name in indexed:
                if not force_update:
                    logger.info(f"  {branch_name}: already indexed, skipping")
                    result["branches_processed"].append(branch_name)
                    result["results"].append({
                        "branch": branch_name,
                        "status": "already_indexed",
                        "indexed_at": timestamp,
                    })
                    rate_limiter.decrease()
                    continue
                logger.info(f"  {branch_name}: already indexed, forcing re-index")
                branch_result = _reindex_branch(driver, repo_url, branch_name, max_retries)
                result["branches_processed"].append(branch_name)
                result["results"].append(branch_result)
                if branch_result["status"] == "success":
                    rate_limiter.decrease()
                else:
                    rate_limiter.increase()
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


def _read_dialog_branches(driver: webdriver.Edge) -> list[str]:
    """Opens Add branch dialog, reads all available branch names, closes it."""
    branches: list[str] = []
    try:
        add_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, _ADD_BRANCH_BTN_XPATH))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_btn)
        add_btn.click()
        time.sleep(1)

        for xpath in ("//*[@role='option']", "//*[@role='listitem'][not(@aria-hidden='true')]"):
            elements = driver.find_elements(By.XPATH, xpath)
            found = [el.text.strip() for el in elements if el.text.strip()]
            if found:
                branches = found
                break

    except Exception as e:
        logger.debug(f"Could not read dialog branches: {e}")
    finally:
        _dismiss_dialog(driver)

    return branches


def _version_key(branch: str) -> tuple:
    for p in _RELEASE_PREFIXES:
        if branch.lower().startswith(p):
            suffix = branch[len(p):]
            break
    else:
        suffix = branch
    suffix = suffix.lstrip("vV")
    parts = re.split(r"[^0-9]+", suffix)
    return tuple(int(p) for p in parts if p.isdigit())


def _find_last_release_branch(branches: list[str]) -> str | None:
    """Returns the highest-versioned release/hotfix branch, using numeric version comparison."""
    release = [
        b for b in branches
        if any(b.lower().startswith(p) for p in _RELEASE_PREFIXES)
    ]
    return max(release, key=_version_key) if release else None


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


def _reindex_branch(
    driver: webdriver.Edge,
    repo_url: str,
    branch_name: str,
    max_retries: int,
) -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()

    for attempt in range(1, max_retries + 1):
        try:
            options_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, _INDEX_OPTIONS_BTN_XPATH))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", options_btn)
            options_btn.click()
            time.sleep(0.8)

            # Look for a menu item that relates to re-indexing, preferably for this branch
            reindex_xpaths = [
                f"//*[@role='menuitem' and contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'reindex') and contains(.,'{branch_name}')]",
                f"//*[@role='menuitem' and contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'re-index') and contains(.,'{branch_name}')]",
                f"//*[@role='menuitem' and contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'reindex')]",
                f"//*[@role='menuitem' and contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'re-index')]",
                f"//*[@role='menuitem' and contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'force')]",
            ]

            option = None
            for xpath in reindex_xpaths:
                elements = driver.find_elements(By.XPATH, xpath)
                if elements:
                    option = elements[0]
                    break

            if option is None:
                logger.warning(f"  {branch_name}: no re-index option found in 'Index options' menu")
                _dismiss_dialog(driver)
                return {
                    "branch": branch_name,
                    "status": "skipped",
                    "indexed_at": timestamp,
                    "error": "Re-index option not found in menu",
                }

            option.click()
            logger.info(f"  {branch_name}: re-index submitted")
            return {
                "branch": branch_name,
                "status": "success",
                "indexed_at": datetime.now(timezone.utc).isoformat(),
            }

        except StaleElementReferenceException:
            logger.debug(f"  {branch_name}: stale element on re-index, retrying ({attempt}/{max_retries})")
            driver.get(repo_url)
            time.sleep(2)
        except TimeoutException as e:
            logger.warning(f"  {branch_name}: re-index timeout attempt {attempt}: {e}")
            driver.get(repo_url)
            time.sleep(2)
        except Exception as e:
            logger.warning(f"  {branch_name}: re-index attempt {attempt} failed: {e}")
            driver.get(repo_url)
            time.sleep(2)

    return {
        "branch": branch_name,
        "status": "error",
        "indexed_at": timestamp,
        "error": f"Re-index failed after {max_retries} attempts",
    }


def _find_branch_option(driver: webdriver.Edge, branch_name: str):
    """Find the branch option inside the opened Add branch dialog."""
    try:
        search_input = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//*[@role='dialog' or @role='listbox']//input"
                " | //input[@placeholder and not(@aria-hidden)]",
            ))
        )
        search_input.clear()
        search_input.send_keys(branch_name)
        time.sleep(0.8)
        logger.debug(f"  Typed '{branch_name}' in dialog search input")
    except TimeoutException:
        logger.debug("  No search input found in dialog, proceeding without filter")

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
