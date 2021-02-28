# MQServices

A collection of various information provider services.
They are designed to periodically publish to a local MQTT server for the purposes of enriching functionalities of IoT devices on the network.

Note:
- All services publish data in human readable format (json) to facilitate easy debugging.
- However, most data is published in array format, as opposed to a more readable dict (key-value pair) format.
This is a compromise to the fact that many IoT devices have limited network bandwidth and/or memory and processing power.

## TimeServ
Publishes the current time info at a configurable interval (default = 10 sec).
Enables your devices without NTP capabilities to track time with reasonable accuracy.

- UTC date and time, and UNIX time with sub-second granularity.
- Local time and timezone info, with daylight saving support.
    - No need to separately manage these messy configurations per device.
- Ethnic calendars info for adding cultural features support to your devices.
    - Currently supports Chinese Lunar calendar.

## AstroServ
Publishes current astronomical observation info at a configurable interval (default = 5 min).
Enables your devices to adjust presentations (e.g. lights on-off, cold/warm colors) with daily and seasonal environments.

- Sun's position, rise-set time, and civil dawn-dusk time.
- Moon's position, rise-set time, and phase info.
    - For moon-observing hobbyists. :D
- Local seasonal data.

## WeatherServ
Publishes current and forecast local weather info at a configurable interval (default = 5 min).

- Current temperature, humidity, wind, precipitation and uv.
- Forecasts of the next few days.
- Active NWS alerts.

Note: Current data is sourced from DarkSky which is scheduled to shutdown in early 2022. Will switch to OpenWeatherMap soon.

## HikCam
Publishes events and alerts from HikVision cameras.

- Maps multiple cameras into semantic topics (e.g. /home/interior/doorway, /home/exterior/patio).
- Publishes all configurable events (e.g. motion, line-crossing, PIR) and alerts (e.g. tampering, storage).

## KODI	
Transcribes message from [kodi2mqtt](https://github.com/owagner/kodi2mqtt).	
Enables your devices to adjust presentation (e.g. lights dim in/out) in response to your KODI video playing.

- Distills information from multiple topics into a single one for easy processing by low power devices.
