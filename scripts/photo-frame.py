#!/usr/bin/env python3

import os
import sys
import time
import warnings
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

from PIL import Image, ImageOps
from inky.auto import auto

PHOTO_DIR = Path("/home/photo1/photos")
STATE_FILE = Path("/home/photo1/.photo-frame-index")
CONFIG_FILE = Path("/etc/photo-frame.conf")
MUXCTL = "/usr/local/sbin/muxctl"

TEST_INTERVAL_MINUTES = 10
DAILY_HOUR = 8
DAILY_MINUTE = 0
DAILY_SECOND = 0
SATURATION = 0.5
SUPPORTED = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def log(message):
    now = datetime.now().astimezone()
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S %Z')}] {message}", flush=True)

def mux_on():
    log("MUX ON: connecting PiSugar")
    subprocess.run([MUXCTL, "pisugar-on"], check=True)
    time.sleep(0.5)

def mux_off():
    log("MUX OFF: isolating PiSugar")
    subprocess.run([MUXCTL, "all-off"], check=True)
    time.sleep(0.5)

def pisugar(command, timeout=10):
    result = subprocess.run(
        ["nc", "-q", "0", "127.0.0.1", "8423"],
        input=command + "\n",
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    response = result.stdout.strip()
    log(f"PiSugar: {command} -> {response}")
    return response

def wait_for_pisugar(timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if "PiSugar 3" in pisugar("get model", 3):
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("PiSugar server unavailable")

def connect_pisugar():
    mux_on()
    subprocess.run(["systemctl", "start", "pisugar-server"], check=True)
    wait_for_pisugar()

def disconnect_pisugar():
    log("Stopping PiSugar server")
    subprocess.run(["systemctl", "stop", "pisugar-server"], check=False)
    time.sleep(0.5)
    mux_off()

def get_mode():
    mode = "TEST"
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text().splitlines():
            if line.strip().startswith("MODE="):
                mode = line.split("=", 1)[1].strip().upper()
    if mode not in {"TEST", "DAILY"}:
        raise RuntimeError(f"Invalid mode: {mode}")
    return mode

def schedule_next_wake():
    result = pisugar("rtc_pi2rtc")
    if "done" not in result.lower():
        raise RuntimeError("RTC synchronization failed")

    mode = get_mode()
    now = datetime.now().astimezone()

    if mode == "TEST":
        alarm = now + timedelta(minutes=TEST_INTERVAL_MINUTES)
        log("TEST MODE: scheduling wake for " + alarm.strftime("%H:%M:%S %Z"))
    else:
        alarm = now.replace(
            hour=DAILY_HOUR,
            minute=DAILY_MINUTE,
            second=DAILY_SECOND,
            microsecond=0,
        )
        if alarm <= now:
            alarm += timedelta(days=1)
        log("DAILY MODE: scheduling wake for " + alarm.strftime("%Y-%m-%d %H:%M:%S %Z"))

    response = pisugar(f"rtc_alarm_set {alarm.isoformat(timespec='seconds')} 127")
    if "done" not in response.lower():
        raise RuntimeError("Could not set PiSugar alarm: " + response)

    enabled = pisugar("get rtc_alarm_enabled")
    repeat = pisugar("get alarm_repeat")
    alarm_time = pisugar("get rtc_alarm_time")
    log(enabled)
    log(repeat)
    log(alarm_time)

    if "true" not in enabled.lower():
        raise RuntimeError("RTC alarm not enabled")
    if "127" not in repeat:
        raise RuntimeError("RTC repeat mask incorrect")

def get_images():
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    images = sorted(
        [p for p in PHOTO_DIR.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED],
        key=lambda p: p.name.lower(),
    )
    if not images:
        raise RuntimeError(f"No photos found in {PHOTO_DIR}")
    return images

def get_next_image():
    images = get_images()
    try:
        index = int(STATE_FILE.read_text().strip())
    except Exception:
        index = 0
    index %= len(images)
    return images, index, images[index]

def advance_image(images, index):
    next_index = (index + 1) % len(images)
    STATE_FILE.write_text(str(next_index) + "\n")
    try:
        os.chown(STATE_FILE, 1000, 1000)
    except PermissionError:
        pass

def refresh_inky(image_path):
    log("Detecting Inky")
    display = auto()
    log(f"Inky resolution: {display.resolution}")
    log(f"Loading: {image_path.name}")

    with Image.open(image_path) as original:
        image = original.convert("RGB")

    image = ImageOps.fit(
        image,
        display.resolution,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    display.set_image(image, saturation=SATURATION)
    log("Starting e-ink refresh")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        display.show()

    for warning in caught:
        text = str(warning.message)
        log("INKY WARNING: " + text)
        if "Timed out waiting for busy" in text:
            raise RuntimeError("Inky BUSY timeout")

    log("E-ink refresh completed")

def main():
    log("==============================")
    log("Photo frame cycle starting")
    log("==============================")
    log("Mode: " + get_mode())

    connect_pisugar()
    log(pisugar("get battery"))

    images, index, image_path = get_next_image()
    log(f"Displaying photo {index + 1}/{len(images)}: {image_path.name}")

    disconnect_pisugar()

    try:
        refresh_inky(image_path)
    except Exception as exc:
        log("DISPLAY FAILED: " + repr(exc))
        try:
            connect_pisugar()
        except Exception as restore_error:
            log("Could not restore PiSugar: " + repr(restore_error))
        sys.exit(1)

    advance_image(images, index)

    log("Photo changed successfully")
    log("Keeping Pi awake for 5 minutes for maintenance/access")
    time.sleep(300)

    connect_pisugar()
    schedule_next_wake()

    log("Enabling PiSugar soft poweroff")
    log(pisugar("set_soft_poweroff true"))
    log(pisugar("get battery"))
    log("Shutting Linux down")
    subprocess.run(["shutdown", "-h", "now"], check=False)

if __name__ == "__main__":
    main()
