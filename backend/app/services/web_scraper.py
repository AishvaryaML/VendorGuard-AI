import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )
}


def fetch_website(url: str):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        return text

    except requests.exceptions.RequestException as e:
        print(f"Error fetching website: {e}")
        return ""


def find_privacy_policy(url: str):
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    keywords = [
        "privacy",
        "privacy policy",
        "privacy notice",
        "data privacy",
        "legal"
    ]

    for link in soup.find_all("a", href=True):
        text = link.get_text(" ", strip=True).lower()
        href = link["href"].lower()

        if any(keyword in text or keyword in href for keyword in keywords):
            return urljoin(url, link["href"])

    return None