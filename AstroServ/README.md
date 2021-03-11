# MQTT Astronomical Service
Publishes current astronomical observation info at a configurable interval (default = 5 min). Enables your devices to adjust presentations (e.g. lights on-off, cold/warm colors) with daily and seasonal environments.

- Sun's position, rise-set time, and civil dawn-dusk time.
- Moon's position, rise-set time, and phase info.
    - For moon-observing hobbyists. :D
- Local seasonal data.

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
        - Set `LOCAL_COORD` as accurate as possible, as it affects observation results.
3. Test connecting to the MQTT server:
    ```
    DRYRUN=1 python3 MQAstroService.py
    ```
4. Test publishing data:
    ```
    python3 MQAstroService.py
    ```
5. Install as service:
    ```
    > crontab -e
    # m h dom mon dow     command
    * * * * *    cd /path/to/AstroServ/__deploy__ && flock -E 0 -xnF Service.lock python3 ../MQAstroService.py
    ```

## Consume
- Topic: `/infr/astro/earth/observer/coord`
    - Sample: `{"lat": 38.9058115, "long": -77.0501575, "alt_m": 13.5}`
- Topic: `/infr/astro/earth/observer`
    - Sample: `{"time": ["2021-03-11T05:49:38Z", "1615441777.673"], "season": [[4, "Winter"], 79.8245, 89.71, 1616233048.52, 9.15823, "Vernal Equinox"]}`
    - Field Meaning:
        - time: `[<iso_datetime>, <unix_timestamp>]`
        - season:
            - `[<index_of_current_season>, <name_of_current_season>]`
            - `[<days_in_season>, <percentage_elapsed>, <next_season_start_timestamp>, <days_to_next_season>, <next_seasonal_event_name>]`
- Topic: `/infr/astro/sun`
    - Sample: `{"position": [-54.0, 13.41], "observable": [false, 6.652, 54.32, 1615461916.16, 5.594], "civic": [false, 6.208, 54.65, 1615460323.25, 5.152]}`
    - Field Meaning:
        - position: `[<altitude>, <azimuth>]`
        - observable: `[<is_observable>, <hours_elapsed>, <percentage>, <next_event_timestamp>, <hours_to_next_event>]`
        - civic: `[<is_civic_day_time>, <hours_elapsed>, <percentage>, <next_event_timestamp>, <hours_to_next_event>]`
    - For environmental control (e.g. lights on-off) civic time is a better choice, since it takes into account of dawn and dusk -- when the sun is not directly observable but natural ambient light is still plenty, thanks to atmospheric refraction and dispersion.
- Topic: `/infr/astro/moon`
    - Sample: `{"position": [-56.59, 59.61], "observable": [false, 9.522, 64.78, 1615460415.51, 5.177], "phase": [[8, "Last Quarter", "Waning Crescent"], 27.447, 5.11, [5.18, 70.3, 1615630869.72, 2.189, "New Moon"]]}`
    - Field Meaning:
        - position: `[<altitude>, <azimuth>]`
        - observable: `[<is_observable>, <hours_elapsed>, <percentage>, <next_event_timestamp>, <hours_to_next_event>]`
        - phase:
            - `[<index_of_current_phase>, <name_of_last_event>, <name_of_current_transition>]`
            - `<moon_age_in_days>`
            - `<percent_of_illumination>`
            - `[<days_since_last_event>, <percentage_elapsed>, <next_phase_event_timestamp>, <days_to_next_event>, <name_of_next_event>]`
    - The moon phases consist of 4 phase "events" and 4 phase "transitions", interleaved:
        - **New Moon** --[ Waxing Crescent ]-->
        - **First Quarter** --[ Waxing Gibbous ]-->
        - **Full Moon** --[ Waning Gibbous ]-->
        - **Last Quarter** --[ Waning Crescent ]-->
    - The phase "events" have fairly short durations, for windows of ~2% change in area of illumination.
     - During the "event" period, the `<name_of_current_transition>` is not published (i.e. the first array in "phase" value will only have 2 entries).
