"""
Session and cookie management for maintaining authentication state.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from src.utils.logger import get_logger

logger = get_logger()


class SessionHandler:
    """Handles saving and loading browser session cookies."""
    
    def __init__(self, session_file: str = "session.json"):
        """
        Initialize session handler.
        
        Args:
            session_file: Path to file for storing session cookies
        """
        self.session_file = Path(session_file)
        self.cookies: List[Dict] = []
        
    def save_cookies(self, driver) -> None:
        """
        Save cookies from the current browser session.
        
        Args:
            driver: Selenium WebDriver instance
        """
        try:
            self.cookies = driver.get_cookies()
            
            session_data = {
                'cookies': self.cookies,
                'saved_at': datetime.now().isoformat(),
                'url': driver.current_url
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)
            
            logger.info(f"Session saved to {self.session_file}")
            logger.debug(f"Saved {len(self.cookies)} cookies")
            
        except Exception as e:
            logger.error(f"Failed to save session: {str(e)}")
            raise
    
    def load_cookies(self, driver) -> bool:
        """
        Load cookies into the browser session.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if cookies were loaded successfully, False otherwise
        """
        if not self.session_file.exists():
            logger.info("No saved session found")
            return False
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            self.cookies = session_data.get('cookies', [])
            saved_at = datetime.fromisoformat(session_data.get('saved_at', ''))
            
            # Check if session is too old (more than 7 days)
            if datetime.now() - saved_at > timedelta(days=7):
                logger.warning("Saved session is older than 7 days, may be expired")
            
            # Navigate to the domain first
            saved_url = session_data.get('url', '')
            if saved_url:
                # Extract domain from URL
                from urllib.parse import urlparse
                parsed = urlparse(saved_url)
                domain_url = f"{parsed.scheme}://{parsed.netloc}"
                driver.get(domain_url)
            
            # Add cookies to the browser
            for cookie in self.cookies:
                try:
                    # Remove problematic fields
                    cookie_copy = cookie.copy()
                    cookie_copy.pop('sameSite', None)
                    cookie_copy.pop('expiry', None)
                    driver.add_cookie(cookie_copy)
                except Exception as e:
                    logger.debug(f"Failed to add cookie {cookie.get('name')}: {str(e)}")
            
            logger.info(f"Loaded {len(self.cookies)} cookies from session")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load session: {str(e)}")
            return False
    
    def is_session_valid(self, driver) -> bool:
        """
        Check if the current session is still valid.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if session is valid, False otherwise
        """
        try:
            # Check if we're on a login page or have access to protected content
            current_url = driver.current_url
            
            # If we're on a login page, session is invalid
            if 'login' in current_url.lower() or 'signin' in current_url.lower():
                logger.warning("Session appears to be invalid (on login page)")
                return False
            
            # Check if we have the expected cookies
            current_cookies = driver.get_cookies()
            if not current_cookies:
                logger.warning("No cookies found in current session")
                return False
            
            logger.info("Session appears to be valid")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate session: {str(e)}")
            return False
    
    def clear_session(self) -> None:
        """Delete the saved session file."""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                logger.info("Session file deleted")
        except Exception as e:
            logger.error(f"Failed to delete session file: {str(e)}")
    
    def get_session_info(self) -> Optional[Dict]:
        """
        Get information about the saved session.
        
        Returns:
            Dictionary with session info or None if no session exists
        """
        if not self.session_file.exists():
            return None
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            saved_at = datetime.fromisoformat(session_data.get('saved_at', ''))
            age = datetime.now() - saved_at
            
            return {
                'file': str(self.session_file),
                'saved_at': session_data.get('saved_at'),
                'age_days': age.days,
                'url': session_data.get('url'),
                'cookie_count': len(session_data.get('cookies', []))
            }
            
        except Exception as e:
            logger.error(f"Failed to get session info: {str(e)}")
            return None

# Made with Bob
