# MQTT client configurations
SERVER="<MQTT server IP or DNS name>"
PORT=8883
CACERTS=None or "<path to SSL CA certificate>"
USER="<username>"
PASS="<password>"

import MQTE as L

def _TFUNC(context, payload):
    return L.MQTEResult()

# A list of MQTE instances
TLIST=[
  L.MQTE("Transcriber-Name", ["/subscribe/topic/1", "/subscribe/topic/2"], _TFUNC)
]

# All messages will be published under this prefix
TOPIC_PFX=None
