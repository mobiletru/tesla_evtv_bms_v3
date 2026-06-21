DOMAIN = "tesla_evtv_bms_v3"
PLATFORMS = ["sensor"]

CONF_NAME = "name"
CONF_PORT = "port"
CONF_MODULE_COUNT = "module_count"
CONF_MODULES_IN_SERIES = "modules_in_series"

CONF_SMA_ENABLED = "sma_enabled"
CONF_SMA_MODE = "sma_mode"
SMA_MODE_LITECAN = "litecan"
SMA_MODE_PCAN = "pcan"

CONF_LITECAN_HOST = "litecan_host"
CONF_LITECAN_PORT = "litecan_port"
CONF_PCAN_CHANNEL = "pcan_channel"
CONF_PCAN_INTERFACE = "pcan_interface"
CONF_PCAN_BITRATE = "pcan_bitrate"

PCAN_INTERFACE_SOCKETCAN = "socketcan"
PCAN_INTERFACE_PCAN = "pcan"

CONF_CHARGE_VOLTAGE = "charge_voltage"
CONF_CHARGE_CURRENT = "charge_current_limit"
CONF_DISCHARGE_CURRENT = "discharge_current_limit"
CONF_DISCHARGE_VOLTAGE = "discharge_voltage_limit"
CONF_INVERT_CURRENT = "invert_current"

DEFAULT_LITECAN_PORT = 6851
DEFAULT_PCAN_INTERFACE = PCAN_INTERFACE_SOCKETCAN
DEFAULT_PCAN_CHANNEL = "can0"
DEFAULT_PCAN_BITRATE = 500000

SMA_MESSAGE_INTERVAL = 0.25  # 250ms between frames (SMA inhibit >= 200ms)

SIGNAL_UPDATE_ENTITY = f"{DOMAIN}_{{}}_update"
