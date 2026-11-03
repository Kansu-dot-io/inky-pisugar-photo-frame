# Verification checklist

## I2C mux

Channel 0 on:

```bash
sudo /usr/local/sbin/muxctl pisugar-on
i2cdetect -y 1
```

Expected devices: `0x50`, `0x57`, `0x68`, `0x70`.

Channel 0 off:

```bash
sudo /usr/local/sbin/muxctl all-off
i2cdetect -y 1
```

Expected devices: `0x50`, `0x70`.

## PiSugar

```bash
echo "get model" | nc -q 0 127.0.0.1 8423
echo "get battery" | nc -q 0 127.0.0.1 8423
```

## Inky

PiSugar should be isolated before refresh.

## Manual boot gate

```bash
sudo /usr/local/sbin/photo-frame-boot
```

If the current RTC time is more than 180 seconds from the stored alarm, it should print that manual power-on was detected and leave the Pi running.
