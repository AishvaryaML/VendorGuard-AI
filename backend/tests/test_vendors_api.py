import uuid
import pytest
import httpx
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import AsyncSessionLocal, init_db_connection
from app.models.vendor import Vendor
from app.models.document import Document, PolicyVersion
from app.models.alert import Alert
from app.services.crawler import VendorCrawlerService
from app.services.vendor_service import sync_vendor_crawled_documents

SAMPLE_MOCK_HOMEPAGE = """
<html>
<head><title>Stripe Payments</title></head>
<body>
  <footer>
    <a href="/privacy">Privacy Policy</a>
    <a href="/terms">Terms of Service</a>
  </footer>
</body>
</html>
"""

SAMPLE_MOCK_PRIVACY_V1 = "<html><head><title>Stripe Privacy</title></head><body><p>We take privacy seriously and encrypt all stored data.</p></body></html>"
SAMPLE_MOCK_PRIVACY_V2 = "<html><head><title>Stripe Privacy</title></head><body><p>We take privacy seriously and encrypt all stored data with AES-256 GCM.</p></body></html>"
SAMPLE_MOCK_TERMS = "<html><head><title>Stripe Terms</title></head><body><p>Standard terms of service for Stripe merchant accounts.</p></body></html>"


@pytest.mark.asyncio
async def test_vendor_api_create_and_versioning_flow():
    await init_db_connection()

    unique_domain = f"stripe-{uuid.uuid4().hex[:8]}.com"
    target_url = f"https://{unique_domain}"

    def mock_http_handler(request: httpx.Request):
        url_str = str(request.url)
        if url_str == target_url:
            return httpx.Response(200, html=SAMPLE_MOCK_HOMEPAGE)
        elif "/privacy" in url_str:
            return httpx.Response(200, html=SAMPLE_MOCK_PRIVACY_V1)
        elif "/terms" in url_str:
            return httpx.Response(200, html=SAMPLE_MOCK_TERMS)
        return httpx.Response(404)

    # Patch crawler to use MockTransport during API call
    original_crawl = VendorCrawlerService.crawl_vendor

    async def mocked_crawl_vendor(self, vendor_url, client=None):
        mock_transport = httpx.MockTransport(mock_http_handler)
        async with httpx.AsyncClient(transport=mock_transport) as mock_client:
            return await original_crawl(self, vendor_url, client=mock_client)

    VendorCrawlerService.crawl_vendor = mocked_crawl_vendor

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Create Vendor via POST /api/v1/vendors
            response = await ac.post("/api/v1/vendors/", json={
                "name": "Stripe Payments",
                "domain": unique_domain,
                "website_url": target_url,
                "industry": "FinTech / Payments"
            })
            assert response.status_code == 201
            vendor_data = response.json()
            vendor_id = vendor_data["id"]

            assert vendor_data["domain"] == unique_domain
            assert vendor_data["status"] == "Active"

            # 2. Get Discovered Documents via GET /api/v1/vendors/{id}/documents
            doc_res = await ac.get(f"/api/v1/vendors/{vendor_id}/documents")
            assert doc_res.status_code == 200
            docs = doc_res.json()
            assert len(docs) >= 2

            privacy_doc = next(d for d in docs if d["document_type"] == "Privacy Policy")
            assert len(privacy_doc["versions"]) == 1
            assert privacy_doc["versions"][0]["version_number"] == 1
            v1_hash = privacy_doc["versions"][0]["content_hash"]

            # 3. Re-crawl with UNCHANGED hash -> verify no duplicate PolicyVersion
            async with AsyncSessionLocal() as session:
                crawl_data_v1 = await VendorCrawlerService().crawl_vendor(target_url)
                processed = await sync_vendor_crawled_documents(session, vendor_id, crawl_data_v1["documents"])
                assert len(processed) >= 2

            # Re-fetch privacy document versions from DB
            async with AsyncSessionLocal() as session:
                from sqlalchemy.orm import selectinload
                doc_stmt = select(Document).options(selectinload(Document.versions)).where(Document.id == privacy_doc["id"])
                doc_obj = (await session.execute(doc_stmt)).scalar_one()
                assert len(doc_obj.versions) == 1 # Still 1 version because hash was unchanged!

            # 4. Re-crawl with CHANGED text -> verify new PolicyVersion (v2) and Alert created
            def mock_http_handler_v2(request: httpx.Request):
                url_str = str(request.url)
                if url_str == target_url:
                    return httpx.Response(200, html=SAMPLE_MOCK_HOMEPAGE)
                elif "/privacy" in url_str:
                    return httpx.Response(200, html=SAMPLE_MOCK_PRIVACY_V2) # Changed text!
                elif "/terms" in url_str:
                    return httpx.Response(200, html=SAMPLE_MOCK_TERMS)
                return httpx.Response(404)

            async def mocked_crawl_v2(self, vendor_url, client=None):
                mock_transport = httpx.MockTransport(mock_http_handler_v2)
                async with httpx.AsyncClient(transport=mock_transport) as mock_client:
                    return await original_crawl(self, vendor_url, client=mock_client)

            VendorCrawlerService.crawl_vendor = mocked_crawl_v2

            async with AsyncSessionLocal() as session:
                crawl_data_v2 = await VendorCrawlerService().crawl_vendor(target_url)
                await sync_vendor_crawled_documents(session, vendor_id, crawl_data_v2["documents"])

            # Verify version 2 and Alert in DB
            async with AsyncSessionLocal() as session:
                doc_stmt = select(Document).options(selectinload(Document.versions)).where(Document.id == privacy_doc["id"])
                doc_obj = (await session.execute(doc_stmt)).scalar_one()
                assert len(doc_obj.versions) == 2
                assert doc_obj.versions[0].version_number == 2
                assert doc_obj.versions[0].content_hash != v1_hash

                alert_stmt = select(Alert).where(Alert.vendor_id == vendor_id)
                alerts = (await session.execute(alert_stmt)).scalars().all()
                assert len(alerts) >= 1
                assert "Policy Updated" in alerts[0].title

    finally:
        VendorCrawlerService.crawl_vendor = original_crawl


@pytest.mark.asyncio
async def test_vendor_api_invalid_url_error_handling():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/vendors/", json={
            "name": "Invalid Domain",
            "domain": "invalid",
            "website_url": "not-a-valid-url"
        })
        # Invalid format handled cleanly with 400 Bad Request
        assert res.status_code in [400, 422]
