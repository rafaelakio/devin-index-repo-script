import pytest
from unittest.mock import MagicMock, patch


def test_extract_repo_list_empty():
    from src.scraper.extractor import extract_repo_list
    driver = MagicMock()
    driver.find_elements.return_value = []
    result = extract_repo_list(driver)
    assert result == []


def test_extract_repo_list_filters_missing_name():
    from src.scraper.extractor import extract_repo_list
    from selenium.common.exceptions import NoSuchElementException

    driver = MagicMock()
    card = MagicMock()
    card.find_element.side_effect = NoSuchElementException()
    driver.find_elements.return_value = [card]

    result = extract_repo_list(driver)
    assert result == []
