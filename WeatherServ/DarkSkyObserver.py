import time
import logging

from pprint import pformat

from darksky.api import DarkSky
from darksky.types import languages, units, weather

_logger = logging.getLogger(__name__)

def WeatherObserver(apikey, loc):
    darksky = DarkSky(apikey)
    def _forecast_fetch(units=units.AUTO, lang=languages.ENGLISH):
        return darksky.get_forecast(loc['lat'], loc['long'], units=units, lang=lang)
    return _forecast_fetch

def TimeToTS(t):
    return 0 if t is None else int(time.mktime(t.timetuple()))

def BearingToDir(deg):
    val = int((deg/22.5)+.5)
    name = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW"
    ]
    return name[val % 16]

def ArrayRLE(arr):
    out = []
    last = arr[0]
    count = -1

    def _flush():
        nonlocal count, out, last
        if count < 2:
            out.append(last)
        else:
            out.append(['RLE', count, last])
        count = 0

    for item in arr:
        if last == item:
            count += 1
            continue
        _flush()
        last = item
    _flush()
    return out

def PrecipDigest(data):
    out = [ data.precip_probability, getattr(data, 'precip_type', '-') ]
    if hasattr(data, 'precip_intensity_error'):
        out.append([data.precip_intensity, data.precip_intensity_error])
    else:
        out.append(data.precip_intensity)
    return out

def WindDigest(data):
    out = [
        ( data.wind_bearing, BearingToDir(data.wind_bearing) ),
        data.wind_speed,
    ]
    if hasattr(data, 'wind_gust_time'):
        out.append([data.wind_gust, TimeToTS(data.wind_gust_time)])
    else:
        out.append(data.wind_gust)
    return out

def EnvDigest(data):
    out = [ int(data.cloud_cover*100), data.visibility, data.ozone ]
    if hasattr(data, 'uv_index_time'):
        out.append([data.uv_index, TimeToTS(data.uv_index_time)])
    else:
        out.append(data.uv_index)
    return out

def ForecastDigestBase(data):
    return {
        '@': data.summary,
        'H': ( int(data.humidity*100), data.dew_point ),
        'W': WindDigest(data),
        'E': EnvDigest(data),
    }

def ForecastDigest(data):
    out = ForecastDigestBase(data)
    out['T'] = ( data.temperature, data.apparent_temperature )
    out['P'] = [ data.pressure, PrecipDigest(data) ]
    return out

def ForecastDigestEx(data):
    out = ForecastDigestBase(data)
    out['T'] = (
        ( data.temperature_high, TimeToTS(data.temperature_high_time) ),
        ( data.apparent_temperature_high, TimeToTS(data.apparent_temperature_high_time) ),
        ( data.temperature_low, TimeToTS(data.temperature_low_time) ),
        ( data.apparent_temperature_low, TimeToTS(data.apparent_temperature_low_time) ),
    )
    out['P'] = (
        data.pressure,
        PrecipDigest(data) + [(
            data.precip_intensity_max, TimeToTS(data.precip_intensity_max_time)
        )],
    )
    return out

class Feed:

    def __init__(self, apikey, loc):
        self._OBSERVER = WeatherObserver(apikey, loc)
        self._DATA = None

    def refresh(self):
        self._DATA = self._OBSERVER()
        return self.stamp()

    def stamp(self):
        DATA = self._DATA
        try:
            return (
                TimeToTS(DATA.currently.time),
                ( DATA.latitude, DATA.longitude ),
                DATA.flags.units
            )
        except:
            _logger.exception("Exception while processing weather data: %s", pformat(DATA))

    def current_condition(self):
        CC = self._DATA.currently
        try:
            FORECAST = ForecastDigest(CC)
            if hasattr(CC, 'nearest_storm_distance'):
                FORECAST['P'].append(CC.nearest_storm_distance)
            return FORECAST
        except:
            _logger.exception("Exception while processing current condition: %s", pformat(CC))

    def minutely_forecast(self):
        MC = self._DATA.minutely
        try:
            return (
                MC.summary,
                ( TimeToTS(MC.data[0].time), TimeToTS(MC.data[-1].time) ),
                ArrayRLE([ PrecipDigest(MI) for MI in MC.data ])
            )
        except:
            _logger.exception("Exception while processing minutely forecast: %s", pformat(MC))

    def hourly_forecast(self):
        HC = self._DATA.hourly
        try:
            return (
                HC.summary,
                ( TimeToTS(HC.data[0].time), TimeToTS(HC.data[-1].time) ),
                [ ForecastDigest(HI) for HI in HC.data ]
            )
        except:
            _logger.exception("Exception while processing hourly forecast: %s", pformat(HC))

    def daily_forecast(self):
        DC = self._DATA.daily
        try:
            return (
                DC.summary,
                ( TimeToTS(DC.data[0].time), TimeToTS(DC.data[-1].time) ),
                [ ForecastDigestEx(DI) for DI in DC.data ]
            )
        except:
            _logger.exception("Exception while processing daily forecast: %s", pformat(DC))

    def alerts(self):
        AL = self._DATA.alerts
        try:
            ALERTS = []
            for AI in AL:
                ALERTS.append([
                    AI.title,
                    ( TimeToTS(AI.time), TimeToTS(AI.expires) ),
                    AI.description
                ])
            return ALERTS
        except:
            _logger.exception("Exception while processing alerts: %s", pformat(AL))

