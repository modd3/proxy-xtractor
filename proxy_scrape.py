import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = Path("socks5_proxies.txt")
MAX_RESULTS = 200
CHECK_TIMEOUT_SECONDS = 2.5
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
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
    )
    return session


def fetch_freeproxy_world(session: requests.Session, pages: int = 10) -> list[ProxyEntry]:
    base_url = "https://www.freeproxy.world/"
    query_params = {
        "type": "socks5",
        "anonymity": "4",
        "country": "",
        "speed": "2000",
        "port": "",
    }

    def is_challenge_page(html_text: str) -> bool:
        markers = (
            "captcha",
            "verify you are human",
            "cf-challenge",
            "cloudflare",
            "hcaptcha",
            "g-recaptcha",
        )
        lowered = html_text.lower()
        return any(marker in lowered for marker in markers)

    proxies: list[ProxyEntry] = []
    seen: set[tuple[str, str]] = set()

    for page_num in range(1, pages + 1):
        try:
            response = session.get(base_url, params={**query_params, "page": str(page_num)}, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[!] freeproxy.world page {page_num} failed: {exc}")
            continue

        if is_challenge_page(response.text):
            print("[!] freeproxy.world presented a captcha/challenge. Skipping this source for now.")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        page_count = 0
        for row in soup.select("table tbody tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
            if len(cells) < 2:
                continue

            ip_match = next((IP_PATTERN.search(cell) for cell in cells if IP_PATTERN.search(cell)), None)
            if not ip_match:
                continue
            ip = ip_match.group(0)

            port = next((cell for cell in cells if cell.isdigit() and 1 <= len(cell) <= 5), None)
            if not port:
                continue

            key = (ip, port)
            if key in seen:
                continue
            seen.add(key)
            proxies.append(ProxyEntry("SOCKS5", ip, port, "freeproxy.world"))
            page_count += 1

        print(f"[*] freeproxy.world page {page_num}: {page_count} candidate proxies")

    return proxies


def fetch_proxyscrape_api(session: requests.Session) -> list[ProxyEntry]:
    url = "https://api.proxyscrape.com/v2/"
    params = {
        "request": "displayproxies",
        "protocol": "socks5",
        "timeout": "2000",
        "country": "all",
        "ssl": "all",
        "anonymity": "all",
    }
    try:
        response = session.get(url, params=params, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[!] proxyscrape API failed: {exc}")
        return []

    proxies: list[ProxyEntry] = []
    for line in response.text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        ip, port = line.rsplit(":", 1)
        if IP_PATTERN.fullmatch(ip) and port.isdigit():
            proxies.append(ProxyEntry("SOCKS5", ip, port, "proxyscrape"))

    print(f"[*] proxyscrape: {len(proxies)} candidate proxies")
    return proxies


def fetch_proxy_list_download(session: requests.Session) -> list[ProxyEntry]:
    url = "https://www.proxy-list.download/api/v1/get"
    params = {"type": "socks5"}
    try:
        response = session.get(url, params=params, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[!] proxy-list.download API failed: {exc}")
        return []

    proxies: list[ProxyEntry] = []
    for line in response.text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        ip, port = line.rsplit(":", 1)
        if IP_PATTERN.fullmatch(ip) and port.isdigit():
            proxies.append(ProxyEntry("SOCKS5", ip, port, "proxy-list.download"))

    print(f"[*] proxy-list.download: {len(proxies)} candidate proxies")
    return proxies


def dedupe_candidates(candidates: list[ProxyEntry]) -> list[ProxyEntry]:
    deduped: list[ProxyEntry] = []
    seen: set[tuple[str, str]] = set()
    for entry in candidates:
        key = (entry.ip, entry.port)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def check_proxy_tcp(ip: str, port: str, timeout: float) -> bool:
    try:
        with socket.create_connection((ip, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def validate_candidates(candidates: list[ProxyEntry]) -> list[ProxyEntry]:
    if not candidates:
        return []

    validated: list[ProxyEntry] = []
    with ThreadPoolExecutor(max_workers=VALIDATION_WORKERS) as executor:
        future_map = {
            executor.submit(check_proxy_tcp, entry.ip, entry.port, CHECK_TIMEOUT_SECONDS): entry
            for entry in candidates
        }
        for future in as_completed(future_map):
            entry = future_map[future]
            try:
                if future.result():
                    validated.append(entry)
            except Exception:
                continue

    return validated


def collect_candidates(session: requests.Session) -> list[ProxyEntry]:
    fetchers: list[Callable[[requests.Session], list[ProxyEntry]]] = [
        fetch_freeproxy_world,
        fetch_proxyscrape_api,
        fetch_proxy_list_download,
    ]

    candidates: list[ProxyEntry] = []
    for fetcher in fetchers:
        fetched = fetcher(session)
        candidates.extend(fetched)

    return dedupe_candidates(candidates)


def write_output(valid_proxies: list[ProxyEntry]) -> None:
    with OUTPUT_FILE.open("w", encoding="utf-8") as txt_file:
        for proxy in valid_proxies[:MAX_RESULTS]:
            txt_file.write(f"{proxy.proxy_type} {proxy.ip} {proxy.port}\n")


def main() -> None:
    session = build_session()
    candidates = collect_candidates(session)
    print(f"[*] Total unique candidates collected: {len(candidates)}")

    if not candidates:
        print("[!] No proxies collected from available sources.")
        return

    valid_proxies = validate_candidates(candidates)
    print(f"[*] Reachable proxies after TCP check: {len(valid_proxies)}")

    if not valid_proxies:
        print("[!] No reachable proxies found. Output file was not modified.")
        return

    write_output(valid_proxies)
    print(f"[+] Wrote {min(len(valid_proxies), MAX_RESULTS)} proxies to {OUTPUT_FILE}")


        print(f"[+] Page {page_num}: extracted {len(proxies)} SOCKS5 proxies")
        all_proxies.extend(proxies)

    unique_proxies: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for proxy in all_proxies:
        if proxy not in seen:
            seen.add(proxy)
            unique_proxies.append(proxy)

    if not unique_proxies:
        print("[!] No proxies extracted. Output file was not modified.")
        return

    with OUTPUT_FILE.open("w", encoding="utf-8") as txt_file:
        for proxy_type, ip, port in unique_proxies:
            txt_file.write(f"{proxy_type} {ip} {port}\n")

    print(f"[+] Wrote {len(unique_proxies)} unique proxies to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
