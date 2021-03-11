# MQTT client configurations
SERVER="<MQTT server IP or DNS name>"
PORT=8883
CACERTS=None or "<path to SSL CA certificate>"
USER="<username>"
PASS="<password>"

# Publish every N seconds
INTERVAL=300

# All messages will be published under this prefix
TOPIC_PFX="/infr/astro"

# Observer location on earth
LOCAL_COORD={
    'lat': 38.9058115,
    'long': -77.0501575,
    'alt_m': 13.5
}
