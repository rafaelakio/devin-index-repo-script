"""
Selenium WebDriver management and browser automation.
"""
import time
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from src.utils.logger import get_logger
from src.browser.session_handler import SessionHandler

logger = get_logger()


class SeleniumManager:
    """Manages Selenium WebDriver lifecycle and browser operations."""
    
    def __init__(self, headless: bool = False, timeout: int = 30):
        """
        Initialize Selenium manager.
        
        Args:
            headless: Whether to run browser in headless mode
            timeout: Default timeout for operations in seconds
        """
        self.headless = headless
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None
        self.session_handler: Optional[SessionHandler] = None
        
    def initialize_driver(self, headless: Optional[bool] = None) -> webdriver.Chrome:
        """
        Initialize Chrome WebDriver with appropriate options.
        
        Args:
            headless: Override headless setting
            
        Returns:
            Initialized WebDriver instance
        """
        if headless is None:
            headless = self.headless
        
        logger.info(f"Initializing Chrome WebDriver (headless={headless})")
        
        options = Options()
        
        if headless:
            options.add_argument('--headless=new')
        
        # Common options for stability
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        
        # User agent to avoid detection
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Disable automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Set page load timeout
            self.driver.set_page_load_timeout(self.timeout)
            
            # Execute CDP commands to hide automation
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Chrome WebDriver initialized successfully")
            return self.driver
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise
    
    def close_driver(self) -> None:
        """Close the WebDriver and cleanup resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {str(e)}")
            finally:
                self.driver = None
    
    def wait_for_element(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ):
        """
        Wait for an element to be present on the page.
        
        Args:
            selector: Element selector
            by: Selenium By locator type
            timeout: Custom timeout (uses default if None)
            
        Returns:
            WebElement if found
            
        Raises:
            TimeoutException if element not found
        """
        if timeout is None:
            timeout = self.timeout
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            logger.error(f"Timeout waiting for element: {selector}")
            raise
    
    def wait_for_clickable(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ):
        """
        Wait for an element to be clickable.
        
        Args:
            selector: Element selector
            by: Selenium By locator type
            timeout: Custom timeout (uses default if None)
            
        Returns:
            WebElement if found and clickable
        """
        if timeout is None:
            timeout = self.timeout
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            return element
        except TimeoutException:
            logger.error(f"Timeout waiting for clickable element: {selector}")
            raise
    
    def safe_click(self, element) -> bool:
        """
        Safely click an element with retry logic.
        
        Args:
            element: WebElement to click
            
        Returns:
            True if click was successful
        """
        try:
            element.click()
            return True
        except Exception as e:
            logger.warning(f"Normal click failed, trying JavaScript click: {str(e)}")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e2:
                logger.error(f"JavaScript click also failed: {str(e2)}")
                return False
    
    def wait_for_login(self, check_interval: int = 2, max_wait: int = 300) -> bool:
        """
        Wait for user to complete manual login.
        
        Args:
            check_interval: Seconds between checks
            max_wait: Maximum seconds to wait
            
        Returns:
            True if login detected, False if timeout
        """
        logger.info("Waiting for manual login...")
        logger.info("Please log in to the Devin platform in the browser window")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                current_url = self.driver.current_url
                
                # Check if we're no longer on login page
                if 'login' not in current_url.lower() and 'signin' not in current_url.lower():
                    # Additional check: look for authenticated content
                    if '/settings/indexing' in current_url or '/org/' in current_url:
                        logger.info("Login detected successfully!")
                        return True
                
                time.sleep(check_interval)
                
            except Exception as e:
                logger.debug(f"Error checking login status: {str(e)}")
                time.sleep(check_interval)
        
        logger.error(f"Login timeout after {max_wait} seconds")
        return False
    
    def is_logged_in(self) -> bool:
        """
        Check if user is currently logged in.
        
        Returns:
            True if logged in, False otherwise
        """
        try:
            current_url = self.driver.current_url
            
            # Check URL patterns
            if 'login' in current_url.lower() or 'signin' in current_url.lower():
                return False
            
            # Check for authenticated content
            if '/settings/indexing' in current_url or '/org/' in current_url:
                return True
            
            # Try to find elements that only appear when logged in
            try:
                # This is a generic check - adjust based on actual Devin UI
                self.driver.find_element(By.CSS_SELECTOR, "button[aria-label*='user'], button[aria-label*='profile'], a[href*='/settings']")
                return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking login status: {str(e)}")
            return False
    
    def switch_to_headless(self) -> None:
        """
        Switch to headless mode by restarting the driver.
        Note: This will require reloading cookies.
        """
        if not self.headless:
            logger.info("Switching to headless mode...")
            
            # Save current cookies
            if self.session_handler:
                self.session_handler.save_cookies(self.driver)
            
            # Close current driver
            self.close_driver()
            
            # Reinitialize in headless mode
            self.headless = True
            self.initialize_driver(headless=True)
            
            # Reload cookies
            if self.session_handler:
                self.session_handler.load_cookies(self.driver)
            
            logger.info("Switched to headless mode successfully")
    
    def take_screenshot(self, filename: str = "screenshot.png") -> bool:
        """
        Take a screenshot of the current page.
        
        Args:
            filename: Path to save screenshot
            
        Returns:
            True if successful
        """
        try:
            self.driver.save_screenshot(filename)
            logger.info(f"Screenshot saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to take screenshot: {str(e)}")
            return False
    
    def scroll_to_element(self, element) -> None:
        """
        Scroll to make an element visible.
        
        Args:
            element: WebElement to scroll to
        """
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)  # Wait for scroll animation
        except Exception as e:
            logger.warning(f"Failed to scroll to element: {str(e)}")

# Made with Bob
