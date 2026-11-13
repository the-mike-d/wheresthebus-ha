"""Constants for the WheresTheBus integration (unofficial)."""

DOMAIN = "wheresthebus"
PLATFORMS = ["sensor", "binary_sensor", "device_tracker"]

BASE_URL = "https://mdt.wheresthebus.com/"
API = "wtbparentapp/api/v2/"
DEVICE_TYPE = "FlutterWeb"
DEVICE_OS = "Web_chrome_Flutter"

CONF_DEVICE_ID = "device_id"
CONF_DRIVE_MIN = "drive_minutes"
CONF_BUFFER_MIN = "buffer_minutes"
CONF_AM_WINDOW = "am_window"
CONF_PM_WINDOW = "pm_window"
CONF_WEEKDAYS_ONLY = "weekdays_only"
CONF_AM_ENABLED = "am_enabled"
CONF_PM_ENABLED = "pm_enabled"
CONF_HOME_ZONE = "home_zone"
CONF_ALERT_MILES = "alert_miles"
CONF_ALERT_MODE = "alert_mode"
ALERT_MODES = ["distance", "time", "either"]

DEFAULT_DRIVE_MIN = 3
DEFAULT_BUFFER_MIN = 3
DEFAULT_AM_WINDOW = "06:00-07:00"
DEFAULT_PM_WINDOW = "14:00-15:00"
DEFAULT_AM_ENABLED = False
DEFAULT_PM_ENABLED = True
DEFAULT_HOME_ZONE = "zone.home"
DEFAULT_ALERT_MILES = 1.0
DEFAULT_ALERT_MODE = "distance"  # minutes estimates are unreliable on routes with many stops

FAST_INTERVAL = 15  # seconds, matches the app
IDLE_INTERVAL = 300  # seconds, outside bus windows (no API calls are made)
FALLBACK_MPH = 15.0  # kept for reference; ETA is hidden until the bus's own speed is learned
MIN_MPH = 8.0  # floor for the learned speed (stops at other kids' houses drag it down)
MAX_MPH = 45.0
WARMUP_SECONDS = 180  # no ETA until this long after tracking starts in a window
ARRIVED_MILES = 0.1  # WheresTheBus reports tenths of a mile; bus this close to the stop = it has reached the stop
