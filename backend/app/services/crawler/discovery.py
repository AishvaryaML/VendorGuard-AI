import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class VendorDiscoveryService:

    def discover(self, vendor_url: str):

        discovered_pages = {
            "homepage": vendor_url,
            "privacy": None,
            "terms": None,
            "security": None,
            "trust": None,
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            )
        }

        try:
            response = requests.get(
                vendor_url,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            links = soup.find_all("a", href=True)

            print(f"Found {len(links)} links")

            for link in links:

                text = link.get_text(" ", strip=True).lower()

                # Keep original href
                href = link["href"]

                # Lowercase copy only for keyword matching
                href_lower = href.lower()

                full_url = urljoin(vendor_url, href)

                if discovered_pages["privacy"] is None:
                    if "privacy" in text or "privacy" in href_lower:
                        discovered_pages["privacy"] = full_url

                if discovered_pages["terms"] is None:
                    if "terms" in text or "terms" in href_lower:
                        discovered_pages["terms"] = full_url

                if discovered_pages["security"] is None:
                    if "security" in text or "security" in href_lower:
                        discovered_pages["security"] = full_url

                if discovered_pages["trust"] is None:
                    if "trust" in text or "trust" in href_lower:
                        discovered_pages["trust"] = full_url

            print("\nDiscovered Pages:")
            print(discovered_pages)

            return discovered_pages

        except requests.exceptions.RequestException as e:
            print(f"Discovery Error: {e}")

            return {
                "homepage": vendor_url,
                "privacy": None,
                "terms": None,
                "security": None,
                "trust": None,
            }