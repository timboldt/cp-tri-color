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

BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000


def get_forecast(requests, url):
    resp = requests.get(url)
    json_data = resp.json()
    return json_data["daily"], json_data["current"]["dt"], json_data["timezone_offset"]


def temperature_text(temp: float) -> tuple[str, int, int]:
    if temp < 30:
        return " Frz", WHITE, RED
    elif temp < 50:
        return "Cold", WHITE, BLACK
    elif temp < 70:
        return "Cool", BLACK, WHITE
    elif temp < 80:
        return "Mild", BLACK, WHITE
    elif temp < 90:
        return "Warm", WHITE, BLACK
    else:
        return " Hot ", WHITE, RED


def humidity_text(humidity: int, temp: float) -> tuple[str, int, int]:
    if humidity < 20:
        return "Dry", BLACK, WHITE
    elif humidity < 60:
        return "Norm", BLACK, WHITE
    elif temp >= 70:
        return " Hum ", WHITE, RED
    else:
        return "Norm", BLACK, WHITE


def wind_text(wind_speed: float) -> tuple[str, int, int]:
    if wind_speed < 5:
        return "Calm", BLACK, WHITE
    elif wind_speed < 15:
        return "Brzy", BLACK, WHITE
    elif wind_speed < 30:
        return "Windy", WHITE, BLACK
    else:
        return "Storm", WHITE, RED


def make_today_banner(city, data, tz_offset, battery_percent):
    date = time.localtime(data["dt"])
    sunrise = time.localtime(data["sunrise"] + tz_offset)
    sunset = time.localtime(data["sunset"] + tz_offset)

    bat_pct = label.Label(
        terminalio.FONT,
        text=f"{int(battery_percent):2d}%",
        color=BLACK,
    )
    bat_pct.anchor_point = (1.0, 0)
    bat_pct.anchored_position = (190, 14)
    if battery_percent < 20:
        bat_pct.color = WHITE
        bat_pct.background_color = BLACK

    today_date = label.Label(
        terminalio.FONT,
        text=f"{DAYS[date.tm_wday].upper()} {MONTHS[date.tm_mon - 1].upper()} {date.tm_mday}, {date.tm_year}",
        color=BLACK,
    )
    today_date.anchor_point = (0, 0)
    today_date.anchored_position = (15, 14)

    city_name = label.Label(terminalio.FONT, text=city, color=BLACK)
    city_name.anchor_point = (0, 0)
    city_name.anchored_position = (15, 25)

    today_icon = displayio.TileGrid(
        icons_large_bmp,
        pixel_shader=icons_small_pal,  # type: ignore
        x=10,
        y=40,
        width=1,
        height=1,
        tile_width=70,
        tile_height=70,
    )
    today_icon[0] = ICON_MAP.index(data["weather"][0]["icon"][:2])

    (txt, fg, bg) = temperature_text(data["temp"]["morn"])
    today_morn_temp = label.Label(
        terminalio.FONT,
        text=txt,
        color=fg,
        background_color=bg,
    )
    today_morn_temp.anchor_point = (0.5, 0)
    today_morn_temp.anchored_position = (118, 59)

    (txt, fg, bg) = temperature_text(data["temp"]["day"])
    today_day_temp = label.Label(
        terminalio.FONT,
        text=txt,
        color=fg,
        background_color=bg,
    )
    today_day_temp.anchor_point = (0.5, 0)
    today_day_temp.anchored_position = (149, 59)

    (txt, fg, bg) = temperature_text(data["temp"]["night"])
    today_night_temp = label.Label(
        terminalio.FONT,
        text=txt,
        color=fg,
        background_color=bg,
    )
    today_night_temp.anchor_point = (0.5, 0)
    today_night_temp.anchored_position = (180, 59)

    (txt, fg, bg) = humidity_text(data["humidity"], data["temp"]["day"])
    today_humidity = label.Label(
        terminalio.FONT,
        text=txt,
        color=fg,
        background_color=bg,
    )
    today_humidity.anchor_point = (0, 0.5)
    today_humidity.anchored_position = (105, 95)

    (txt, fg, bg) = wind_text(data["wind_speed"])
    today_wind = label.Label(
        terminalio.FONT,
        text=txt,
        color=fg,
        background_color=bg,
    )
    today_wind.anchor_point = (0, 0.5)
    today_wind.anchored_position = (160, 95)

    today_sunrise = label.Label(
        terminalio.FONT,
        text=f"{sunrise.tm_hour:2d}:{sunrise.tm_min:02d} AM",
        color=BLACK,
    )
    today_sunrise.anchor_point = (0, 0.5)
    today_sunrise.anchored_position = (45, 117)

    today_sunset = label.Label(
        terminalio.FONT,
        text=f"{sunset.tm_hour - 12:2d}:{sunset.tm_min:02d} PM",
        color=BLACK,
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
        color=BLACK,
    )
    day_of_week.anchor_point = (0, 0.5)
    day_of_week.anchored_position = (0, 10)

    icon = displayio.TileGrid(
        icons_small_bmp,
        pixel_shader=icons_small_pal,  # type: ignore
        x=25,
        y=0,
        width=1,
        height=1,
        tile_width=20,
        tile_height=20,
    )
    icon[0] = ICON_MAP.index(data["weather"][0]["icon"][:2])

    (txt, fg, bg) = temperature_text(data["temp"]["day"])
    day_temp = label.Label(
        terminalio.FONT,
        text=txt,
        color=fg,
        background_color=bg,
    )
    day_temp.anchor_point = (0, 0.5)
    day_temp.anchored_position = (50, 10)

    group = displayio.Group(x=x, y=y)
    group.append(day_of_week)
    group.append(icon)
    group.append(day_temp)

    return group


# Initialize I2C and battery monitor early to check battery level
i2c = board.I2C()
battery_monitor = adafruit_max1704x.MAX17048(i2c)
battery_percent = battery_monitor.cell_percent

# Only fetch weather data if battery level is sufficient
# This saves ~20mAh per day when battery is critically low
if battery_percent > 15:
    try:
        wifi.radio.connect(
            os.getenv("CIRCUITPY_WIFI_SSID"),
            os.getenv("CIRCUITPY_WIFI_PASSWORD"),
        )
        print("Connected to:", os.getenv("CIRCUITPY_WIFI_SSID"))
    except TypeError:
        print("Could not find WiFi info. Check your settings.toml file!")
        raise

    try:
        url = (
            "https://api.openweathermap.org/data/3.0/onecall"
            + "?lat="
            + os.getenv("OPEN_WEATHER_LAT")  # type: ignore
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
else:
    print(f"Battery too low ({battery_percent:.1f}%), skipping WiFi to conserve power")
    requests = None

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

# Used to ensure the display is free in CircuitPython
displayio.release_displays()

# Define the pins needed for display use
# This pinout is for a Feather M4 and may be different for other boards
spi = board.SPI()  # Uses SCK and MOSI
epd_cs = board.D9  # type: ignore
epd_dc = board.D10  # type: ignore
epd_reset = board.D5
epd_busy = board.D6  # type: ignore

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
    highlight_color=RED,
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

# Only fetch weather if WiFi was enabled (battery sufficient)
if requests is not None:
    forecast_data, utc_time, local_tz_offset = get_forecast(requests, url)
else:
    # Use current time for display when skipping WiFi
    forecast_data = None
    utc_time = time.time()
    local_tz_offset = -8 * 3600  # Default to PST

# Place the display group on the screen
display.root_group = g

# Only display weather if we fetched data; otherwise show low battery message
if forecast_data is not None:
    city = "Pleasanton, CA"
    today_banner = make_today_banner(
        city=city,
        data=forecast_data[0],
        tz_offset=local_tz_offset,
        battery_percent=battery_percent,
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
else:
    # Display low battery message
    low_battery_msg = label.Label(
        terminalio.FONT,
        text=f"Battery Low: {battery_percent:.1f}%",
        color=WHITE,
        background_color=RED,
    )
    low_battery_msg.anchor_point = (0.5, 0.5)
    low_battery_msg.anchored_position = (148, 30)
    g.append(low_battery_msg)

    power_save_msg = label.Label(
        terminalio.FONT,
        text="Power Save Mode",
        color=BLACK,
    )
    power_save_msg.anchor_point = (0.5, 0.5)
    power_save_msg.anchored_position = (148, 50)
    g.append(power_save_msg)

    recharge_msg = label.Label(
        terminalio.FONT,
        text="Please Recharge",
        color=BLACK,
    )
    recharge_msg.anchor_point = (0.5, 0.5)
    recharge_msg.anchored_position = (148, 70)
    g.append(recharge_msg)

# Explicitly disable WiFi to save power during display refresh and deep sleep
# Unconditionally disable to ensure lowest possible power consumption
wifi.radio.enabled = False

# Refresh the display to have it actually show the image
# NOTE: Do not refresh eInk displays sooner than 180 seconds
display.refresh()
time.sleep(20)  # Allow time for the display to refresh (reduced from 30s to save power)
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

time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_seconds)  # type: ignore

# Turn off I2C power by setting it to input
i2c_power = digitalio.DigitalInOut(board.I2C_POWER)  # type: ignore
i2c_power.switch_to_input()
alarm.exit_and_deep_sleep_until_alarms(time_alarm)

# Should never reach here, but just in case.
time.sleep(180)
