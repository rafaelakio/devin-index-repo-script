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
from src.utils.logger import setup_logger
from src.utils.output import OutputWriter, RepositoryResult, ErrorEntry


def run(
    indexing_url: str,
    search_term: str,
    output_file: str,
    session_file: str,
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

        # --- Search and extract repositories ---
        repositories = search_repositories(driver, indexing_url, search_term, rate_limit)

        if not repositories:
            logger.warning("No repositories found. Check search term and page structure.")
            take_screenshot(driver, "no_repos_found.png")

        # --- Process each repository ---
        for repo in repositories:
            if not force_update and repo.get("has_indexed_branches"):
                logger.info(f"Skipping {repo['owner']}/{repo['name']} (already indexed, use --force-update to override)")
                continue
            rate_limiter.wait()
            repo_result = process_repository(driver, repo, rate_limiter, max_retries, force_update)
            writer.add_repository(RepositoryResult(
                name=repo_result["name"],
                owner=repo_result["owner"],
                url=repo_result["url"],
                branches_found=repo_result["branches_found"],
                branches_processed=repo_result["branches_processed"],
                results=repo_result["results"],
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


def _extract_base_url(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


if __name__ == "__main__":
    from src.cli import cli
    cli()
