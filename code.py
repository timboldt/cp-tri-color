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


def required_setting(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name} in settings.toml")
    return value


def fetch_forecast():
    """Connect to WiFi, fetch the forecast, and always turn the radio back off."""
    try:
        wifi.radio.connect(
            required_setting("WIFI_SSID"), required_setting("WIFI_PASSWORD")
        )
        print("Connected to:", os.getenv("WIFI_SSID"))
        url = (
            "https://api.openweathermap.org/data/3.0/onecall"
            + "?lat="
            + required_setting("OPEN_WEATHER_LAT")
            + "&lon="
            + required_setting("OPEN_WEATHER_LON")
            + "&units=imperial&exclude=minutely,hourly,alerts"
            + "&appid="
            + required_setting("OPEN_WEATHER_KEY")
        )
        pool = socketpool.SocketPool(wifi.radio)
        requests = adafruit_requests.Session(pool, ssl.create_default_context())
        resp = requests.get(url)
        try:
            json_data = resp.json()
        finally:
            resp.close()
        return (
            json_data["daily"],
            json_data["current"]["dt"],
            json_data["timezone_offset"],
        )
    finally:
        wifi.radio.enabled = False


def icon_index(data):
    """Map an OpenWeatherMap icon code to a sprite index (cloud if unknown)."""
    code = data["weather"][0]["icon"][:2]
    if code in ICON_MAP:
        return ICON_MAP.index(code)
    print("Unknown icon code:", code)
    return ICON_MAP.index("03")


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
        # High humidity and warm temps feel uncomfortable
        return " Hum ", WHITE, RED
    else:
        # High humidity at cooler temps feels normal
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


def clock_text(t):
    """Format a struct_time as a 12-hour clock time, e.g. " 6:42 AM"."""
    hour = t.tm_hour % 12 or 12
    suffix = "AM" if t.tm_hour < 12 else "PM"
    return f"{hour:2d}:{t.tm_min:02d} {suffix}"


def make_today_banner(city, data, tz_offset, battery_percent):
    date = time.localtime(data["dt"] + tz_offset)
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
        pixel_shader=icons_large_pal,  # type: ignore
        x=10,
        y=40,
        width=1,
        height=1,
        tile_width=70,
        tile_height=70,
    )
    today_icon[0] = icon_index(data)

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
        text=clock_text(sunrise),
        color=BLACK,
    )
    today_sunrise.anchor_point = (0, 0.5)
    today_sunrise.anchored_position = (45, 117)

    today_sunset = label.Label(
        terminalio.FONT,
        text=clock_text(sunset),
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


def make_future_day_banner(x, y, data, tz_offset):
    """Make a single future forecast info banner group."""
    day_of_week = label.Label(
        terminalio.FONT,
        text=DAYS[time.localtime(data["dt"] + tz_offset).tm_wday][:3].upper(),
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
    icon[0] = icon_index(data)

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


BACKGROUND_BMP = "/bmps/weather_bg.bmp"
ICONS_LARGE_FILE = "/bmps/weather_icons_70px.bmp"
ICONS_SMALL_FILE = "/bmps/weather_icons_20px.bmp"
ICON_MAP = ("01", "02", "03", "04", "09", "10", "11", "13", "50")
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

CITY = "Pleasanton, CA"
LOW_BATTERY_PERCENT = 15
WAKE_HOUR = 6  # Local time to wake for the next update
ERROR_RETRY_SECONDS = 60 * 60  # Retry an hour after a failed update
LOW_BATTERY_SLEEP_SECONDS = 24 * 3600
REFRESH_TIMEOUT_SECONDS = 60


def init_display():
    # Used to ensure the display is free in CircuitPython
    displayio.release_displays()

    # Pins for the tri-color e-ink FeatherWing
    spi = board.SPI()  # Uses SCK and MOSI
    display_bus = fourwire.FourWire(
        spi,
        command=board.D10,  # type: ignore
        chip_select=board.D9,  # type: ignore
        reset=board.D5,
        baudrate=1000000,
    )
    return adafruit_il0373.IL0373(
        display_bus,
        width=296,
        height=128,
        rotation=270,
        busy_pin=board.D6,  # type: ignore
        highlight_color=RED,
    )


def show(display, group):
    """Refresh the e-ink display and wait until the panel reports it is done."""
    display.root_group = group
    # NOTE: Do not refresh eInk displays sooner than 180 seconds
    display.refresh()
    deadline = time.monotonic() + REFRESH_TIMEOUT_SECONDS
    while display.busy and time.monotonic() < deadline:
        time.sleep(0.1)
    print("refreshed")


def background_group():
    g = displayio.Group()
    bg_pic = displayio.OnDiskBitmap(BACKGROUND_BMP)
    g.append(displayio.TileGrid(bg_pic, pixel_shader=bg_pic.pixel_shader))
    return g


def show_forecast(display, forecast_data, tz_offset, battery_percent):
    global icons_large_bmp, icons_large_pal, icons_small_bmp, icons_small_pal
    icons_large_bmp, icons_large_pal = adafruit_imageload.load(ICONS_LARGE_FILE)
    icons_small_bmp, icons_small_pal = adafruit_imageload.load(ICONS_SMALL_FILE)

    g = background_group()
    g.append(
        make_today_banner(
            city=CITY,
            data=forecast_data[0],
            tz_offset=tz_offset,
            battery_percent=battery_percent,
        )
    )
    for i in range(5):
        g.append(
            make_future_day_banner(
                x=210, y=18 + 21 * i, data=forecast_data[i + 1], tz_offset=tz_offset
            )
        )
    show(display, g)


def show_low_battery(display, battery_percent):
    g = background_group()
    low_battery_msg = label.Label(
        terminalio.FONT,
        text=f"Battery Low: {battery_percent:.0f}%",
        color=WHITE,
        background_color=RED,
    )
    low_battery_msg.anchor_point = (0, 0.5)
    low_battery_msg.anchored_position = (5, 30)
    g.append(low_battery_msg)
    show(display, g)


def seconds_until_wake(utc_time, tz_offset):
    """Seconds from now until the next WAKE_HOUR:00 local time."""
    local_now = time.localtime(utc_time + tz_offset)
    seconds_now = local_now.tm_hour * 3600 + local_now.tm_min * 60 + local_now.tm_sec
    seconds_target = WAKE_HOUR * 3600
    if seconds_now < seconds_target:
        return seconds_target - seconds_now
    return 24 * 3600 - seconds_now + seconds_target


def run(i2c):
    """Do one update cycle and return how many seconds to sleep afterwards."""
    battery_percent = adafruit_max1704x.MAX17048(i2c).cell_percent

    if battery_percent <= LOW_BATTERY_PERCENT:
        # Skip WiFi entirely to conserve power; the clock isn't synced, so
        # just sleep a full day rather than aiming for a time of day.
        print(f"Battery too low ({battery_percent:.1f}%), skipping WiFi")
        show_low_battery(init_display(), battery_percent)
        return LOW_BATTERY_SLEEP_SECONDS

    # Fetch first so the radio is off before the slower display work starts.
    forecast_data, utc_time, tz_offset = fetch_forecast()
    show_forecast(init_display(), forecast_data, tz_offset, battery_percent)
    return seconds_until_wake(utc_time, tz_offset)


try:
    sleep_seconds = run(board.I2C())
except Exception as e:  # Any failure must still end in deep sleep
    print("Update failed:", repr(e))
    sleep_seconds = ERROR_RETRY_SECONDS

# Belt and braces: make sure the radio is off however we got here.
wifi.radio.enabled = False

print("Sleeping for", sleep_seconds, "seconds")
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_seconds)  # type: ignore

# Turn off I2C power by setting it to input
i2c_power = digitalio.DigitalInOut(board.I2C_POWER)  # type: ignore
i2c_power.switch_to_input()
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
