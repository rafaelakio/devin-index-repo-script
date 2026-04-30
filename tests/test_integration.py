import pytest


@pytest.mark.integration
def test_full_flow_requires_edge():
    """
    Placeholder for end-to-end integration test.
    Requires Microsoft Edge and valid Devin credentials.
    Run with: pytest -m integration
    """
    pytest.skip("Integration tests require Edge and live Devin session")
