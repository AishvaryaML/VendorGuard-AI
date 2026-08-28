import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawler import VendorCrawlerService
from app.services import vendor_service
from app.services.agents.state import VendorRiskState

logger = logging.getLogger("vendorguard.agents.discovery")


class DiscoveryAgent:
    """
    Specialized Discovery Agent responsible for:
    - Vendor website discovery
    - Discovering legal, privacy, security, and compliance policy documents
    - Calling VendorCrawlerService and syncing policy versions
    - Handling crawl failures cleanly
    """

    def __init__(self, crawler_service: Optional[VendorCrawlerService] = None):
        self.crawler = crawler_service or VendorCrawlerService()

    async def run(self, state: VendorRiskState, db: AsyncSession) -> Dict[str, Any]:
        vendor_id = state.get("vendor_id")
        logger.info(f"DiscoveryAgent executing for vendor_id '{vendor_id}'")

        state["current_step"] = "discovery"
        state["status"] = "crawling"

        vendor = await vendor_service.get_vendor_by_id(db=db, vendor_id=vendor_id)
        if not vendor:
            err = f"DiscoveryAgent failure: Vendor with ID '{vendor_id}' not found."
            logger.error(err)
            errors = state.get("errors", [])
            errors.append(err)
            return {
                "current_step": "discovery",
                "status": "failed",
                "errors": errors
            }

        vendor_name = vendor.name
        vendor_domain = vendor.domain
        vendor_url = vendor.website_url

        state["vendor_name"] = vendor_name
        state["domain"] = vendor_domain
        state["website_url"] = vendor_url

        try:
            crawl_data = await self.crawler.crawl_vendor(vendor_url)
            documents = await vendor_service.sync_vendor_crawled_documents(
                db=db, vendor_id=vendor.id, raw_documents=crawl_data["documents"]
            )

            discovered_info = [
                {
                    "document_id": doc.id,
                    "document_type": doc.document_type,
                    "title": doc.title,
                    "url": doc.url,
                    "version_hash": doc.current_version_hash,
                }
                for doc in documents
            ]

            logger.info(f"DiscoveryAgent completed: {len(discovered_info)} documents discovered for '{vendor_name}'")

            return {
                "vendor_name": vendor_name,
                "domain": vendor_domain,
                "website_url": vendor_url,
                "discovered_documents": discovered_info,
                "current_step": "discovery",
                "status": "crawling_completed",
            }

        except Exception as exc:
            err_msg = f"DiscoveryAgent crawl failed for '{vendor_name}': {str(exc)}"
            logger.error(err_msg, exc_info=True)
            errors = state.get("errors", [])
            errors.append(err_msg)
            return {
                "current_step": "discovery",
                "status": "failed",
                "errors": errors
            }
