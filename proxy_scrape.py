from bs4 import BeautifulSoup
import requests

def main():
    base_url = "https://www.freeproxy.world/?type=socks5&anonymity=4&country=&speed=&port=&page={}"

    # Iterate over 5 pages
    for page_num in range(1, 6):
        url = base_url.format(page_num)

        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"[!] Failed to fetch page {page_num}: {e}")
            continue

        try:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all <td> elements with class 'show-ip-div'
            ip_elements = soup.find_all('td', class_='show-ip-div')

            # Find all <td> elements
            port_td_elements = soup.find_all('td')

            # Extracting text from each element and adding to list
            ip_list = [ip.get_text(strip=True) for ip in ip_elements]

            # Check if they contain a child <a> element with 'href' containing the string 'port' or 'type'
            port_list = []
            type_list = []
            for td in port_td_elements:
                a_element = td.find('a', href=True)
                if a_element:
                    if 'port' in a_element['href']:
                        port_list.append(a_element.get_text(strip=True))
                    if 'type' in a_element['href']:
                        type_list.append(a_element.get_text(strip=True))

            if not ip_list or not port_list or not type_list:
                print(f"[!] No proxies found on page {page_num}")
                continue

            # Write to a text file in the format type ip port in every line
            with open('socks5_proxies.txt', 'a') as txt_file:
                for ip, port, typ in zip(ip_list, port_list, type_list):
                    txt_file.write(f"{typ} {ip} {port}\n")

        except Exception as e:
            print(f"[!] Error processing page {page_num}: {e}")
            continue

if __name__ == "__main__":
    main()
