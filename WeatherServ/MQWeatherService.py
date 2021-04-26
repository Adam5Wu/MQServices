import os
import logging
import time
import json
import signal

from common import MQPubCli

from DarkSkyObserver import Feed as DSOFeed

from __deploy__ import Config

DEBUG = os.environ.get('DEBUG')
logging.basicConfig(level=logging.NOTSET if DEBUG else logging.WARNING)

DRYRUN = os.environ.get('DRYRUN')

WEATHER_FEED = DSOFeed(Config.WS_APIKEY, Config.LOCAL_COORD)

class MQWeatherService(MQPubCli.IntervalPublisher):

    def on_interval(self, unix_ts):
        STAMP = WEATHER_FEED.refresh()
        self._publish('stamp', json.dumps(STAMP), retain=True)

        CC = WEATHER_FEED.current_condition()
        self._publish('current', json.dumps(CC), retain=True)

        MC = WEATHER_FEED.minutely_forecast()
        self._publish('forecast/minutely', json.dumps(MC), retain=True)

        HC = WEATHER_FEED.hourly_forecast()
        self._publish('forecast/hourly', json.dumps(HC), retain=True)

        DC = WEATHER_FEED.daily_forecast()
        self._publish('forecast/daily', json.dumps(DC), retain=True)

        ALERTS = WEATHER_FEED.alerts()
        self._publish('alerts', json.dumps(ALERTS), retain=True)

service = MQWeatherService(__name__, Config.TOPIC_PFX, DRYRUN)

# Handle keyboard interruption
def CtrlCHandler(sig, frame):
    service.stop()
signal.signal(signal.SIGINT, CtrlCHandler)

service.run(Config.SERVER, Config.PORT, Config.USER, Config.PASS,
            Config.CACERTS, Config.INTERVAL)
