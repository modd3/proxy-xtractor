#!/bin/bash

display_banner() {
	cat << "EOF"



 ___  ____ ____ _ _ _ _    _ _ ___ ____ ____ ____ ___ ____ ____
 |--' |--< [__] _X_  Y  -- _X_  |  |--< |--| |___  |  [__] |--<




EOF

}

# Check if the script is run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "[!] This script must be run as root."
    exit 1
fi

display_banner

# Set default paths
PROXYCHAINS4_CONF="/etc/proxychains4.conf"
PROXYCHAINS4_CONF_DEFAULT="/etc/proxychains4.conf.default"
PROXYCHAINS_CONF="/etc/proxychains.conf"
DEFAULT_CREATED=false

# Check if proxychains4.conf.default exists
if [ ! -f "$PROXYCHAINS4_CONF_DEFAULT" ]; then
    # If proxychains4.conf.default doesn't exist, create it
    if [ -f "$PROXYCHAINS4_CONF" ]; then
        cp "$PROXYCHAINS4_CONF" "$PROXYCHAINS4_CONF_DEFAULT"
        echo "[+] Created $PROXYCHAINS4_CONF_DEFAULT from $PROXYCHAINS4_CONF"
        DEFAULT_CREATED=true
    elif [ -f "$PROXYCHAINS_CONF" ]; then
        cp "$PROXYCHAINS_CONF" "$PROXYCHAINS4_CONF_DEFAULT"
        echo "[+] Created $PROXYCHAINS4_CONF_DEFAULT from $PROXYCHAINS_CONF"
        PROXYCHAINS4_CONF="$PROXYCHAINS_CONF"
        DEFAULT_CREATED=true
    else
        echo "[!] Neither $PROXYCHAINS4_CONF nor $PROXYCHAINS_CONF found. You must install proxychains-ng to use this script."
        exit 1
    fi
fi

# Only write to proxychains4.conf if default was not created in this run
if [ "$DEFAULT_CREATED" = false ]; then
    if ! cp "$PROXYCHAINS4_CONF_DEFAULT" "$PROXYCHAINS4_CONF"; then
        echo "[!] Failed to write to $PROXYCHAINS4_CONF."
        exit 1
    fi
    echo "[+] Wrote $PROXYCHAINS4_CONF"
else
    echo "[*] Skipped writing to $PROXYCHAINS4_CONF as $PROXYCHAINS4_CONF_DEFAULT was just created"
fi

echo '[*] Getting fresh socks5 proxies...'
if ! python proxy_scrape.py; then
    echo "[!] Failed to run proxy_scrape.py."
    exit 1
fi
echo '[+] Added new proxies...'

# Check if socks5_proxies.txt file exists
if [ ! -f socks5_proxies.txt ]; then
    echo "[!] socks5_proxies.txt not found."
    exit 1
fi

# Attempt to add proxies to proxychains4.conf
if ! head -n 20 socks5_proxies.txt >> "$PROXYCHAINS4_CONF"; then
    echo "[!] Failed to add socks5 proxies to $PROXYCHAINS4_CONF."
    exit 1
fi
echo '[+] Added socks5 proxies to proxychains4.conf'

# Check if the final proxychains4.conf exists and read it
if ! tail -n 30 "$PROXYCHAINS4_CONF"; then
    echo "[!] Failed to read $PROXYCHAINS4_CONF."
    exit 1
fi

echo '[*] Done...'
