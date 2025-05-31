import os
import ssl
import time

import adafruit_il0373
import adafruit_imageload
import adafruit_max1704x
import adafruit_requests
import alarm
import board
import digitalio
import displayio
import fourwire
import socketpool
import terminalio
import wifi
from adafruit_display_text import label


def get_forecast(requests, url):
    resp = requests.get(url)
    json_data = resp.json()
    return json_data["daily"], json_data["current"]["dt"], json_data["timezone_offset"]


def make_today_banner(city, data, tz_offset, battery_percent):
    date = time.localtime(data["dt"])
    sunrise = time.localtime(data["sunrise"] + tz_offset)
    sunset = time.localtime(data["sunset"] + tz_offset)

    bat_pct = label.Label(
        terminalio.FONT,
        text=f"{int(battery_percent):2d}%",
        color=0x000000,
    )
    bat_pct.anchor_point = (1.0, 0)
    bat_pct.anchored_position = (190, 14)
    if battery_percent < 20:
        bat_pct.color = 0xFFFFFF
        bat_pct.background_color = 0xFF0000

    today_date = label.Label(
        terminalio.FONT,
        text=f"{DAYS[date.tm_wday].upper()} {MONTHS[date.tm_mon - 1].upper()} {date.tm_mday}, {date.tm_year}",
        color=0x000000,
    )
    today_date.anchor_point = (0, 0)
    today_date.anchored_position = (15, 14)

    city_name = label.Label(terminalio.FONT, text=city, color=0x000000)
    city_name.anchor_point = (0, 0)
    city_name.anchored_position = (15, 25)

    today_icon = displayio.TileGrid(
        icons_large_bmp,
        pixel_shader=icons_small_pal,
        x=10,
        y=40,
        width=1,
        height=1,
        tile_width=70,
        tile_height=70,
    )
    today_icon[0] = ICON_MAP.index(data["weather"][0]["icon"][:2])

    today_morn_temp = label.Label(
        terminalio.FONT, text="{:3.0f}F".format(data["temp"]["morn"]), color=0x000000,
    )
    today_morn_temp.anchor_point = (0.5, 0)
    today_morn_temp.anchored_position = (118, 59)
    if int(data["temp"]["morn"]) < 30:
        today_morn_temp.color = 0xFFFFFF
        today_morn_temp.background_color = 0xFF0000

    today_day_temp = label.Label(
        terminalio.FONT, text="{:3.0f}F".format(data["temp"]["day"]), color=0x000000,
    )
    today_day_temp.anchor_point = (0.5, 0)
    today_day_temp.anchored_position = (149, 59)
    if int(data["temp"]["day"]) >= 90:
        today_day_temp.color = 0xFFFFFF
        today_day_temp.background_color = 0xFF0000

    today_night_temp = label.Label(
        terminalio.FONT, text="{:3.0f}F".format(data["temp"]["night"]), color=0x000000,
    )
    today_night_temp.anchor_point = (0.5, 0)
    today_night_temp.anchored_position = (180, 59)
    if int(data["temp"]["night"]) < 30:
        today_night_temp.color = 0xFFFFFF
        today_night_temp.background_color = 0xFF0000

    today_humidity = label.Label(
        terminalio.FONT, text="{:3d}%".format(data["humidity"]), color=0x000000,
    )
    today_humidity.anchor_point = (0, 0.5)
    today_humidity.anchored_position = (105, 95)
    if int(data["humidity"]) < 20 or int(data["humidity"]) > 80:
        today_humidity.color = 0xFFFFFF
        today_humidity.background_color = 0xFF0000

    today_wind = label.Label(
        terminalio.FONT, text="{:3.0f}mph".format(data["wind_speed"]), color=0x000000,
    )
    today_wind.anchor_point = (0, 0.5)
    today_wind.anchored_position = (155, 95)
    if int(data["wind_speed"]) > 30:
        today_wind.color = 0xFFFFFF
        today_wind.background_color = 0xFF0000

    today_sunrise = label.Label(
        terminalio.FONT,
        text=f"{sunrise.tm_hour:2d}:{sunrise.tm_min:02d} AM",
        color=0x000000,
    )
    today_sunrise.anchor_point = (0, 0.5)
    today_sunrise.anchored_position = (45, 117)

    today_sunset = label.Label(
        terminalio.FONT,
        text=f"{sunset.tm_hour - 12:2d}:{sunset.tm_min:02d} PM",
        color=0x000000,
    )
    today_sunset.anchor_point = (0, 0.5)
    today_sunset.anchored_position = (130, 117)

    group = displayio.Group()
    group.append(bat_pct)
    group.append(today_date)
    group.append(city_name)
    group.append(today_icon)
    group.append(today_morn_temp)
    group.append(today_day_temp)
    group.append(today_night_temp)
    group.append(today_humidity)
    group.append(today_wind)
    group.append(today_sunrise)
    group.append(today_sunset)

    return group


def make_future_day_banner(x, y, data):
    """Make a single future forecast info banner group."""
    day_of_week = label.Label(
        terminalio.FONT,
        text=DAYS[time.localtime(data["dt"]).tm_wday][:3].upper(),
        color=0x000000,
    )
    day_of_week.anchor_point = (0, 0.5)
    day_of_week.anchored_position = (0, 10)

    icon = displayio.TileGrid(
        icons_small_bmp,
        pixel_shader=icons_small_pal,
        x=25,
        y=0,
        width=1,
        height=1,
        tile_width=20,
        tile_height=20,
    )
    icon[0] = ICON_MAP.index(data["weather"][0]["icon"][:2])

    day_temp = label.Label(
        terminalio.FONT, text="{:3.0f}F".format(data["temp"]["day"]), color=0x000000,
    )
    day_temp.anchor_point = (0, 0.5)
    day_temp.anchored_position = (50, 10)
    if (
        int(data["temp"]["day"]) >= 95
        or int(data["temp"]["night"]) <= 25
        or int(data["temp"]["morn"]) <= 25
    ):
        day_temp.color = 0xFFFFFF
        day_temp.background_color = 0xFF0000

    group = displayio.Group(x=x, y=y)
    group.append(day_of_week)
    group.append(icon)
    group.append(day_temp)

    return group


try:
    wifi.radio.connect(
        os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"),
    )
    print("Connected to:", os.getenv("CIRCUITPY_WIFI_SSID"))
except TypeError:
    print("Could not find WiFi info. Check your settings.toml file!")
    raise

try:
    url = (
        "https://api.openweathermap.org/data/3.0/onecall"
        + "?lat="
        + os.getenv("OPEN_WEATHER_LAT")
        + "&lon="
        + os.getenv("OPEN_WEATHER_LON")
        + "&units=imperial&exclude=minutely,hourly"
        + "&appid="
        + os.getenv("OPEN_WEATHER_KEY")
    )
except TypeError:
    print("Could not find OpenWeatherMap token. Check your settings.toml file!")
    raise

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

BACKGROUND_BMP = "/bmps/weather_bg.bmp"
ICONS_LARGE_FILE = "/bmps/weather_icons_70px.bmp"
ICONS_SMALL_FILE = "/bmps/weather_icons_20px.bmp"
ICON_MAP = ("01", "02", "03", "04", "09", "10", "11", "13", "50")
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

i2c = board.I2C()
battery_monitor = adafruit_max1704x.MAX17048(board.I2C())

# Used to ensure the display is free in CircuitPython
displayio.release_displays()

# Define the pins needed for display use
# This pinout is for a Feather M4 and may be different for other boards
spi = board.SPI()  # Uses SCK and MOSI
epd_cs = board.D9
epd_dc = board.D10
epd_reset = board.D5
epd_busy = board.D6

# Create the displayio connection to the display pins
display_bus = fourwire.FourWire(
    spi,
    command=epd_dc,
    chip_select=epd_cs,
    reset=epd_reset,
    baudrate=1000000,
)
time.sleep(1)  # Wait a bit

# Create the display object - the third color is red (0xff0000)
display = adafruit_il0373.IL0373(
    display_bus,
    width=296,
    height=128,
    rotation=270,
    busy_pin=epd_busy,
    highlight_color=0xFF0000,
)

# Create a display group for our screen objects
g = displayio.Group()

# Display a ruler graphic from the root directory of the CIRCUITPY drive
bg = open(BACKGROUND_BMP, "rb")
bg_pic = displayio.OnDiskBitmap(bg)
bg_tg = displayio.TileGrid(bg_pic, pixel_shader=bg_pic.pixel_shader)
g.append(bg_tg)

icons_large_bmp, icons_large_pal = adafruit_imageload.load(ICONS_LARGE_FILE)
icons_small_bmp, icons_small_pal = adafruit_imageload.load(ICONS_SMALL_FILE)

forecast_data, utc_time, local_tz_offset = get_forecast(requests, url)

# Place the display group on the screen
display.root_group = g

city = "Pleasanton, CA"
today_banner = make_today_banner(
    city=city,
    data=forecast_data[0],
    tz_offset=local_tz_offset,
    battery_percent=battery_monitor.cell_percent,
)
g.append(today_banner)

future_banners = [
    make_future_day_banner(x=210, y=18, data=forecast_data[1]),
    make_future_day_banner(x=210, y=39, data=forecast_data[2]),
    make_future_day_banner(x=210, y=60, data=forecast_data[3]),
    make_future_day_banner(x=210, y=81, data=forecast_data[4]),
    make_future_day_banner(x=210, y=102, data=forecast_data[5]),
]
for future_banner in future_banners:
    g.append(future_banner)

# Refresh the display to have it actually show the image
# NOTE: Do not refresh eInk displays sooner than 180 seconds
display.refresh()
time.sleep(30)  # Allow time for the display to refresh
print("refreshed")

local_now = time.localtime(utc_time + local_tz_offset)
# Target wake time: 6:00 AM local time
target_hour = 6
target_minute = 0
target_second = 0
# Compute seconds since midnight for current and target times
seconds_now = local_now.tm_hour * 3600 + local_now.tm_min * 60 + local_now.tm_sec
seconds_target = target_hour * 3600 + target_minute * 60 + target_second

# Compute delay until next 6:00 AM
if seconds_now < seconds_target:
    sleep_seconds = seconds_target - seconds_now
else:
    # Next day's 6:00 AM
    sleep_seconds = (24 * 3600 - seconds_now) + seconds_target

print("Sleeping for", sleep_seconds, "seconds")

time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_seconds)

# Turn off I2C power by setting it to input
i2c_power = digitalio.DigitalInOut(board.I2C_POWER)
i2c_power.switch_to_input()
alarm.exit_and_deep_sleep_until_alarms(time_alarm)

# Should never reach here, but just in case.
time.sleep(180)
