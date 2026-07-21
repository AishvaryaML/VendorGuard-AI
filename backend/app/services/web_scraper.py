import requests
from bs4 import BeautifulSoup


def fetch_website(url: str):
    response = requests.get(url)

    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text(separator=" ", strip=True)

    return text
from urllib.parse import urljoin

def find_privacy_policy(url: str):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    links = soup.find_all("a")

    for link in links:
        text = link.get_text(strip=True)

        if "privacy" in text.lower():
            href = link.get("href")

            if href:
                return urljoin(url, href)

    return None