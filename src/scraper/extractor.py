"""
Data extraction from Devin web pages.
"""
from typing import List, Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from src.utils.logger import get_logger

logger = get_logger()


class DataExtractor:
    """Extracts repository and branch information from Devin pages."""
    
    def __init__(self, driver):
        """
        Initialize data extractor.
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
    
    def extract_repositories(self) -> List[Dict[str, str]]:
        """
        Extract repository information from the indexing page.
        
        Returns:
            List of dictionaries containing repository data
        """
        repositories = []
        
        try:
            # Wait for repository cards to load
            repo_links = self.driver.find_elements(
                By.CSS_SELECTOR,
                "a[href*='/settings/indexing/repositories/']"
            )
            
            logger.info(f"Found {len(repo_links)} repository cards")
            
            for link in repo_links:
                try:
                    repo_data = self._extract_repo_from_card(link)
                    if repo_data:
                        repositories.append(repo_data)
                except Exception as e:
                    logger.warning(f"Failed to extract repository data: {str(e)}")
                    continue
            
            logger.info(f"Successfully extracted {len(repositories)} repositories")
            return repositories
            
        except Exception as e:
            logger.error(f"Failed to extract repositories: {str(e)}")
            return []
    
    def _extract_repo_from_card(self, card_element: WebElement) -> Optional[Dict[str, str]]:
        """
        Extract repository information from a single card element.
        
        Args:
            card_element: WebElement representing a repository card
            
        Returns:
            Dictionary with repository data or None if extraction fails
        """
        try:
            # Extract repository name
            name_element = card_element.find_element(
                By.CSS_SELECTOR,
                ".text-text-primary.text-13.truncate"
            )
            repo_name = name_element.text.strip()
            
            # Extract owner
            owner_element = card_element.find_element(
                By.CSS_SELECTOR,
                ".text-text-secondary.text-13.truncate"
            )
            owner = owner_element.text.strip()
            
            # Extract URL
            repo_url = card_element.get_attribute("href")
            
            # Extract indexing status (optional)
            status_text = ""
            try:
                status_element = card_element.find_element(
                    By.CSS_SELECTOR,
                    "span.text-text-secondary.text-13"
                )
                status_text = status_element.text.strip()
            except NoSuchElementException:
                pass
            
            repo_data = {
                'name': repo_name,
                'owner': owner,
                'url': repo_url,
                'full_name': f"{owner}/{repo_name}",
                'status': status_text
            }
            
            logger.debug(f"Extracted repository: {repo_data['full_name']}")
            return repo_data
            
        except Exception as e:
            logger.warning(f"Failed to extract data from card: {str(e)}")
            return None
    
    def extract_branches(self, repo_url: str) -> List[Dict[str, str]]:
        """
        Extract branch information from a repository details page.
        
        Args:
            repo_url: URL of the repository details page
            
        Returns:
            List of dictionaries containing branch data
        """
        branches = []
        
        try:
            # Navigate to repository details page
            logger.debug(f"Navigating to {repo_url}")
            self.driver.get(repo_url)
            
            # Wait for page to load
            import time
            time.sleep(2)
            
            # Try to find branch elements
            # Note: The exact selectors depend on the actual page structure
            # This is a generic implementation that may need adjustment
            
            branch_elements = self._find_branch_elements()
            
            for element in branch_elements:
                try:
                    branch_data = self._extract_branch_from_element(element)
                    if branch_data:
                        branches.append(branch_data)
                except Exception as e:
                    logger.warning(f"Failed to extract branch data: {str(e)}")
                    continue
            
            logger.info(f"Found {len(branches)} branches")
            return branches
            
        except Exception as e:
            logger.error(f"Failed to extract branches from {repo_url}: {str(e)}")
            return []
    
    def _find_branch_elements(self) -> List[WebElement]:
        """
        Find branch elements on the page.
        
        Returns:
            List of WebElements representing branches
        """
        # Try multiple selectors as the structure may vary
        selectors = [
            "div[data-branch]",
            "button[data-branch]",
            "a[href*='/branch/']",
            ".branch-item",
            "[class*='branch']"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.debug(f"Found branch elements with selector: {selector}")
                    return elements
            except:
                continue
        
        logger.warning("Could not find branch elements with any known selector")
        return []
    
    def _extract_branch_from_element(self, element: WebElement) -> Optional[Dict[str, str]]:
        """
        Extract branch information from an element.
        
        Args:
            element: WebElement representing a branch
            
        Returns:
            Dictionary with branch data or None if extraction fails
        """
        try:
            # Try to get branch name from various attributes
            branch_name = None
            
            # Try data attribute
            branch_name = element.get_attribute("data-branch")
            
            # Try text content
            if not branch_name:
                branch_name = element.text.strip()
            
            # Try aria-label
            if not branch_name:
                branch_name = element.get_attribute("aria-label")
            
            if branch_name:
                # Check if already indexed
                is_indexed = self._check_if_indexed(element)
                
                return {
                    'name': branch_name,
                    'is_indexed': is_indexed
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract branch from element: {str(e)}")
            return None
    
    def _check_if_indexed(self, element: WebElement) -> bool:
        """
        Check if a branch is already indexed.
        
        Args:
            element: WebElement representing a branch
            
        Returns:
            True if indexed, False otherwise
        """
        try:
            # Look for indicators that branch is indexed
            # This could be a checkmark icon, specific class, or text
            
            # Check for checkmark SVG
            try:
                element.find_element(By.CSS_SELECTOR, "svg[class*='check']")
                return True
            except NoSuchElementException:
                pass
            
            # Check for "indexed" text or class
            element_html = element.get_attribute("outerHTML").lower()
            if "indexed" in element_html or "check" in element_html:
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Failed to check index status: {str(e)}")
            return False
    
    def filter_branches(
        self,
        branches: List[Dict[str, str]],
        allowed_branches: List[str] = None
    ) -> List[Dict[str, str]]:
        """
        Filter branches to only include specified branch names.
        
        Args:
            branches: List of branch dictionaries
            allowed_branches: List of allowed branch names (default: ['main', 'develop'])
            
        Returns:
            Filtered list of branches
        """
        if allowed_branches is None:
            allowed_branches = ['main', 'develop']
        
        # Normalize allowed branch names to lowercase
        allowed_lower = [b.lower() for b in allowed_branches]
        
        filtered = [
            branch for branch in branches
            if branch['name'].lower() in allowed_lower
        ]
        
        logger.info(f"Filtered {len(branches)} branches to {len(filtered)} (allowed: {allowed_branches})")
        return filtered
    
    def get_page_title(self) -> str:
        """
        Get the current page title.
        
        Returns:
            Page title
        """
        try:
            return self.driver.title
        except Exception as e:
            logger.error(f"Failed to get page title: {str(e)}")
            return ""
    
    def get_current_url(self) -> str:
        """
        Get the current page URL.
        
        Returns:
            Current URL
        """
        try:
            return self.driver.current_url
        except Exception as e:
            logger.error(f"Failed to get current URL: {str(e)}")
            return ""

# Made with Bob
