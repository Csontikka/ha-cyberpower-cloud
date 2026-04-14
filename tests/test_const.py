"""Tests for CyberPower Cloud constants."""
from custom_components.cyberpower_cloud.const import (
    API_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UPS_RATED_POWER,
    DOMAIN,
    EVENT_POWER_OUTAGE_ENDED,
    EVENT_POWER_OUTAGE_STARTED,
)


def test_domain() -> None:
    """Test domain constant."""
    assert DOMAIN == "cyberpower_cloud"


def test_api_base_url() -> None:
    """Test API base URL."""
    assert API_BASE_URL.startswith("https://")


def test_default_scan_interval() -> None:
    """Test default scan interval is reasonable."""
    assert 60 <= DEFAULT_SCAN_INTERVAL <= 3600


def test_default_ups_rated_power_forces_configuration() -> None:
    """Test default rated power is 0 to force user configuration."""
    assert DEFAULT_UPS_RATED_POWER == 0


def test_event_names_contain_domain() -> None:
    """Test event names include the domain prefix."""
    assert EVENT_POWER_OUTAGE_STARTED.startswith(DOMAIN)
    assert EVENT_POWER_OUTAGE_ENDED.startswith(DOMAIN)
