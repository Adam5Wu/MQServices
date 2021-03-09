import os
import logging
import time
import json
import signal

from common import MQPubCli

import ethnic
from ethnic import *

from __deploy__ import Config

DEBUG = os.environ.get('DEBUG')
logging.basicConfig(level=logging.NOTSET if DEBUG else logging.WARNING)

DRYRUN = os.environ.get('DRYRUN')

# Load local timezone information
CLOCK_TZS = [ [ time.tzname[0], time.timezone ] ]
if time.daylight:
    CLOCK_TZS.append([ time.tzname[1], time.altzone ])

def ConvertStructTime(stime,tzcnt):
    tscomp = [
        stime[0], stime[1], stime[2],
        stime[3], stime[4], stime[5],
        stime[6], stime[7]
    ]
    if tzcnt > 1:
        tscomp.append(bool(stime[8]))
    return tscomp

class MQTimeService(MQPubCli.IntervalPublisher):

    def on_connected(self, unix_ts, con_count):
        self._publish('Local/tz', json.dumps(CLOCK_TZS), retain=True)

    def on_interval(self, unix_ts):
        utc_info = ConvertStructTime(time.gmtime(unix_ts), 1)
        self._publish('UTC', json.dumps(utc_info))
        self._publish('UTC/unix', "%.3f" % unix_ts)

        loc_info = ConvertStructTime(time.localtime(unix_ts), len(CLOCK_TZS))
        self._publish('Local', json.dumps(loc_info))

        for sub_topic, func in ethnic.registry.items():
            ethnic_info = func(unix_ts, ConvertStructTime)
            self._publish(sub_topic, json.dumps(ethnic_info))

service = MQTimeService(__name__, Config.TOPIC_PFX, DRYRUN)

# Handle keyboard interruption
def CtrlCHandler(sig, frame):
    service.stop()
signal.signal(signal.SIGINT, CtrlCHandler)

service.run(Config.SERVER, Config.PORT, Config.USER, Config.PASS,
            Config.CACERTS, Config.INTERVAL)
