"""
Repository search functionality for Devin platform.
"""
import time
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.utils.logger import get_logger
from src.scraper.extractor import DataExtractor

logger = get_logger()


class RepositorySearch:
    """Handles searching and filtering repositories on Devin."""
    
    def __init__(self, driver, selenium_manager):
        """
        Initialize repository search.
        
        Args:
            driver: Selenium WebDriver instance
            selenium_manager: SeleniumManager instance for helper methods
        """
        self.driver = driver
        self.selenium_manager = selenium_manager
        self.extractor = DataExtractor(driver)
    
    def navigate_to_indexing_page(self, indexing_url: str) -> bool:
        """
        Navigate to the Devin indexing page.
        
        Args:
            indexing_url: URL of the indexing page
            
        Returns:
            True if navigation successful
        """
        try:
            logger.info(f"Navigating to indexing page: {indexing_url}")
            self.driver.get(indexing_url)
            
            # Wait for page to load
            time.sleep(2)
            
            # Verify we're on the right page
            if '/settings/indexing' not in self.driver.current_url:
                logger.error("Not on indexing page after navigation")
                return False
            
            logger.info("Successfully navigated to indexing page")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to indexing page: {str(e)}")
            return False
    
    def search_repositories(self, search_term: str) -> List[Dict[str, str]]:
        """
        Search for repositories using the search term.
        
        Args:
            search_term: Term to search for
            
        Returns:
            List of repository dictionaries
        """
        try:
            logger.info(f"Searching for repositories with term: '{search_term}'")
            
            # Find search input
            search_input = self._find_search_input()
            if not search_input:
                logger.error("Could not find search input")
                return []
            
            # Clear and enter search term
            search_input.clear()
            search_input.send_keys(search_term)
            
            # Wait for results to update
            time.sleep(2)
            
            # Extract repositories from results
            repositories = self.extractor.extract_repositories()
            
            logger.info(f"Found {len(repositories)} repositories matching '{search_term}'")
            return repositories
            
        except Exception as e:
            logger.error(f"Failed to search repositories: {str(e)}")
            return []
    
    def _find_search_input(self):
        """
        Find the search input element.
        
        Returns:
            WebElement for search input or None
        """
        selectors = [
            "input[placeholder='Search repositories...']",
            "input[placeholder*='Search']",
            "input[type='search']",
            "input[aria-label*='search' i]"
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                logger.debug(f"Found search input with selector: {selector}")
                return element
            except NoSuchElementException:
                continue
        
        logger.warning("Could not find search input with any known selector")
        return None
    
    def click_refresh_button(self) -> bool:
        """
        Click the refresh repositories button.
        
        Returns:
            True if successful
        """
        try:
            refresh_button = self.driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label='Refresh repositories']"
            )
            
            self.selenium_manager.safe_click(refresh_button)
            logger.info("Clicked refresh button")
            
            # Wait for refresh to complete
            time.sleep(3)
            return True
            
        except NoSuchElementException:
            logger.warning("Refresh button not found")
            return False
        except Exception as e:
            logger.error(f"Failed to click refresh button: {str(e)}")
            return False
    
    def get_all_repositories(self) -> List[Dict[str, str]]:
        """
        Get all repositories without filtering.
        
        Returns:
            List of all repository dictionaries
        """
        try:
            logger.info("Extracting all repositories")
            
            # Clear search to show all
            search_input = self._find_search_input()
            if search_input:
                search_input.clear()
                time.sleep(2)
            
            repositories = self.extractor.extract_repositories()
            logger.info(f"Found {len(repositories)} total repositories")
            return repositories
            
        except Exception as e:
            logger.error(f"Failed to get all repositories: {str(e)}")
            return []
    
    def filter_repositories_by_term(
        self,
        repositories: List[Dict[str, str]],
        search_term: str
    ) -> List[Dict[str, str]]:
        """
        Filter repositories by search term (client-side filtering).
        
        Args:
            repositories: List of repository dictionaries
            search_term: Term to filter by
            
        Returns:
            Filtered list of repositories
        """
        search_lower = search_term.lower()
        
        filtered = [
            repo for repo in repositories
            if search_lower in repo['name'].lower() or
               search_lower in repo['owner'].lower() or
               search_lower in repo['full_name'].lower()
        ]
        
        logger.info(f"Filtered {len(repositories)} repos to {len(filtered)} matching '{search_term}'")
        return filtered
    
    def wait_for_repositories_to_load(self, timeout: int = 10) -> bool:
        """
        Wait for repository list to load.
        
        Args:
            timeout: Maximum seconds to wait
            
        Returns:
            True if repositories loaded
        """
        try:
            self.selenium_manager.wait_for_element(
                "a[href*='/settings/indexing/repositories/']",
                timeout=timeout
            )
            logger.debug("Repository list loaded")
            return True
        except TimeoutException:
            logger.warning("Timeout waiting for repositories to load")
            return False
    
    def handle_pagination(self) -> List[Dict[str, str]]:
        """
        Handle pagination if present and collect all repositories.
        
        Returns:
            List of all repositories across all pages
        """
        all_repositories = []
        page = 1
        
        while True:
            logger.info(f"Processing page {page}")
            
            # Extract repositories from current page
            repos = self.extractor.extract_repositories()
            all_repositories.extend(repos)
            
            # Check for next page button
            if not self._go_to_next_page():
                logger.info(f"No more pages. Total pages processed: {page}")
                break
            
            page += 1
            time.sleep(2)  # Wait for page to load
        
        logger.info(f"Collected {len(all_repositories)} repositories from {page} page(s)")
        return all_repositories
    
    def _go_to_next_page(self) -> bool:
        """
        Navigate to the next page if pagination exists.
        
        Returns:
            True if successfully navigated to next page
        """
        try:
            # Look for next page button
            next_selectors = [
                "button[aria-label='Next page']",
                "button[aria-label='Next']",
                "a[aria-label='Next page']",
                "button:has-text('Next')",
                ".pagination button:last-child"
            ]
            
            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # Check if button is disabled
                    if next_button.get_attribute("disabled") or \
                       "disabled" in next_button.get_attribute("class"):
                        return False
                    
                    self.selenium_manager.safe_click(next_button)
                    logger.debug("Navigated to next page")
                    return True
                    
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"No next page available: {str(e)}")
            return False

# Made with Bob
