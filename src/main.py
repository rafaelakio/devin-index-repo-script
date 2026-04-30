"""
Main entry point for the Devin Repository Indexer.
"""
import time
from datetime import datetime
from typing import Dict, Any

from src.utils.logger import get_logger, setup_logger
from src.browser.selenium_manager import SeleniumManager
from src.browser.session_handler import SessionHandler
from src.scraper.search import RepositorySearch
from src.indexer.api_client import IndexingAPIClient
from src.utils.output import OutputWriter

logger = get_logger()


def run_indexer(config: Dict[str, Any]) -> None:
    """
    Main function to run the indexing process.
    
    Args:
        config: Configuration dictionary with all settings
    """
    start_time = time.time()
    
    # Extract configuration
    indexing_url = config['indexing_url']
    search_term = config['search_term']
    output_file = config['output_file']
    session_file = config['session_file']
    headless = config['headless']
    max_retries = config['max_retries']
    rate_limit = config['rate_limit']
    
    # Initialize components
    selenium_manager = None
    driver = None
    
    try:
        logger.info("Initializing Devin Repository Indexer...")
        
        # Initialize Selenium Manager (start in non-headless mode for login)
        selenium_manager = SeleniumManager(headless=False, timeout=30)
        driver = selenium_manager.initialize_driver(headless=False)
        
        # Initialize Session Handler
        session_handler = SessionHandler(session_file)
        selenium_manager.session_handler = session_handler
        
        # Check for existing session
        session_info = session_handler.get_session_info()
        if session_info:
            logger.info(f"Found existing session (age: {session_info['age_days']} days)")
            logger.info("Attempting to load saved session...")
            
            if session_handler.load_cookies(driver):
                # Navigate to indexing page to verify session
                driver.get(indexing_url)
                time.sleep(2)
                
                if session_handler.is_session_valid(driver):
                    logger.info("Session is valid, skipping login")
                else:
                    logger.warning("Session is invalid, manual login required")
                    session_handler.clear_session()
                    driver.get(indexing_url)
                    if not selenium_manager.wait_for_login(max_wait=300):
                        raise Exception("Login timeout")
                    session_handler.save_cookies(driver)
            else:
                logger.warning("Failed to load session, manual login required")
                driver.get(indexing_url)
                if not selenium_manager.wait_for_login(max_wait=300):
                    raise Exception("Login timeout")
                session_handler.save_cookies(driver)
        else:
            logger.info("No saved session found")
            logger.info("Opening browser for manual login...")
            
            # Navigate to indexing page
            driver.get(indexing_url)
            time.sleep(2)
            
            # Check if already logged in
            if not selenium_manager.is_logged_in():
                logger.info("Please log in manually in the browser window...")
                if not selenium_manager.wait_for_login(max_wait=300):
                    raise Exception("Login timeout")
            
            # Save session
            session_handler.save_cookies(driver)
            logger.info("Session saved successfully")
        
        # Switch to headless mode if configured
        if headless:
            logger.info("Switching to headless mode...")
            selenium_manager.switch_to_headless()
            driver = selenium_manager.driver
            
            # Navigate back to indexing page
            driver.get(indexing_url)
            time.sleep(2)
        
        # Initialize search and indexing components
        repo_search = RepositorySearch(driver, selenium_manager)
        api_client = IndexingAPIClient(driver, selenium_manager, max_retries, rate_limit)
        
        # Navigate to indexing page
        if not repo_search.navigate_to_indexing_page(indexing_url):
            raise Exception("Failed to navigate to indexing page")
        
        # Search for repositories
        logger.info(f"Searching for repositories with term: '{search_term}'")
        repositories = repo_search.search_repositories(search_term)
        
        if not repositories:
            logger.warning(f"No repositories found matching '{search_term}'")
            logger.info("Trying to get all repositories...")
            repositories = repo_search.get_all_repositories()
            
            if repositories:
                # Filter client-side
                repositories = repo_search.filter_repositories_by_term(
                    repositories,
                    search_term
                )
        
        if not repositories:
            logger.error("No repositories found")
            return
        
        logger.info(f"Found {len(repositories)} repositories to process")
        
        # Index repositories
        logger.info("Starting indexing process...")
        results = api_client.batch_index_repositories(
            repositories,
            allowed_branches=['main', 'develop']
        )
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Prepare metadata
        metadata = {
            'execution_timestamp': datetime.now().isoformat(),
            'indexing_url': indexing_url,
            'search_term': search_term,
            'total_repositories_found': len(repositories),
            'execution_time_seconds': round(execution_time, 2)
        }
        
        # Write results to file
        logger.info("Writing results to output file...")
        output_writer = OutputWriter(output_file)
        output_writer.write_results(results, metadata)
        
        # Display summary
        logger.info("\n" + output_writer.get_summary())
        
        # Export CSV if there are results
        if results.get('successful') or results.get('failed'):
            logger.info("Exporting results to CSV...")
            output_writer.export_csv()
        
        logger.info(f"Total execution time: {execution_time:.2f} seconds")
        logger.info("Indexing process completed!")
        
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        raise
        
    except Exception as e:
        logger.error(f"Error during indexing: {str(e)}", exc_info=True)
        raise
        
    finally:
        # Cleanup
        if selenium_manager:
            logger.info("Closing browser...")
            selenium_manager.close_driver()


if __name__ == '__main__':
    # This allows running the script directly for testing
    # In production, use cli.py instead
    from src.cli import main
    main()

# Made with Bob
