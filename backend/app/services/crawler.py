import re
import hashlib
import logging
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup

from app.core.config import settings

logger = logging.getLogger("vendorguard.crawler")

# Keyword signals for document classification
DOCUMENT_CLASSIFICATION_RULES = {
    "Privacy Policy": {
        "keywords": ["privacy", "gdpr", "ccpa", "privacy-policy", "data-privacy", "privacy-notice"],
        "weight": 10
    },
    "Terms of Service": {
        "keywords": ["terms", "tos", "terms-of-service", "terms-and-conditions", "service-agreement", "eula", "user-agreement"],
        "weight": 9
    },
    "Security Center": {
        "keywords": ["security", "trust", "security-center", "trust-center", "soc2", "iso27001", "security-posture"],
        "weight": 8
    },
    "Data Processing Addendum": {
        "keywords": ["dpa", "data-processing", "subprocessors", "sub-processors", "data-transfer-agreement"],
        "weight": 7
    },
    "Compliance Doc": {
        "keywords": ["compliance", "certifications", "regulatory", "audit-report", "soc-reports", "hipaa"],
        "weight": 6
    }
}


def normalize_url(url: str) -> str:
    """
    Normalizes a given URL string safely:
    - Strips whitespace
    - Ensures scheme (default https://)
    - Lowercases domain
    - Removes fragments and trailing slashes
    """
    if not url:
        raise ValueError("URL string cannot be empty.")
    
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"Invalid URL format: '{url}' missing domain host.")

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    
    # Remove default ports if present
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    path = parsed.path
    if path == "/":
        path = ""
    elif path.endswith("/"):
        path = path[:-1]

    normalized = f"{scheme}://{netloc}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    
    return normalized


def extract_domain(url: str) -> str:
    """Extracts the registered netloc/domain from a URL."""
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    return parsed.netloc


def is_same_or_subdomain(target_url: str, base_domain: str) -> bool:
    """
    Checks if a target URL belongs to the base domain or one of its subdomains
    (e.g., trust.slack.com matches base_domain slack.com).
    """
    try:
        target_netloc = extract_domain(target_url)
    except ValueError:
        return False

    base_domain = base_domain.lower()
    if target_netloc == base_domain or target_netloc.endswith("." + base_domain):
        return True
    return False


def classify_document_type(link_text: str, link_url: str) -> Optional[str]:
    """
    Classifies a link into a document type based on anchor text and URL pattern match.
    """
    combined_signal = f"{link_text.lower()} {link_url.lower()}"
    best_match = None
    best_score = 0

    for doc_type, rule in DOCUMENT_CLASSIFICATION_RULES.items():
        score = 0
        for keyword in rule["keywords"]:
            if keyword in combined_signal:
                score += rule["weight"]
                # Give bonus if keyword appears in URL path specifically
                if keyword in link_url.lower():
                    score += 5
        if score > best_score:
            best_score = score
            best_match = doc_type

    return best_match if best_score >= 6 else None


def extract_clean_text(html_content: str) -> Tuple[str, str]:
    """
    Strips scripts, styles, navigation, boilerplate tags from HTML
    and extracts clean plain text + document title.
    """
    if not html_content or not html_content.strip():
        return "", "Untitled Document"

    soup = BeautifulSoup(html_content, "html.parser")

    # Extract title before removing tags
    title_tag = soup.find("title")
    title = title_tag.get_text().strip() if title_tag else "Untitled Document"

    # Remove unwanted non-content elements
    for element in soup(["script", "style", "noscript", "nav", "header", "footer", "svg", "iframe", "form", "button"]):
        element.decompose()

    text = soup.get_text(separator="\n")

    # Clean up whitespace line by line
    lines = [line.strip() for line in text.splitlines()]
    clean_lines = [line for line in lines if line]
    clean_text = "\n".join(clean_lines)

    return clean_text, title


def calculate_content_hash(text: str) -> str:
    """Calculates SHA-256 hex digest of normalized clean text."""
    normalized_text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


def discover_policy_links(html_content: str, base_url: str, base_domain: str) -> List[Dict[str, str]]:
    """
    Parses HTML content to discover candidate policy document links.
    Returns deduplicated list of dicts with keys: url, title, document_type.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    discovered_links: List[Dict[str, str]] = []
    seen_urls = set()
    seen_types = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        link_text = a_tag.get_text().strip()

        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue

        try:
            full_url = normalize_url(urljoin(base_url, href))
        except ValueError:
            continue

        if not is_same_or_subdomain(full_url, base_domain):
            continue

        doc_type = classify_document_type(link_text, full_url)
        if not doc_type:
            continue

        # Deduplicate by (type, url)
        dedup_key = (doc_type, full_url)
        if full_url in seen_urls or dedup_key in seen_types:
            continue

        seen_urls.add(full_url)
        seen_types.add(dedup_key)

        title = link_text if link_text and len(link_text) <= 100 else doc_type
        discovered_links.append({
            "url": full_url,
            "title": title,
            "document_type": doc_type
        })

    return discovered_links


class VendorCrawlerService:
    """
    Async Crawler service to discover, fetch, and extract vendor legal and security policy documents.
    """

    def __init__(self, timeout_seconds: int = 20, user_agent: Optional[str] = None):
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent or settings.CRAWLER_USER_AGENT

    async def fetch_page(self, client: httpx.AsyncClient, url: str) -> Optional[str]:
        """Fetches a single page with error handling and custom user agent."""
        try:
            headers = {"User-Agent": self.user_agent}
            response = await client.get(
                url,
                headers=headers,
                timeout=self.timeout_seconds,
                follow_redirects=True
            )
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Failed to fetch '{url}' — HTTP {response.status_code}")
                return None
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching '{url}' after {self.timeout_seconds}s")
            return None
        except Exception as e:
            logger.error(f"Error fetching '{url}': {str(e)}")
            return None

    async def crawl_vendor(
        self,
        vendor_url: str,
        client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        """
        Main crawler entrypoint:
        1. Normalizes vendor URL & domain.
        2. Fetches homepage.
        3. Discovers policy links.
        4. Fetches and extracts content for each discovered policy.
        5. Returns structured document dictionary list.
        """
        normalized_start_url = normalize_url(vendor_url)
        base_domain = extract_domain(normalized_start_url)

        should_close_client = False
        if client is None:
            client = httpx.AsyncClient(verify=True)
            should_close_client = True

        try:
            homepage_html = await self.fetch_page(client, normalized_start_url)
            if not homepage_html:
                raise ValueError(f"Could not reach or fetch vendor website at {normalized_start_url}")

            # Discover policy links from homepage
            policy_links = discover_policy_links(homepage_html, normalized_start_url, base_domain)

            # If no policy links discovered from homepage links, add fallback URL guesses
            if not policy_links:
                fallback_paths = [
                    ("/privacy", "Privacy Policy"),
                    ("/terms", "Terms of Service"),
                    ("/security", "Security Center"),
                ]
                for path, doc_type in fallback_paths:
                    fallback_url = normalize_url(urljoin(normalized_start_url, path))
                    policy_links.append({
                        "url": fallback_url,
                        "title": doc_type,
                        "document_type": doc_type
                    })

            results = []
            for link_info in policy_links:
                doc_html = await self.fetch_page(client, link_info["url"])
                if not doc_html:
                    continue

                clean_text, parsed_title = extract_clean_text(doc_html)
                if not clean_text or len(clean_text) < 50:
                    continue

                doc_title = link_info["title"] if link_info["title"] != link_info["document_type"] else parsed_title
                content_hash = calculate_content_hash(clean_text)

                results.append({
                    "document_type": link_info["document_type"],
                    "title": doc_title,
                    "url": link_info["url"],
                    "clean_text": clean_text,
                    "content_hash": content_hash
                })

            return {
                "vendor_domain": base_domain,
                "normalized_start_url": normalized_start_url,
                "documents": results
            }

        finally:
            if should_close_client:
                await client.aclose()
