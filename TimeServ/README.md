# MQTT Time Service
Publishes the current time info at a configurable interval (default = 10 sec).
Enables your devices without NTP capabilities to track time with reasonable accuracy.

- UTC date and time, and UNIX time with sub-second granularity.
- Local time and timezone info, with daylight saving support.
    - No need to separately manage these messy configurations per device.
- Ethnic calendars info for adding cultural features support to your devices.
    - Currently supports Chinese Lunar calendar.

## Install
Recommended running with Python 3.7+.

1. Install dependent modules:
    ```
    python3 -m pip install -r requirements.txt
    ```
2. Configure the service:
    - Create `__deploy__` sub-directory;
    - Make a copy of `Config.py` in `__deploy__`;
    - Edit `__deploy__/Config.py` as fit.
3. Test connecting to the MQTT server:
    ```
    DRYRUN=1 python3 MQTimeService.py
    ```
4. Test publishing data:
    ```
    python3 MQTimeService.py
    ```
5. Install as service:
    ```
    > crontab -e
    # m h dom mon dow   command
    * * * * *       cd /path/to/TimeServ/__deploy__ && flock -E 0 -xnF Service.lock python3 ../MQTimeService.py
    ```

## Consume
- Topic: `/infr/clock/Local`
    - Sample: `[2021, 3, 9, 12, 10, 44, 1, 68, false]`
    - Field Meaning: `[<year>, <month>, <day>, <hour>, <minute>, <second>, <day-of-week>, <day-of-year>, <daylight_saving_in_effect>]`
- Topic: `/infr/clock/Local/tz`
    - Sample: `[["EST", 18000], ["EDT", 14400]]`
    - Field Meaning:
        - `[<local_timezone_name>, <offset_from_utc_seconds>]`
        - `[<daylight_saving_timezone_name>, <offset_from_utc_seconds>]`
    - If your region does not practice daylight saving, the outer array will only have one entry, e.g. `[["UTC", 0]]`
- Topic: `/infr/clock/UTC`
    - Sample: `[2021, 3, 9, 19, 10, 44, 1, 68]`
    - Field Meaning: `[<year>, <month>, <day>, <hour>, <minute>, <second>, <day-of-week>, <day-of-year>]`
- Topic: `/infr/clock/UTC/unix`
    - Sample: `1615335044.878`
    - Field Meaning: Unix timestamp
- Topic: `/infr/clock/Lunar`
    - Sample: `[[2021, 3, 10, 3, 10, 44, 1, 68], [2021, 1, false, 27], [[[3, "\u60ca\u86f0", "awakening of insects"], 5], [[4, "\u6625\u5206", "vernal equinox"], 10]]]`
    - Field Meaning:
        1. Time in China (UTC+8): `[<year>, <month>, <day>, <hour>, <minute>, <second>, <day-of-week>, <day-of-year>]`
        2. Lunar date: `[<lunar_year>, <lunar_month>, <is_leap_month>, <lunar_day>]`
        3. Solar term:
            1.  `[[<index_of_past_term>, <past_term_native_name>, <past_term_english_name>], <days_since_past_term>]`
            2.  `[[<index_of_next_term>, <next_term_native_name>, <next_term_english_name>], <days_to_next_term>]`
