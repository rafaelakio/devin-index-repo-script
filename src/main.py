import sys
import time
import logging

from src.browser.selenium_manager import create_driver, quit_driver
from src.browser.session_handler import (
    is_logged_in,
    load_session,
    save_session,
    wait_for_login,
)
from src.indexer.api_client import process_repository
from src.indexer.retry_handler import AdaptiveRateLimiter
from src.scraper.extractor import take_screenshot
from src.scraper.search import navigate_to_indexing, search_repositories
from src.utils.control_file import ControlFile
from src.utils.logger import setup_logger
from src.utils.output import OutputWriter, RepositoryResult

_DEAD_SESSION_KEYWORDS = (
    "httpconnectionpool",
    "read timed out",
    "no such driver session",
    "invalid session id",
    "connection refused",
    "connection reset",
    "newconnectionerror",
    "remotedisconnected",
    "connectionabortederror",
)


def run(
    indexing_url: str,
    search_term: str,
    output_file: str,
    session_file: str,
    control_file: str,
    headless: bool,
    max_retries: int,
    rate_limit: float,
    login_timeout: int,
    force_update: bool,
    verbose: bool,
) -> None:
    logger = setup_logger(verbose)
    start_time = time.time()
    writer = OutputWriter(indexing_url, search_term)
    rate_limiter = AdaptiveRateLimiter(rate_limit)

    base_url = _extract_base_url(indexing_url)
    driver = None

    try:
        # --- Authentication phase ---
        session_loaded = False
        driver = create_driver(headless=False)

        if load_session(driver, session_file, indexing_url):
            if is_logged_in(driver):
                logger.info("Existing session is valid")
                session_loaded = True
            else:
                logger.info("Session expired, manual login required")

        if not session_loaded:
            navigate_to_indexing(driver, indexing_url)
            if not is_logged_in(driver):
                logged_in = wait_for_login(driver, indexing_url, timeout=login_timeout)
                if not logged_in:
                    logger.error("Login not completed within timeout, exiting")
                    sys.exit(1)
            save_session(driver, session_file)

        # --- Switch to headless if requested ---
        if headless:
            logger.info("Switching to headless mode")
            cookies = driver.get_cookies()
            local_storage = driver.execute_script(
                "return Object.entries(localStorage);"
            ) or []
            session_storage = driver.execute_script(
                "return Object.entries(sessionStorage);"
            ) or []
            quit_driver(driver)
            driver = create_driver(headless=True)
            driver.get(base_url)
            for cookie in cookies:
                cookie.pop("sameSite", None)
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass
            driver.get(base_url)
            for key, value in local_storage:
                driver.execute_script(
                    "localStorage.setItem(arguments[0], arguments[1]);", key, value
                )
            for key, value in session_storage:
                driver.execute_script(
                    "sessionStorage.setItem(arguments[0], arguments[1]);", key, value
                )
            driver.get(indexing_url)
            time.sleep(2)

        # --- Load or create control file ---
        ctrl = ControlFile(control_file)
        if ctrl.exists() and ctrl.load() and ctrl.matches(indexing_url, search_term):
            logger.info(f"Resuming previous run — {ctrl.pending_count()} repos still pending")
        else:
            repositories = search_repositories(driver, indexing_url, search_term, rate_limit)
            if not repositories:
                logger.warning("No repositories found. Check search term and page structure.")
                take_screenshot(driver, "no_repos_found.png")
            ctrl.initialize(indexing_url, search_term, repositories)

        # --- Process each repository ---
        for idx, repo_ctrl in enumerate(ctrl.get_repositories()):
            if repo_ctrl["status"] in ("done", "skipped"):
                continue

            if not force_update and repo_ctrl.get("has_indexed_branches"):
                logger.info(
                    f"Skipping {repo_ctrl['owner']}/{repo_ctrl['name']} "
                    "(already indexed, use --force-update to override)"
                )
                ctrl.mark_skipped(idx, "already indexed")
                continue

            ctrl.mark_processing(idx)
            rate_limiter.wait()

            repo_result = _process_with_recovery(
                driver=driver,
                repo=repo_ctrl,
                rate_limiter=rate_limiter,
                max_retries=max_retries,
                force_update=force_update,
                headless=headless,
                base_url=base_url,
                session_file=session_file,
                indexing_url=indexing_url,
                logger=logger,
            )

            if repo_result is None:
                ctrl.mark_error(idx, "session recovery exhausted")
                # driver may have been replaced inside — retrieve it
                continue

            # repo_result is a (driver, result_dict) tuple after recovery
            driver, result_dict = repo_result

            if result_dict.get("_session_dead"):
                ctrl.mark_error(idx, "session could not be recovered")
                continue

            ctrl.mark_done(idx, result_dict)
            writer.add_repository(RepositoryResult(
                name=result_dict["name"],
                owner=result_dict["owner"],
                url=result_dict["url"],
                branches_found=result_dict["branches_found"],
                branches_processed=result_dict["branches_processed"],
                results=result_dict["results"],
            ))

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=verbose)
        if driver:
            take_screenshot(driver, "fatal_error.png")
        sys.exit(1)
    finally:
        if driver:
            quit_driver(driver)

    execution_time = time.time() - start_time
    writer.save(output_file, execution_time)

    meta = writer.build(execution_time)["metadata"]
    logger.info(
        f"Done in {execution_time:.1f}s | "
        f"Repos: {meta['total_repositories_processed']} | "
        f"Success: {meta['successful_indexations']} | "
        f"Failed: {meta['failed_indexations']} | "
        f"Already indexed: {meta['already_indexed']}"
    )


def _process_with_recovery(
    driver,
    repo: dict,
    rate_limiter,
    max_retries: int,
    force_update: bool,
    headless: bool,
    base_url: str,
    session_file: str,
    indexing_url: str,
    logger,
):
    """Run process_repository with up to 2 session-recovery attempts on WebDriver death."""
    for attempt in range(3):
        try:
            result = process_repository(driver, repo, rate_limiter, max_retries, force_update)
            return driver, result
        except Exception as e:
            if _is_session_dead(e) and attempt < 2:
                logger.warning(
                    f"WebDriver session died ({e.__class__.__name__}: {e}), "
                    f"recreating session (attempt {attempt + 1}/2)..."
                )
                driver = _recreate_session(driver, headless, base_url, session_file, indexing_url, logger)
                time.sleep(2)
            else:
                logger.error(f"Failed to process {repo['owner']}/{repo['name']}: {e}")
                return driver, {"_session_dead": True, **_empty_result(repo)}

    return driver, {"_session_dead": True, **_empty_result(repo)}


def _recreate_session(old_driver, headless: bool, base_url: str, session_file: str, indexing_url: str, logger) -> object:
    quit_driver(old_driver)
    time.sleep(3)
    driver = create_driver(headless=headless)
    if load_session(driver, session_file, indexing_url):
        if is_logged_in(driver):
            logger.info("Session recreated successfully")
        else:
            logger.warning("Session file loaded but user is not authenticated")
    else:
        logger.warning("Could not reload session file after recovery")
    return driver


def _is_session_dead(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in _DEAD_SESSION_KEYWORDS)


def _empty_result(repo: dict) -> dict:
    return {
        "name": repo["name"],
        "owner": repo["owner"],
        "url": repo["url"],
        "branches_found": [],
        "branches_processed": [],
        "results": [],
    }


def _extract_base_url(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


if __name__ == "__main__":
    from src.cli import cli
    cli()
