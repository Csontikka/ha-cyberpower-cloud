"""Constants for CyberPower Cloud integration."""

DOMAIN = "cyberpower_cloud"
API_BASE_URL = "https://iotapi.cyberpower.com"
HMAC_SECRET = "cyberpower@TP08!"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes

CONF_UPS_RATED_POWER = "ups_rated_power"
DEFAULT_UPS_RATED_POWER = 0  # 0 = not configured, user must set per device

EVENT_POWER_OUTAGE_STARTED = f"{DOMAIN}_power_outage_started"
EVENT_POWER_OUTAGE_ENDED = f"{DOMAIN}_power_outage_ended"
