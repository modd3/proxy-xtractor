#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"


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
# Detect config file version (v3 vs v4)
if [ -f "/etc/proxychains.conf" ]; then
    CONF="/etc/proxychains.conf"
elif [ -f "/etc/proxychains4.conf" ]; then
    CONF="/etc/proxychains4.conf"
else
    echo "[!] No proxychains config found."
    exit 1
fi

BACKUP="${CONF}.default"

# Create initial backup if missing
if [ ! -f "$BACKUP" ]; then
    cp "$CONF" "$BACKUP"
    echo "[+] Backup created: $BACKUP"
fi

# Restore clean config and optimize settings
cp "$BACKUP" "$CONF"
sed -i 's/^strict_chain/# strict_chain/' "$CONF"
sed -i 's/^#dynamic_chain/dynamic_chain/' "$CONF"
echo "[*] Configuration optimized for dynamic_chain."

# Run scraper
echo "[*] Scraping and validating fresh proxies..."
python3 proxy_scrape.py

if [ -f "socks5_proxies.txt" ]; then
    head -n 25 socks5_proxies.txt >> "$CONF"
    echo "[+] Added 25 verified proxies to $CONF"
else
    echo "[!] Scraper failed."
    exit 1
fi

echo "[*] Done. Run 'proxychains3 curl google.com' to test."
