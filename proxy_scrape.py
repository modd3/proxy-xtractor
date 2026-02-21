import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests
from bs4 import BeautifulSoup

# Constants for output and validation
OUTPUT_FILE = Path("socks5_proxies.txt")
MAX_RESULTS = 200
CHECK_TIMEOUT_SECONDS = 5.0  # Increased for functional test
VALIDATION_WORKERS = 40
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

@dataclass(frozen=True)
class ProxyEntry:
    proxy_type: str
    ip: str
    port: str
    source: str

def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    })
    return session

def fetch_freeproxy_world(session: requests.Session, pages: int = 5) -> list[ProxyEntry]:
    base_url = "https://www.freeproxy.world/"
    query_params = {"type": "socks5", "anonymity": "4", "speed": "2000"}
    proxies: list[ProxyEntry] = []
    seen: set[tuple[str, str]] = set()

    for page_num in range(1, pages + 1):
        try:
            response = session.get(base_url, params={**query_params, "page": str(page_num)}, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for row in soup.select("table tbody tr"):
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
                ip_match = next((IP_PATTERN.search(cell) for cell in cells if IP_PATTERN.search(cell)), None)
                port = next((cell for cell in cells if cell.isdigit() and 1 <= len(cell) <= 5), None)
                if ip_match and port:
                    ip = ip_match.group(0)
                    if (ip, port) not in seen:
                        seen.add((ip, port))
                        proxies.append(ProxyEntry("SOCKS5", ip, port, "freeproxy.world"))
        except Exception as e:
            print(f"[!] Error scraping page {page_num}: {e}")
    return proxies

def fetch_proxyscrape_api(session: requests.Session) -> list[ProxyEntry]:
    url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=2000&country=all"
    try:
        response = session.get(url, timeout=20)
        proxies = []
        for line in response.text.splitlines():
            if ":" in line:
                ip, port = line.strip().rsplit(":", 1)
                if IP_PATTERN.fullmatch(ip) and port.isdigit():
                    proxies.append(ProxyEntry("SOCKS5", ip, port, "proxyscrape"))
        return proxies
    except Exception:
        return []

def check_proxy_functional(entry: ProxyEntry, timeout: float) -> bool:
    """Verifies the proxy can actually reach the internet."""
    proxy_url = f"socks5://{entry.ip}:{entry.port}"
    proxies = {"http": proxy_url, "https": proxy_url}
    try:
        # Use Google's connectivity check for speed and reliability
        response = requests.get("http://connectivitycheck.gstatic.com/generate_204", 
                                proxies=proxies, timeout=timeout)
        return response.status_code == 204
    except:
        return False

def validate_candidates(candidates: list[ProxyEntry]) -> list[ProxyEntry]:
    validated: list[ProxyEntry] = []
    with ThreadPoolExecutor(max_workers=VALIDATION_WORKERS) as executor:
        future_to_proxy = {executor.submit(check_proxy_functional, p, CHECK_TIMEOUT_SECONDS): p for p in candidates}
        for future in as_completed(future_to_proxy):
            if future.result():
                validated.append(future_to_proxy[future])
    return validated

def main():
    session = build_session()
    print("[*] Collecting candidates...")
    candidates = fetch_freeproxy_world(session) + fetch_proxyscrape_api(session)
    print(f"[*] Found {len(candidates)} candidates. Validating...")
    
    valid_proxies = validate_candidates(candidates)
    print(f"[*] Found {len(valid_proxies)} working proxies.")
    
    with OUTPUT_FILE.open("w") as f:
        for p in valid_proxies[:MAX_RESULTS]:
            f.write(f"{p.proxy_type.lower()} {p.ip} {p.port}\n")
    print(f"[+] Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
