import pytest
import httpx
from app.services.crawler import (
    normalize_url,
    extract_domain,
    is_same_or_subdomain,
    classify_document_type,
    extract_clean_text,
    calculate_content_hash,
    discover_policy_links,
    VendorCrawlerService
)

SAMPLE_HOMEPAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Acme Cloud Services</title></head>
<body>
    <header><nav><a href="/">Home</a></nav></header>
    <main>
        <h1>Welcome to Acme</h1>
        <p>Enterprise SaaS solutions.</p>
    </main>
    <footer>
        <a href="/privacy-policy">Privacy Policy</a>
        <a href="https://trust.acme.com/security">Security & Trust Center</a>
        <a href="/terms-of-service">Terms of Service</a>
        <a href="https://google.com">External Partner</a>
    </footer>
</body>
</html>
"""

SAMPLE_PRIVACY_HTML_V1 = """
<!DOCTYPE html>
<html>
<head><title>Acme Privacy Policy</title></head>
<body>
    <h1>Acme Privacy Policy</h1>
    <p>We respect your privacy and process personal data in compliance with GDPR.</p>
    <p>Data retention is limited to 30 days post account termination.</p>
</body>
</html>
"""

SAMPLE_PRIVACY_HTML_V2 = """
<!DOCTYPE html>
<html>
<head><title>Acme Privacy Policy</title></head>
<body>
    <h1>Acme Privacy Policy</h1>
    <p>We respect your privacy and process personal data in compliance with GDPR.</p>
    <p>UPDATED: Data retention is extended to 90 days post account termination.</p>
</body>
</html>
"""


def test_url_normalization():
    assert normalize_url("acme.com") == "https://acme.com"
    assert normalize_url("http://ACME.com/") == "http://acme.com"
    assert normalize_url("  https://sub.acme.com/privacy/  ") == "https://sub.acme.com/privacy"
    assert normalize_url("https://acme.com/terms#section-1") == "https://acme.com/terms"

    with pytest.raises(ValueError):
        normalize_url("")


def test_domain_extraction_and_matching():
    assert extract_domain("https://acme.com/privacy") == "acme.com"
    assert is_same_or_subdomain("https://trust.acme.com/soc2", "acme.com") is True
    assert is_same_or_subdomain("https://external-malicious.com", "acme.com") is False


def test_document_classification():
    assert classify_document_type("Privacy Policy", "https://acme.com/privacy") == "Privacy Policy"
    assert classify_document_type("Terms of Service", "https://acme.com/terms") == "Terms of Service"
    assert classify_document_type("Trust & Security", "https://trust.acme.com/security") == "Security Center"
    assert classify_document_type("Random Link", "https://acme.com/about") is None


def test_text_extraction_and_hashing():
    clean_text, title = extract_clean_text(SAMPLE_PRIVACY_HTML_V1)
    assert title == "Acme Privacy Policy"
    assert "GDPR" in clean_text
    assert "<head>" not in clean_text
    assert "<h1>" not in clean_text

    hash1 = calculate_content_hash(clean_text)
    assert len(hash1) == 64 # SHA-256 length

    # Hash should be deterministic
    hash2 = calculate_content_hash(clean_text)
    assert hash1 == hash2


def test_policy_link_discovery():
    links = discover_policy_links(SAMPLE_HOMEPAGE_HTML, "https://acme.com", "acme.com")
    assert len(links) == 3
    doc_types = [link["document_type"] for link in links]
    assert "Privacy Policy" in doc_types
    assert "Security Center" in doc_types
    assert "Terms of Service" in doc_types

    # Ensure external domain google.com was excluded
    urls = [link["url"] for link in links]
    assert not any("google.com" in url for url in urls)


@pytest.mark.asyncio
async def test_crawler_service_with_mocked_http():
    def custom_handler(request: httpx.Request):
        url_str = str(request.url)
        if url_str == "https://acme.com":
            return httpx.Response(200, html=SAMPLE_HOMEPAGE_HTML)
        elif "privacy-policy" in url_str:
            return httpx.Response(200, html=SAMPLE_PRIVACY_HTML_V1)
        elif "security" in url_str:
            return httpx.Response(200, html="<html><title>Acme Security</title><body><p>SOC2 Certified and ISO27001 compliant security controls.</p></body></html>")
        elif "terms-of-service" in url_str:
            return httpx.Response(200, html="<html><title>Acme Terms</title><body><p>Standard terms of service and liability caps.</p></body></html>")
        return httpx.Response(404)

    transport = httpx.MockTransport(custom_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        crawler = VendorCrawlerService()
        data = await crawler.crawl_vendor("https://acme.com", client=client)

        assert data["vendor_domain"] == "acme.com"
        assert len(data["documents"]) >= 3
        types = [doc["document_type"] for doc in data["documents"]]
        assert "Privacy Policy" in types


@pytest.mark.asyncio
async def test_crawler_failure_handling():
    def failure_handler(request: httpx.Request):
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(failure_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        crawler = VendorCrawlerService()
        with pytest.raises(ValueError, match="Could not reach or fetch vendor website"):
            await crawler.crawl_vendor("https://failing-vendor.com", client=client)
