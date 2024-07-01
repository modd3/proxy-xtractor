# PROXY-XTRACTOR                                                                   


## For use with proxychains4

This script automates the setup of proxy configurations using Proxychains-ng by fetching fresh SOCKS5 proxies from https://freeproxy.world/
The proxies are added to the proxychains4.conf, tor proxy is disabled.


## Installation

Clone the repository from GitHub:

```bash
git clone https://github.com/your_username/proxy-xtractor.git
cd proxy-xtractor
```

## Usage

Ensure the script is executable:

```bash
chmod +x add_prox2conf.sh
chmod +x clear_conf.sh
```

### Setting up Proxychains

Run the main script with root privileges to set up Proxychains:

```bash
sudo ./add_prox2conf.sh
```

### Clearing Proxychains Configuration

To clear the `proxychains4.conf` file, use the `clear_conf.sh` script:

```bash
./clear_conf.sh
```

## Description

The main script (`add_prox2conf.sh`) performs the following tasks:
- Checks if `proxychains4.conf.default` exists; if not, creates it based on existing configurations (`proxychains4.conf` or `proxychains.conf`).
- Fetches fresh SOCKS5 proxies from https://freeproxy.world using `python proxy_scrape.py`.
- Appends the top 20 SOCKS5 proxies to `proxychains4.conf`.
- Displays the last 30 lines of `proxychains4.conf` for verification.

The `clear_conf.sh` script:
- Removes all content from `proxychains4.conf`, effectively resetting it.

If neither `proxychains4.conf` nor `proxychains.conf` is found, the main script exits with an error message prompting the installation of Proxychains-ng.

### Requirements

- Python 3.x
- Requests library (`pip install requests`)
- BeautifulSoup4 library (`pip install beautifulsoup4`)

## Contributing

Contributions are welcome! Please submit issues for any bugs or feature requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

