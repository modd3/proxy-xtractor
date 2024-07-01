#!/bin/bash

# Check if the script is run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "[!] This script must be run as root."
    exit 1
fi

# Check if the proxychains4.conf.default file exists
if [ ! -f /etc/proxychains4.conf.default ]; then
    echo "[!] /etc/proxychains4.conf.default not found."
    exit 1
fi

# Attempt to write to proxychains4.conf
if ! cp /etc/proxychains4.conf.default /etc/proxychains4.conf; then
    echo "[!] Failed to write to /etc/proxychains4.conf."
    exit 1
fi
echo '[+] wrote proxychains4.conf'
