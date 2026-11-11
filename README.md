# Tri-color E-Ink Weather Display

Written in CircuitPython.

Uses Feather ESP32-S2 deep sleep. Runs for weeks on a small battery.

## Images

The image sources are editable PNGs:

- `art/background.png`: the full-screen 296x128 background
- `icons/70px/` (today) and `icons/20px/` (forecast): one PNG per OpenWeatherMap
  icon code (`01-clear.png`, `10-rain.png`, ...)

Edit them with any image editor using only white, black, and pure red (`#FF0000`),
then rebuild:

    uv run tools/build_images.py

This writes `bmps/weather_bg.bmp`, `bmps/weather_icons_70px.bmp`, and
`bmps/weather_icons_20px.bmp` (4-bit indexed, fixed white/black/red palette). Off-palette pixels are snapped
to the nearest of the three colors, and transparency becomes white. Copy the
`bmps/` folder to the CIRCUITPY drive after rebuilding. Don't edit the BMPs
directly.

Credits: Code was liberally borrowed from https://github.com/adafruit/Adafruit_Learning_System_Guides/tree/main/MagTag/MagTag_Weather and then adjusted for my purposes.
