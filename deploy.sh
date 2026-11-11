#!/bin/sh
# Copy code and images to the CIRCUITPY drive (macOS or Linux).
set -e
cd "$(dirname "$0")"

for d in /Volumes/CIRCUITPY "/media/$USER/CIRCUITPY" /media/tboldt/CIRCUITPY; do
    if [ -d "$d" ]; then
        DEST="$d"
        break
    fi
done
if [ -z "$DEST" ]; then
    echo "CIRCUITPY drive not found. Is the board awake and plugged in?" >&2
    exit 1
fi

mkdir -p "$DEST/bmps"

# CircuitPython auto-reloads when a file changes, which can interrupt a copy
# in progress, so verify each file and retry if needed.
copy() {
    for _ in 1 2 3; do
        cp -X "$1" "$DEST/$1" 2>/dev/null || cp "$1" "$DEST/$1"
        sync
        if cmp -s "$1" "$DEST/$1"; then
            echo "copied $1"
            return 0
        fi
        sleep 2
    done
    echo "failed to copy $1" >&2
    return 1
}

for f in bmps/*.bmp; do
    copy "$f"
done
# Copy code.py last so the reload it triggers sees the new images.
copy code.py
