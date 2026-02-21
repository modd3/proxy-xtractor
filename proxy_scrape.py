import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.freeproxy.world/"
QUERY_PARAMS = {
    "type": "socks5",
    "anonymity": "4",
    "country": "",
    "speed": "2000",
    "port": "",
}
MAX_PAGES = 10
OUTPUT_FILE = Path("socks5_proxies.txt")
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


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
            "Referer": "https://www.freeproxy.world/",
            "Connection": "keep-alive",
        }
    )
    return session


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


def extract_proxies(html_text: str) -> list[tuple[str, str, str]]:
    soup = BeautifulSoup(html_text, "html.parser")

    proxies: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()

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

        proxy_type = next((cell.upper() for cell in cells if "SOCKS5" in cell.upper()), "SOCKS5")

        proxy = (proxy_type, ip, port)
        if proxy not in seen:
            seen.add(proxy)
            proxies.append(proxy)

    return proxies


def fetch_page(session: requests.Session, page_num: int) -> str | None:
    params = {**QUERY_PARAMS, "page": str(page_num)}

    try:
        response = session.get(BASE_URL, params=params, timeout=20)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        print(f"[!] Failed to fetch page {page_num}: {exc}")
        return None


def main() -> None:
    session = build_session()

    all_proxies: list[tuple[str, str, str]] = []
    for page_num in range(1, MAX_PAGES + 1):
        html_text = fetch_page(session, page_num)
        if html_text is None:
            continue

        if is_challenge_page(html_text):
            print(
                f"[!] Blocked by anti-bot challenge on page {page_num}. "
                "Open the URL in a browser, pass the checkbox/captcha, "
                "then rerun from a trusted IP/VPN."
            )
            break

        proxies = extract_proxies(html_text)
        if not proxies:
            print(f"[!] No SOCKS5 proxies found on page {page_num}")
            continue

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
