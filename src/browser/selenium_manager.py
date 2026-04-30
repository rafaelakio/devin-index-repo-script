import logging
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager

logger = logging.getLogger("devin_indexer.browser")


def _build_options(headless: bool) -> EdgeOptions:
    options = EdgeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    return options


def create_driver(headless: bool = False) -> webdriver.Edge:
    options = _build_options(headless)
    service = EdgeService(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    driver.implicitly_wait(10)
    mode = "headless" if headless else "visible"
    logger.debug(f"Edge driver created ({mode})")
    return driver


def quit_driver(driver: webdriver.Edge) -> None:
    try:
        driver.quit()
        logger.debug("Edge driver closed")
    except Exception:
        pass
