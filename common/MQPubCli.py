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

    def __init__(self, name, topic_pfx, dryrun, *,
                 dryrun_loglevel = logging.WARNING,
                 sub_pairs = []):
        self._LOGGER = logging.getLogger(name)
        self._PUB_TOPIC_PFX = topic_pfx or ''
        self._SUB_PAIRS = sub_pairs
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
        self._PUBCLI.on_message = self.on_message
        self._PUBCLI.on_subscribe = self.on_subscribe

    # Start the publisher client with given MQTT server and connection info,
    # and publish data at given interval (in seconds).
    # Does NOT return until:
    #  - stop() method is called, or
    #  - Mid-night maintenance window is reached.
    def run(self, server, port, user, passwd, cacerts, interval):
        self._setup(user, passwd, cacerts)
        if interval < 1:
            raise Exception("Avoid using interval < 1 second!")
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
    def _publish(self, sub_topic=None, message=None, qos=2, retain=False):
        if sub_topic:
            topic = os.path.join(self._PUB_TOPIC_PFX, sub_topic)
        else:
            topic = self._PUB_TOPIC_PFX
        log_level = self._DRYRUN_LOGLEVEL if self._DRYRUN else logging.DEBUG
        self._LOGGER.log(log_level, "MQTT [%s(%d%s)] <-- '%s'",
                         topic, qos, "+R" if retain else "", message)
        if not self._DRYRUN:
            self._PUBCLI.publish(topic, message, qos, retain)

    # Override to handle new connection (e.g. subscribe to topics)
    # Note that topic subscription is already handled.
    def on_connected(self, unix_ts, con_count):
        pass

    # Override to handle disconnects
    def on_disconnected(self, unix_ts, final):
        pass

    # Override to perform periodical publish
    def on_interval(self, unix_ts):
        pass

    # Override to process messages from subscriptions
    def on_receive(self, unix_ts, topic, message, qos, retain):
        pass

    # Handle connection events
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._CONNECTED = True
            self._CONCOUNT+= 1
            self._LOGGER.debug("Connected to MQTT server (#%d)", self._CONCOUNT)

            for topic, qos in self._SUB_PAIRS or []:
                result, mid = self._PUBCLI.subscribe(topic, qos)
                self._LOGGER.debug("Subscribing '%s' (QoS=%d) <-- %d", topic, qos, mid)
            self.on_connected(time.time(), self._CONCOUNT)
        else:
            self._CONNECTED = False
            self._LOGGER.warning("Connection error - %s", mqtt.connack_string(rc))

    # Handle disconnection events
    def on_disconnect(self, client, userdata, rc):
        self._CONNECTED = False
        if rc != 0:
            self._LOGGER.warning("Disconnected from MQTT server - %s",
                                 mqtt.connack_string(rc))
        self.on_disconnected(time.time(), rc == 0)

    # Handle subscription events
    def on_subscribe(self, client, userdata, mid, granted_qos):
        self._LOGGER.debug("Subscription %d granted (QoS=%s)", mid,
                           ','.join([str(qos) for qos in granted_qos]))

    # Handle messages from subscriptions
    def on_message(self, client, userdata, message):
        self._LOGGER.info("MQTT [%s(%d%s)] --> '%s'",
                         message.topic, message.qos, "+R" if message.retain else "",
                         message.payload.decode('utf-8'))
        self.on_receive(time.time(), message.topic, message.payload,
                        message.qos, message.retain)

