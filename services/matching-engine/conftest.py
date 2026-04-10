"""Pytest configuration for matching engine tests"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set the event loop policy for Windows compatibility"""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    if sys.platform == "win32":
        loop = asyncio.new_event_loop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
