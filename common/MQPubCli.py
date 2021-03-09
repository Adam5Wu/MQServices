# Common implementatiosn of MQTT data publishers

import os
import time
import logging
import paho.mqtt.client as mqtt

"""
An MQTT client that publishes at regular interval
"""
class IntervalPublisher:
    _PUBCLI = mqtt.Client()

    def __init__(self, name, topic_pfx, dryrun, dryrun_loglevel = logging.WARNING):
        self._LOGGER = logging.getLogger(name)
        self._TOPIC_PFX = topic_pfx
        self._DRYRUN = dryrun
        self._DRYRUN_LOGLEVEL = dryrun_loglevel
        # State variables used during run() and accessed in callbacks
        self._STOP = None
        self._CONNECTED = None
        self._CONCOUNT = None

    # Setup MQTT server connection information
    def _setup(self, user, passwd, cacerts):
        self._PUBCLI.username_pw_set(user, passwd)
        if cacerts:
            self._PUBCLI.tls_set(cacerts)
        self._PUBCLI.on_connect = self.on_connect
        self._PUBCLI.on_disconnect = self.on_disconnect

    # Start the publisher client with given MQTT server and connection info,
    # and publish data at given interval (in seconds).
    # Does NOT return until:
    #  - stop() method is called, or
    #  - Mid-night maintenance window is reached.
    def run(self, server, port, user, passwd, cacerts, interval):
        self._setup(user, passwd, cacerts)
        self._LOGGER.debug("Connecting to MQTT server '%s'...", server)
        self._PUBCLI.connect_async(server, port)
        self._PUBCLI.loop_start()

        self._STOP = False
        self._CONNECTED = False
        self._CONCOUNT = 0
        while not self._STOP:
            self._idleWait(interval)
            UNIXTS = time.time()
            if self._CONNECTED:
                self.on_interval(UNIXTS)
            self._checkMaintTime(UNIXTS, interval)

        self._PUBCLI.loop_stop()
        self._PUBCLI.disconnect()

    # Signal the run-loop to stop
    def stop(self):
        self._LOGGER.warning('Stop signal received')
        self._STOP = True

    # Wait for a given interval (in seconds) or stop signal
    def _idleWait(self, timeout):
        while timeout > 0 and not self._STOP:
            time.sleep(1)
            timeout-= 1

    # Check if we are at mid-night maintenance window
    def _checkMaintTime(self, unix_ts, interval):
        local_time = time.localtime(unix_ts)
        if local_time.tm_hour*3600 + local_time.tm_min*60 < interval*1.5:
            self._LOGGER.info("Scheduled maintenance termination at midnight")
            self._STOP = True

    # Publish a message to specified MQTT topic
    def _publish(self, sub_topic, message, qos=2, retain=False):
        if sub_topic:
            topic = os.path.join(self._TOPIC_PFX, sub_topic)
        else:
            topic = self._TOPIC_PFX
        log_level = self._DRYRUN_LOGLEVEL if self._DRYRUN else logging.DEBUG
        self._LOGGER.log(log_level, "MQTT [%s(%d%s)] <-- '%s'",
                         topic, qos, "+R" if retain else "", message)
        if not self._DRYRUN:
            self._PUBCLI.publish(topic, message, qos, retain)

    # Override to handle new connection (e.g. subscribe to topics)
    def on_connected(self, unix_ts, con_count):
        pass

    def on_interval(self, unix_ts):
        self._publish(None, "Override on_publish() to publish data")

    # Handle connection events
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._CONNECTED = True
            self._CONCOUNT+= 1
            self._LOGGER.debug("Connected to MQTT server (#%d)", self._CONCOUNT)

            UNIXTS = time.time()
            self.on_connected(UNIXTS, self._CONCOUNT)
        else:
            self._CONNECTED = False
            self._LOGGER.warning("Connection error - %s", mqtt.connack_string(rc))

    # Handle disconnection events
    def on_disconnect(self, client, userdata, rc):
        self._CONNECTED = False
        if rc != 0:
            self._LOGGER.warning("Disconnected from MQTT server - %s",
                                 mqtt.connack_string(rc))
