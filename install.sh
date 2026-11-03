#!/bin/bash
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "Run with sudo: sudo ./install.sh"
    exit 1
fi

USER_NAME="${SUDO_USER:-photo1}"
HOME_DIR="$(getent passwd "$USER_NAME" | cut -d: -f6)"
[ -n "$HOME_DIR" ] || HOME_DIR="/home/photo1"

apt update
apt install -y i2c-tools netcat-openbsd python3-pip python3-pil python3-numpy rsync
python3 -m pip install --break-system-packages inky==2.6.0

install -m 0755 scripts/muxctl /usr/local/sbin/muxctl
install -m 0755 scripts/photo-frame.py /usr/local/bin/photo-frame.py
install -m 0755 scripts/photo-frame-boot /usr/local/sbin/photo-frame-boot

install -m 0644 systemd/pisugar-mux.service /etc/systemd/system/pisugar-mux.service
install -m 0644 systemd/photo-frame.service /etc/systemd/system/photo-frame.service

mkdir -p /etc/systemd/system/pisugar-server.service.d
install -m 0644 systemd/pisugar-server-mux.conf /etc/systemd/system/pisugar-server.service.d/mux.conf

if [ ! -f /etc/photo-frame.conf ]; then
    install -m 0644 config/photo-frame.conf.example /etc/photo-frame.conf
fi

mkdir -p "$HOME_DIR/photos"
touch "$HOME_DIR/.photo-frame-index"
if [ ! -s "$HOME_DIR/.photo-frame-index" ]; then
    echo 0 > "$HOME_DIR/.photo-frame-index"
fi
chown -R "$USER_NAME":"$USER_NAME" "$HOME_DIR/photos" "$HOME_DIR/.photo-frame-index"

systemctl daemon-reload
systemctl enable pisugar-mux.service
systemctl enable pisugar-server.service
systemctl enable photo-frame.service

echo
echo "Installed."
echo "Ensure I2C and SPI are enabled in raspi-config."
echo "Set timezone if needed: timedatectl set-timezone Africa/Johannesburg"
echo "Upload photos to: $HOME_DIR/photos"
echo "Config: /etc/photo-frame.conf"
