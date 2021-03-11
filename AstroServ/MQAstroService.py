import os
import logging
import json
import signal

from common import MQPubCli

import numpy as np

from datetime import datetime, timezone
from skyfield import api as sf_api, almanac

from __deploy__ import Config
from SkyFieldCompute import *

DEBUG = os.environ.get('DEBUG')
logging.basicConfig(level=logging.NOTSET if DEBUG else logging.WARNING)

DRYRUN = os.environ.get('DRYRUN')

# Custom json encoder to handle numpy types
class CusEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(CusEncoder, self).default(obj)

# Load observer references
OBLOC = sf_api.Topos(latitude_degrees=Config.LOCAL_COORD['lat'],
                     longitude_degrees=Config.LOCAL_COORD['long'],
                     elevation_m=Config.LOCAL_COORD['alt_m'])

SUN_OBSERVER = PlanetObserver(SUN, OBLOC)
MOON_OBSERVER = PlanetObserver(MOON, OBLOC)

SUN_RISESET = PlanetRiseSet(SUN_OBSERVER, 0.5, SUN_TOP_HORIZON_APPARENT)
SUN_DAWNDUSK = PlanetRiseSet(SUN_OBSERVER, 0.5, SUN_CIVIL_TWILIGHT)
MOON_RISESET = PlanetRiseSet(MOON_OBSERVER, 0.5, MOON_TOP_HORIZON_APPARENT)

class MQAstroService(MQPubCli.IntervalPublisher):

    def on_connected(self, unix_ts, con_count):
        self._publish('earth/observer/coord', json.dumps(Config.LOCAL_COORD), retain=True)

    def on_interval(self, unix_ts):
        # === Observer (on Earth) Info ===
        # What is the time now
        TIME_TS = TIMESCALE.from_datetime(datetime.fromtimestamp(unix_ts, timezone.utc))
        TIME_DT = TIME_TS.utc_datetime()
        TIME_ORD = TIME_TS.toordinal()
        LOCAL_INFO = {
            'time': ( TIME_TS.utc_iso(), "%.3f"%unix_ts )
        }
        # What is this season
        SEASON_CUR = SEASONS(TIME_TS)
        SEASON_INFO = [ ( SEASON_CUR+1, almanac.SEASONS[SEASON_CUR] ) ]
        SEASON_INFO += SeasonProg(TIME_DT, TIME_ORD)
        LOCAL_INFO['season'] = SEASON_INFO
        self._publish('earth/observer', json.dumps(LOCAL_INFO, cls=CusEncoder), retain=True)

        # === Sun Info ===
        # Location from observer
        SUN_LOC = SUN_OBSERVER(TIME_TS).altaz()
        # Rise/set from the observability perspective
        SUN_CUROB = SUN_RISESET(TIME_TS)
        SUN_OBINFO = [ bool(SUN_CUROB) ]
        SUN_OBINFO += DayNightProg(TIME_DT, TIME_ORD, SUN_RISESET)
        # Dawn/dusk from the civil perspective
        SUN_CURDD = SUN_DAWNDUSK(TIME_TS)
        SUN_DDINFO = [ bool(SUN_CURDD) ]
        SUN_DDINFO += DayNightProg(TIME_DT, TIME_ORD, SUN_DAWNDUSK)
        SUN_INFO = {
            'position': [ round(SUN_LOC[0].degrees,2), round(SUN_LOC[1].degrees,2) ],
            'observable': SUN_OBINFO,
            'civic': SUN_DDINFO
        }
        self._publish('sun', json.dumps(SUN_INFO, cls=CusEncoder), retain=True)

        # === Moon Info ===
        MOON_CUROB = MOON_RISESET(TIME_TS)
        MOON_OBINFO = [ bool(MOON_CUROB) ]
        # Location from observer
        MOON_LOC = MOON_OBSERVER(TIME_TS).altaz()
        # Rise/set from the observability perspective
        MOON_OBINFO += MoonRiseSetProg(TIME_DT, TIME_ORD, MOON_RISESET)
        # Phase related information
        MOON_ILLUM = MOON_ILLUMOB(TIME_TS)
        MOON_PHDEG = MOON_PHDEGOB(TIME_TS)
        MOON_CURPH = MoonPhaseEx(MOON_PHDEG, MOON_ILLUM)
        MOON_PHNAME = [ MOON_CURPH+1, almanac.MOON_PHASES[MOON_CURPH//2] ]
        if MOON_CURPH & 1:
            MOON_PHNAME.append(MOON_PHASEEX_NAMES[MOON_CURPH])
        MOON_PHINFO = [
            MOON_PHNAME,
            round(MoonAge(TIME_TS, TIME_DT),3),
            round(MOON_ILLUM*100,2),
            MoonPhaseProg(TIME_DT, TIME_ORD)
        ]
        MOON_INFO = {
            'position': [ round(MOON_LOC[0].degrees,2), round(MOON_LOC[1].degrees,2) ],
            'observable': MOON_OBINFO,
            'phase': MOON_PHINFO
        }
        self._publish('moon', json.dumps(MOON_INFO, cls=CusEncoder), retain=True)

service = MQAstroService(__name__, Config.TOPIC_PFX, DRYRUN)

# Handle keyboard interruption
def CtrlCHandler(sig, frame):
    service.stop()
signal.signal(signal.SIGINT, CtrlCHandler)

service.run(Config.SERVER, Config.PORT, Config.USER, Config.PASS,
            Config.CACERTS, Config.INTERVAL)
