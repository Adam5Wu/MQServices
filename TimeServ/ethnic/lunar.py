from datetime import datetime

import pytz
from lunarcalendar import Lunar
from lunarcalendar.solarterm import solarterms

from . import registry

LUNAR_TIMEZONE = pytz.timezone('Asia/Shanghai')
LUNAR_NATIVELANG = 'zh_hans'

def GetLunarInfo(unix_ts, time_conv):
    ethnic_time = datetime.fromtimestamp(unix_ts, LUNAR_TIMEZONE)
    lunar_date = Lunar.from_date(ethnic_time.date())
    lunar_info = [
        time_conv(ethnic_time.timetuple(), 1),
        ( lunar_date.year, lunar_date.month, lunar_date.isleap, lunar_date.day )
    ]
    ethnic_date = ethnic_time.date()
    # Compute the progression of solar terms
    scan_year = lunar_date.year
    last_term = None
    next_term = None
    while not next_term:
        for i in range(24):
            term = solarterms[i]
            term_date = term(scan_year)
            if term_date <= ethnic_date:
                last_term = ( i+1, term, term_date )
            else:
                next_term = ( i+1, term, term_date )
                break
        scan_year += 1
    lunar_info.append((
        (
            ( last_term[0], last_term[1].langs[LUNAR_NATIVELANG][0], last_term[1].langs['en'][0] ),
            (ethnic_date - last_term[2]).days
        ), (
            ( next_term[0], next_term[1].langs[LUNAR_NATIVELANG][0], next_term[1].langs['en'][0] ),
            (next_term[2] - ethnic_date).days
        )
    ))
    return lunar_info

registry['Lunar'] = GetLunarInfo
