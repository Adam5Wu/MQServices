# MQTT client configurations
SERVER="<MQTT server IP or DNS name>"
PORT=8883
CACERTS=None or "<path to SSL CA certificate>"
USER="<username>"
PASS="<password>"

# Publish every N seconds
INTERVAL=10

# All messages will be published under this prefix
TOPIC_PFX="/infr/clock"
