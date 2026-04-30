"""
API client for Devin indexing operations.
"""
import time
from typing import Dict, Optional, Any
from datetime import datetime

from src.utils.logger import get_logger
from src.indexer.retry_handler import RetryHandler

logger = get_logger()


class IndexingAPIClient:
    """Client for interacting with Devin's indexing functionality."""
    
    def __init__(
        self,
        driver,
        selenium_manager,
        max_retries: int = 3,
        rate_limit: float = 1.0
    ):
        """
        Initialize API client.
        
        Args:
            driver: Selenium WebDriver instance
            selenium_manager: SeleniumManager instance
            max_retries: Maximum retry attempts
            rate_limit: Delay between operations in seconds
        """
        self.driver = driver
        self.selenium_manager = selenium_manager
        self.retry_handler = RetryHandler(
            max_retries=max_retries,
            rate_limit_delay=rate_limit
        )
    
    def index_repository_branch(
        self,
        repo_name: str,
        branch_name: str,
        repo_url: str
    ) -> Dict[str, Any]:
        """
        Index a specific branch of a repository.
        
        Args:
            repo_name: Repository name
            branch_name: Branch name to index
            repo_url: URL of the repository details page
            
        Returns:
            Dictionary with indexing result
        """
        try:
            logger.info(f"Indexing {repo_name}:{branch_name}")
            
            # Use retry handler for the indexing operation
            result = self.retry_handler.with_retry(
                self._perform_indexing,
                repo_name,
                branch_name,
                repo_url
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to index {repo_name}:{branch_name}: {str(e)}")
            return {
                'repository': repo_name,
                'branch': branch_name,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _perform_indexing(
        self,
        repo_name: str,
        branch_name: str,
        repo_url: str
    ) -> Dict[str, Any]:
        """
        Perform the actual indexing operation.
        
        Args:
            repo_name: Repository name
            branch_name: Branch name
            repo_url: Repository details URL
            
        Returns:
            Dictionary with result
        """
        try:
            # Navigate to repository details page
            logger.debug(f"Navigating to {repo_url}")
            self.driver.get(repo_url)
            time.sleep(2)
            
            # Find the branch element
            branch_element = self._find_branch_element(branch_name)
            if not branch_element:
                raise Exception(f"Branch '{branch_name}' not found on page")
            
            # Check if already indexed
            if self._is_branch_indexed(branch_element):
                logger.info(f"{repo_name}:{branch_name} is already indexed")
                return {
                    'repository': repo_name,
                    'branch': branch_name,
                    'status': 'already_indexed',
                    'message': 'Branch is already indexed',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Trigger indexing
            success = self._trigger_indexing(branch_element, branch_name)
            
            if success:
                logger.info(f"Successfully indexed {repo_name}:{branch_name}")
                return {
                    'repository': repo_name,
                    'branch': branch_name,
                    'status': 'success',
                    'message': 'Branch indexed successfully',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                raise Exception("Failed to trigger indexing")
                
        except Exception as e:
            logger.error(f"Error during indexing: {str(e)}")
            raise
    
    def _find_branch_element(self, branch_name: str):
        """
        Find the element for a specific branch.
        
        Args:
            branch_name: Name of the branch to find
            
        Returns:
            WebElement or None
        """
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException
        
        # Try multiple strategies to find the branch
        strategies = [
            # By data attribute
            lambda: self.driver.find_element(
                By.CSS_SELECTOR,
                f"[data-branch='{branch_name}']"
            ),
            # By text content
            lambda: self._find_element_by_text(branch_name),
            # By aria-label
            lambda: self.driver.find_element(
                By.CSS_SELECTOR,
                f"[aria-label*='{branch_name}']"
            )
        ]
        
        for strategy in strategies:
            try:
                element = strategy()
                if element:
                    logger.debug(f"Found branch element for '{branch_name}'")
                    return element
            except NoSuchElementException:
                continue
            except Exception as e:
                logger.debug(f"Strategy failed: {str(e)}")
                continue
        
        logger.warning(f"Could not find element for branch '{branch_name}'")
        return None
    
    def _find_element_by_text(self, text: str):
        """
        Find element containing specific text.
        
        Args:
            text: Text to search for
            
        Returns:
            WebElement or None
        """
        from selenium.webdriver.common.by import By
        
        try:
            # Use XPath to find element by text
            xpath = f"//*[contains(text(), '{text}')]"
            elements = self.driver.find_elements(By.XPATH, xpath)
            
            # Return the first matching element
            for element in elements:
                if element.text.strip().lower() == text.lower():
                    return element
            
            return elements[0] if elements else None
            
        except Exception as e:
            logger.debug(f"Failed to find element by text: {str(e)}")
            return None
    
    def _is_branch_indexed(self, branch_element) -> bool:
        """
        Check if a branch is already indexed.
        
        Args:
            branch_element: WebElement for the branch
            
        Returns:
            True if indexed, False otherwise
        """
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException
        
        try:
            # Look for indicators of indexing
            # Check for checkmark icon
            try:
                branch_element.find_element(By.CSS_SELECTOR, "svg[class*='check']")
                return True
            except NoSuchElementException:
                pass
            
            # Check for "indexed" text or class
            element_html = branch_element.get_attribute("outerHTML").lower()
            if "indexed" in element_html:
                return True
            
            # Check for disabled state (might indicate already indexed)
            if branch_element.get_attribute("disabled"):
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking index status: {str(e)}")
            return False
    
    def _trigger_indexing(self, branch_element, branch_name: str) -> bool:
        """
        Trigger indexing for a branch.
        
        Args:
            branch_element: WebElement for the branch
            branch_name: Name of the branch
            
        Returns:
            True if successful
        """
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException
        
        try:
            # Look for index button or checkbox
            # Try to find a button within or near the branch element
            try:
                index_button = branch_element.find_element(
                    By.CSS_SELECTOR,
                    "button[aria-label*='index' i], button[aria-label*='add' i]"
                )
                self.selenium_manager.safe_click(index_button)
                logger.debug(f"Clicked index button for {branch_name}")
                time.sleep(1)
                return True
            except NoSuchElementException:
                pass
            
            # Try to find a checkbox
            try:
                checkbox = branch_element.find_element(
                    By.CSS_SELECTOR,
                    "input[type='checkbox']"
                )
                if not checkbox.is_selected():
                    self.selenium_manager.safe_click(checkbox)
                    logger.debug(f"Checked checkbox for {branch_name}")
                    time.sleep(1)
                    return True
            except NoSuchElementException:
                pass
            
            # Try clicking the element itself
            self.selenium_manager.safe_click(branch_element)
            logger.debug(f"Clicked branch element for {branch_name}")
            time.sleep(1)
            
            # Wait for confirmation or status change
            time.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to trigger indexing: {str(e)}")
            return False
    
    def batch_index_repositories(
        self,
        repositories: list,
        allowed_branches: list = None
    ) -> Dict[str, Any]:
        """
        Index multiple repositories in batch.
        
        Args:
            repositories: List of repository dictionaries
            allowed_branches: List of branch names to index (default: ['main', 'develop'])
            
        Returns:
            Dictionary with batch results
        """
        if allowed_branches is None:
            allowed_branches = ['main', 'develop']
        
        results = {
            'successful': [],
            'failed': [],
            'already_indexed': [],
            'skipped': []
        }
        
        total = len(repositories)
        
        for idx, repo in enumerate(repositories, 1):
            logger.info(f"Processing repository {idx}/{total}: {repo['full_name']}")
            
            try:
                # Get branches for this repository
                from src.scraper.extractor import DataExtractor
                extractor = DataExtractor(self.driver)
                
                branches = extractor.extract_branches(repo['url'])
                filtered_branches = extractor.filter_branches(branches, allowed_branches)
                
                if not filtered_branches:
                    logger.warning(f"No valid branches found for {repo['full_name']}")
                    results['skipped'].append({
                        'repository': repo['full_name'],
                        'reason': 'No valid branches found'
                    })
                    continue
                
                # Index each branch
                for branch in filtered_branches:
                    result = self.index_repository_branch(
                        repo['full_name'],
                        branch['name'],
                        repo['url']
                    )
                    
                    if result['status'] == 'success':
                        results['successful'].append(result)
                    elif result['status'] == 'already_indexed':
                        results['already_indexed'].append(result)
                    else:
                        results['failed'].append(result)
                
            except Exception as e:
                logger.error(f"Error processing {repo['full_name']}: {str(e)}")
                results['failed'].append({
                    'repository': repo['full_name'],
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return results

# Made with Bob
