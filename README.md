# Inky + PiSugar Automatic Photo Frame

Battery-powered automatic photo frame for a Pimoroni Inky Impression 13.3" using a Raspberry Pi, PiSugar 3, and a TCA9548A I2C mux.

The mux electrically isolates PiSugar from the I2C bus during Inky refreshes, preventing the BUSY timeout observed when PiSugar remains attached to the same bus.

## Hardware

- Raspberry Pi Zero / Zero 2 W-class board
- Pimoroni Inky Impression 13.3" (`inky_el133uf1`, 1600x1200)
- PiSugar 3
- TCA9548A I2C mux at `0x70`

### Wiring

Pi -> TCA9548A upstream:

- Pin 1 (3.3V) -> VCC
- Pin 6 (GND) -> GND
- Pin 3 (SDA) -> SDA
- Pin 5 (SCL) -> SCL

TCA9548A channel 0 -> PiSugar:

- SD0 -> PiSugar SDAT/SDA
- SC0 -> PiSugar SSCL/SCL

PiSugar master pins `MDAT/MSCL` are unused. PiSugar direct SDA/SCL pogo contacts should remain disconnected from the Pi.

Expected bus state:

- mux off: `0x50`, `0x70`
- mux channel 0 on: `0x50`, `0x57`, `0x68`, `0x70`

## Software behavior

Automatic RTC boot:

1. Pi boots near the programmed PiSugar RTC alarm.
2. `photo-frame-boot` recognizes it as an automatic wake.
3. PiSugar is connected through TCA9548A channel 0.
4. The next photo is selected from `/home/photo1/photos`.
5. PiSugar service is stopped and channel 0 is disconnected.
6. Inky refreshes while PiSugar is electrically isolated.
7. PiSugar is reconnected.
8. The next RTC wake is programmed.
9. PiSugar soft-poweroff is enabled.
10. Linux shuts down and PiSugar removes 5V.

Manual power-on:

- If boot is not within the configured RTC-wake window, the frame does nothing and stays awake for maintenance/SSH.

## Photo library

Photos live in:

```text
/home/photo1/photos
```

Supported formats:

- JPG / JPEG
- PNG
- BMP
- WEBP

Photos are displayed alphabetically by filename and loop forever.

### Upload from macOS

```bash
rsync -av --progress /path/to/photos/ photo1@photo1.local:/home/photo1/photos/
```

Example:

```bash
rsync -av --progress \
/Users/10x-remoteconnector/Desktop/JacobK214469/ \
photo1@photo1.local:/home/photo1/photos/
```

## Test mode

`/etc/photo-frame.conf`:

```text
MODE=TEST
```

The next wake is programmed 10 minutes after the cycle starts.

## Daily mode

Change to:

```text
MODE=DAILY
```

The frame wakes daily at 08:00 in the Pi's local timezone. Set the Pi to South Africa time with:

```bash
sudo timedatectl set-timezone Africa/Johannesburg
```

## Install

Run:

```bash
sudo ./install.sh
```

Then place photos in `/home/photo1/photos`.

## Useful commands

Check service:

```bash
systemctl status photo-frame.service
```

Check boot gate manually:

```bash
sudo /usr/local/sbin/photo-frame-boot
```

Run a frame cycle manually:

```bash
sudo /usr/local/bin/photo-frame.py
```

Inspect photo index:

```bash
cat /home/photo1/.photo-frame-index
```

Reset to first image:

```bash
echo 0 | sudo tee /home/photo1/.photo-frame-index
sudo chown photo1:photo1 /home/photo1/.photo-frame-index
```

Inspect previous automatic cycle:

```bash
journalctl -u photo-frame.service -b --no-pager
```
