# MQTT Weather Service
Publishes current and forecast local weather info at a configurable interval (default = 5 min).

- Current temperature, humidity, wind, precipitation and uv.
- Forecasts of the next few days.
- Active NWS alerts.

Note: Current data is sourced from DarkSky which is scheduled to shutdown in early 2022. Will switch to OpenWeatherMap soon.

## Install
Recommended running with Python 3.7+.

1. Install dependent modules:
    ```
    python3 -m pip install -r requirements.txt --ignore-installed pytz
    ```
2. Configure the service:
    - Create `__deploy__` sub-directory;
    - Make a copy of `Config.py` in `__deploy__`;
    - Edit `__deploy__/Config.py` as fit.
        - Set `LOCAL_COORD` as accurate as possible, as it affects observation results.
3. Test connecting to the MQTT server:
    ```
    DRYRUN=1 python3 MQWeatherService.py
    ```
4. Test publishing data:
    ```
    python3 MQWeatherService.py
    ```
5. Install as service:
    ```
    > crontab -e
    # m h dom mon dow   command
    * * * * *       cd /path/to/WeatherServ/__deploy__ && flock -E 0 -xnF Service.lock python3 ../MQWeatherService.py
    ```

## Consume
- Topic: `/infr/weather/stamp`
    - Sample: `[1617593472, [38.9058115, -77.0501575], "us"]`
    - Field Meaning: `[<unix_timestamp_of_observation>, [<station_latitude>, <station_longitude>], <measuring_units>]`
- Topic: `/infr/weather/current`
    - Sample: `{"@": "Partly Cloudy", "H": [66, 44.62], "W": [[316, "NW"], 7.57, 18.07], "E": [40, 10, 391, 0], "T": [55.97, 55.97], "P": [1014.2, [0, "-", 0], 34]}`
    - Field Meaning:
        - `@`: `<text description of current condition>`
        - `H`: `[<relative humidity percentage>, <dew point>]`
        - `W`: `[[<wind direction degrees>, <name>], <speed>, <gust speed>]`
        - `E`: `[<cloud cover percentage>, <visibility distance>, <ozone density>, <uv index>]`
        - `T`: `[<temperature>, <feels like>]`
        - `P`: `[<atmospherical pressure>, [<precipitation probability>, <type>, <intensity>], <?nearest storm distance?>]`
            - The last element, `<nearest storm distance>` may not present if no storm is near by.
- Topic: `/infr/weather/forecast/minutely`
    - Sample: `["Partly cloudy for the hour.", [1619404740, 1619408340], [["RLE", 60, [0, "-", 0]]]]`
    - Field Meaning: `[<text description of forecast of next hour>, [<unix timestamp start time>, <end time>], [(run-length encoded)60*[<precipitation probability>, <type>, <intensity>]]]`
        - The last element is a per-minute precipitation forecast. It is run-length encoded, so that for N minutes with the same forecast values, they are expressed as `["RLE", N, (forecast data)]`. 
- Topic: `/infr/weather/forecast/hourly`
    - Sample: `["Clear throughout the day.", [1619402400, 1619575200], [{"@": "Partly Cloudy", "H": [66, 45.7], "W": [[301, "WNW"], 6.65, 15.74], "E": [50, 10, 390.8, 0], "T": [57.06, 57.06], "P": [1013.6, [0, "-", 0]]}, ...]]`
    - Field Meaning: `[<text description of forecast of next day>, [<unix timestamp start time>, <end time>]], [24*(hourly forecast data)]`
        - Hourly forecast data fields:
            - `@`: `<text description of the hour>`
            - `H`: `[<relative humidity percentage>, <dew point>]`
            - `W`: `[[<wind direction degrees>, <name>], <speed>, <gust speed>]`
            - `E`: `[<cloud cover percentage>, <visibility distance>, <ozone density>, <uv index>]`
            - `T`: `[<temperature>, <feels like>]`
            - `P`: `[<atmospherical pressure>, [<precipitation probability>, <type>, <intensity>]]`
- Topic: `/infr/weather/forecast/daily`
    - Sample: `["Rain today through Friday.", [1619323200, 1619928000], [{"@": "Light rain in the morning.", "H": [75, 47.44], "W": [[326, "NW"], 8.25, [23.82, 1619382780]], "E": [77, 9.013, 373.9, [5, 1619373600]], "T": [[66.71, 1619385600], [66.21, 1619385600], [40.67, 1619434560], [35.52, 1619434620]], "P": [1009.1, [0.97, "rain", 0.0141, [0.1292, 1619323200]]]}, ...]]`
    - Field Meaning: `[<text description of forecast of next week>, [<unix timestamp start time>, <end time>]], [7*(daily forecast data)]`
        - Daily forecast data fields:
            - `@`: `<text description of the day>`
            - `H`: `[<relative humidity percentage>, <dew point>]`
            - `W`: `[[<wind direction degrees>, <name>], <speed>, [<peak gust speed>, <unix timestamp>]]`
            - `E`: `[<cloud cover percentage>, <visibility distance>, <ozone density>, [<peak uv index>, <unix timestamp>]]`
            - `T`: `[[<high temperature>, <unix timestamp>], [<high feels like>, <unix timestamp>], [<low temperature>, <unix timestamp>], [<low feels like>, <unix timestamp>]]`
            - `P`: `[<atmospherical pressure>, [<precipitation probability>, <type>, <intensity>, [<max intensity>, <unix timestamp>]]]`
- Topic: `/infr/weather/alerts`
    - Sample: `[["Flood Watch for Mason, WA", [1509993360, 1510036680], "...FLOOD WATCH REMAINS IN EFFECT THROUGH LATE MONDAY NIGHT...\nTHE FLOOD WATCH CONTINUES FOR\n* A PORTION OF NORTHWEST WASHINGTON..."], ...]`
    - Field Meaning: `[<alert title>, [<unix timestamp effective>, <expires>], <alert description>]`

