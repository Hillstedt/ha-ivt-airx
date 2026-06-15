DOMAIN = "ivt_airx"
MANUFACTURER = "IVT / Bosch Thermotechnology"

# Config entry keys
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_EXPIRES_AT = "expires_at"
CONF_GATEWAY_ID = "gateway_id"

# OAuth2 / SingleKey ID
OAUTH_AUTHORIZE_URL = "https://singlekey-id.com/auth/connect/authorize"
OAUTH_TOKEN_URL = "https://singlekey-id.com/auth/connect/token"
OAUTH_CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
OAUTH_REDIRECT_URI = "com.bosch.tt.dashtt.pointt://app/login"
OAUTH_STYLE_ID = "tt_bsch"
OAUTH_SCOPES = (
    "openid",
    "email",
    "profile",
    "offline_access",
    "pointt.gateway.claiming",
    "pointt.gateway.removal",
    "pointt.gateway.list",
    "pointt.gateway.users",
    "pointt.gateway.resource.dashapp",
    "pointt.castt.flow.token-exchange",
    "bacon",
)

# PoinTT API
POINTT_BASE_URL = "https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1"
POINTT_USER_AGENT = "DashApp/3.7.0 (iOS-Release)"

# Polling
DEFAULT_SCAN_INTERVAL = 120  # seconds

# Sentinel values the API uses for "not available"
SENTINEL_VALUES = (32767.0, -32768.0, 32767, -32768)

# ── API resource paths ────────────────────────────────────────

# System
PATH_OUTDOOR_TEMP = "/system/sensors/temperatures/outdoor_t1"
PATH_SYSTEM_BRAND = "/system/brand"
PATH_SYSTEM_TYPE = "/system/type"

# Gateway
PATH_GW_FIRMWARE = "/gateway/versionFirmware"
PATH_GW_HARDWARE = "/gateway/versionHardware"
PATH_GW_SERIAL = "/gateway/serialId"
PATH_GW_MAC = "/gateway/wifi/mac"

# Heat sources
PATH_SUPPLY_TEMP = "/heatSources/actualSupplyTemperature"
PATH_RETURN_TEMP = "/heatSources/returnTemperature"
PATH_MODULATION = "/heatSources/actualModulation"
PATH_COMPRESSOR_STATUS = "/heatSources/compressor/status"
PATH_CH_STATUS = "/heatSources/chStatus"

# DHW
PATH_DHW_TEMP = "/dhwCircuits/dhw1/actualTemp"
