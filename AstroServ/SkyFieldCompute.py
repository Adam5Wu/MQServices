import logging

from numpy import cos, ndarray

from datetime import datetime, timedelta
from skyfield import api as sf_api, almanac
from skyfield.nutationlib import iau2000b

_logger = logging.getLogger(__name__)

# Useful constants
SECS_IN_HOUR=3600
HOURS_IN_DAY=24
SECS_IN_DAY=SECS_IN_HOUR*HOURS_IN_DAY
UNIX_TS_OFFSET=datetime(1970,1,1).toordinal()*SECS_IN_DAY
DAYS_IN_YEAR=365.2422
MOON_SYNODIC_PERIOD=29.53

# Load Skyfield data
TIMESCALE = sf_api.load.timescale()
PLANETS = sf_api.load('de421.bsp')
SUN = PLANETS['sun']
MOON = PLANETS['moon']
EARTH = PLANETS['earth']
SEASONS = almanac.seasons(PLANETS)

# Generalized from skyfield/almanac.py
def PlanetObserver(planet, topos):
    topos_at = (EARTH + topos).at

    def _observe_at(t):
        t._nutation_angles = iau2000b(t.tt)
        return topos_at(t).observe(planet).apparent()
    return _observe_at

# For computing sun/moon rise/set time
SUN_TOP_HORIZON = 0.26667
SUN_TOP_HORIZON_APPARENT = 0.8333
SUN_CIVIL_TWILIGHT = 6.0
SUN_NAUTICAL_TWILIGHT = 12.0
SUN_ASTRONOMICAL_TWILIGHT = 18.0

MOON_TOP_HORIZON = 0.26667
MOON_TOP_HORIZON_APPARENT = -0.125

def PlanetRiseSet(observer, rough_period, degref=0.0):
    def _is_planet_up_at(t):
        return observer(t).altaz()[0].degrees > -degref
    _is_planet_up_at.rough_period = rough_period
    return _is_planet_up_at

# For computing moon phase info
def ObjectPhaseAngleObserver(obj):
    def _phase_angle_at(t):
        pe = EARTH.at(t).observe(obj)
        pe.position.au *= -1     # rotate 180 degrees to point back at Earth
        t2 = t.ts.tt_jd(t.tt - pe.light_time)
        ps = obj.at(t2).observe(SUN)
        return pe.separation_from(ps)
    return _phase_angle_at

def ObjectIlluminationObserver(obj):
    phang_observer = ObjectPhaseAngleObserver(obj)
    def _illumination_at(t):
        phang = phang_observer(t)
        return 0.5*(1.0 + cos(phang.radians))
    return _illumination_at

def ObjectPhaseDegreeObserver(obj):
    def _phase_degree_at(t):
        t._nutation_angles = iau2000b(t.tt)
        e = EARTH.at(t)
        _, mlon, _ = e.observe(obj).apparent().ecliptic_latlon('date')
        _, slon, _ = e.observe(SUN).apparent().ecliptic_latlon('date')
        return (mlon.degrees - slon.degrees) % 360
    return _phase_degree_at

MOON_ILLUMOB = ObjectIlluminationObserver(MOON)
MOON_PHDEGOB = ObjectPhaseDegreeObserver(MOON)

# For deriving moon phase name and progression

MOON_ILLUM_THRES = [
    0.01,
    0.49,
    0.51,
    0.99
]
MOON_PHASEEX_NAMES = [
    'New Moon',
    'Waxing Crescent',
    'First Quarter',
    'Waxing Gibbous',
    'Full Moon',
    'Waning Gibbous',
    'Last Quarter',
    'Waning Crescent'
]

def MoonPhaseEx(phdeg, illum):
    if phdeg < 180:
        for i in range(4):
            if MOON_ILLUM_THRES[i] > illum:
                return i
        return 4
    else:
        for i in range(4):
            if MOON_ILLUM_THRES[3-i] < illum:
                return 4+i
        return 0

def MoonPhaseCycleObserver():
    def _moon_cycle(t):
        phdeg = MOON_PHDEGOB(t)
        moon_cycle = ndarray((len(t),),int)
        for ofs in range(len(t)):
            moon_cycle[ofs] = phdeg[ofs] >= 0 and phdeg[ofs] < 180
        return moon_cycle
    _moon_cycle.rough_period = MOON_SYNODIC_PERIOD // 2
    return _moon_cycle

MOON_PHASE_EVENTS = almanac.moon_phases(PLANETS)
MOON_PHASE_CYCLES = MoonPhaseCycleObserver()

# For computing progression of this season
def SeasonProg(time_dt, time_ordinal):
    QUARTER = DAYS_IN_YEAR/4
    period_start = TIMESCALE.utc(time_dt - timedelta(days=QUARTER+1))
    period_end = TIMESCALE.utc(time_dt + timedelta(days=QUARTER+1))
    ST, SI = almanac.find_discrete(period_start, period_end, SEASONS)
    ST_ORD = ST.toordinal().tolist()
    SI_ARR = SI.tolist()
    if len(ST_ORD) == 3:
        if time_ordinal >= ST_ORD[1]:
            SI_ARR.pop(0)
            ST_ORD.pop(0)
    if len(ST_ORD) != 2:
        _logger.warning("Unexpected seasons lookup - expect 2 entries, got %d", len(ST_ORD))
        return []
    season_start = ST_ORD[0]
    season_end = ST_ORD[1]
    season_length = season_end - season_start
    season_elapsed = time_ordinal - season_start
    season_remain = season_end - time_ordinal
    season_endts = season_end*SECS_IN_DAY - UNIX_TS_OFFSET
    return (
        round(season_elapsed,5), round(season_elapsed/season_length*100,2),
        round(season_endts,2), round(season_remain,5),
        almanac.SEASON_EVENTS[SI_ARR[1]]
    )

# For computing the Sun's day/night progression
def DayNightProg(time_dt, time_ordinal, ob_cond):
    period_start = TIMESCALE.utc(time_dt - timedelta(days=1))
    period_end = TIMESCALE.utc(time_dt + timedelta(days=1))
    ST, SI = almanac.find_discrete(period_start, period_end, ob_cond)
    ST_ORD = ST.toordinal().tolist()
    SI_ARR = SI.tolist()
    while len(ST_ORD) > 1:
        if ST_ORD[1] < time_ordinal:
            SI_ARR.pop(0)
            ST_ORD.pop(0)
        else:
            break
    if len(ST_ORD) in [0,1]:
        # If we are near polar regions, we may have [last_raise_set] or [] or [next_raise_set]
        # TODO: Support polar regions by expanding time period until we find the last/next event
        pass
    if len(ST_ORD) < 3:
        _logger.warning("Unexpected day-night lookup - expect 3+ entries, got %d", len(ST_ORD))
        return []

    # Normally, we have [last_raise_set, next_set_raise, ...]
    day_night_start = ST_ORD[0]
    day_night_end = ST_ORD[1]
    day_night_length = (day_night_end - day_night_start)*HOURS_IN_DAY
    day_night_elapsed = (time_ordinal - day_night_start)*HOURS_IN_DAY
    day_night_remain = (day_night_end - time_ordinal)*HOURS_IN_DAY
    day_night_endts = day_night_end*SECS_IN_DAY - UNIX_TS_OFFSET
    return (
        round(day_night_elapsed,3), round(day_night_elapsed/day_night_length*100,2),
        round(day_night_endts,2), round(day_night_remain,3)
    )

# For computing the Moon's rise/set progression
def MoonRiseSetProg(time_dt, time_ordinal, ob_cond):
    period_start = TIMESCALE.utc(time_dt - timedelta(days=1, hours=1))
    period_end = TIMESCALE.utc(time_dt + timedelta(days=1, hours=1))
    ST, SI = almanac.find_discrete(period_start, period_end, ob_cond)
    ST_ORD = ST.toordinal().tolist()
    SI_ARR = SI.tolist()
    while len(ST_ORD) > 1:
        if ST_ORD[1] < time_ordinal:
            SI_ARR.pop(0)
            ST_ORD.pop(0)
        else:
            break
    if len(ST_ORD) < 3:
        _logger.warning("Unexpected moon-night lookup - expect 3+ entries, got %d", len(ST_ORD))
        return []

    # We should have [last_raise_set, next_set_raise, ...]
    moon_night_start = ST_ORD[0]
    moon_night_end = ST_ORD[1]
    moon_night_length = (moon_night_end - moon_night_start)*HOURS_IN_DAY
    moon_night_elapsed = (time_ordinal - moon_night_start)*HOURS_IN_DAY
    moon_night_remain = (moon_night_end - time_ordinal)*HOURS_IN_DAY
    moon_night_endts = moon_night_end*SECS_IN_DAY - UNIX_TS_OFFSET
    return (
        round(moon_night_elapsed,3), round(moon_night_elapsed/moon_night_length*100,2),
        round(moon_night_endts,2), round(moon_night_remain,3)
    )

# For computing the Moon's phase progression
def MoonAge(time_ts, time_dt):
    period_start = TIMESCALE.utc(time_dt - timedelta(days=(MOON_SYNODIC_PERIOD // 1)+1))
    PT, PI = almanac.find_discrete(period_start, time_ts, MOON_PHASE_CYCLES)
    cycle_start = PT[-1] if PI[-1] else PT[-2]
    return time_ts-cycle_start

def MoonPhaseProg(time_dt, time_ordinal):
    QUARTER = MOON_SYNODIC_PERIOD // 4
    period_start = TIMESCALE.utc(time_dt - timedelta(days=QUARTER+1))
    period_end = TIMESCALE.utc(time_dt + timedelta(days=QUARTER+1))
    PT, PI = almanac.find_discrete(period_start, period_end, MOON_PHASE_EVENTS)
    PT_ORD = PT.toordinal().tolist()
    PI_ARR = PI.tolist()
    if len(PT_ORD) == 3:
        if time_ordinal >= PT_ORD[1]:
            PI_ARR.pop(0)
            PT_ORD.pop(0)
    if len(PT_ORD) != 2:
       _logger.warning("Unexpected moon-phase lookup - expect 2 entries, got %d", len(PT_ORD))
       return []

    phase_start = PT_ORD[0]
    phase_end = PT_ORD[1]
    phase_length = phase_end - phase_start
    phase_elapsed = time_ordinal - phase_start
    phase_remain = phase_end - time_ordinal
    phase_endts = phase_end*SECS_IN_DAY-UNIX_TS_OFFSET
    return (
        round(phase_elapsed,3), round(phase_elapsed/phase_length*100,2),
        round(phase_endts,2), round(phase_remain,3),
        almanac.MOON_PHASES[PI_ARR[1]]
    )
