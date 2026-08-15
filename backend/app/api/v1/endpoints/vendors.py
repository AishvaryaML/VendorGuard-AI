from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.vendor import VendorCreate, VendorResponse, VendorUpdate
from app.schemas.document import DocumentResponse
from app.services.crawler import VendorCrawlerService, normalize_url
from app.services import vendor_service

router = APIRouter()


@router.post("/", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    vendor_in: VendorCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new vendor profile and initiates initial document discovery & web crawl.
    Discovers legal, security, privacy, terms, and compliance pages, calculates SHA-256 hashes,
    and persists PolicyVersion records in the database.
    """
    try:
        normalize_url(vendor_in.website_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid vendor website URL: {str(e)}"
        )

    try:
        vendor, _ = await vendor_service.create_vendor_and_discover_documents(
            db=db,
            vendor_in=vendor_in
        )
        return vendor
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to crawl vendor website: {str(exc)}"
        )


@router.get("/", response_model=List[VendorResponse])
async def list_vendors(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Lists registered vendor profiles."""
    vendors = await vendor_service.list_vendors(db=db, skip=skip, limit=limit)
    return vendors


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves vendor details by ID."""
    vendor = await vendor_service.get_vendor_by_id(db=db, vendor_id=vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{vendor_id}' not found."
        )
    return vendor


@router.get("/{vendor_id}/documents", response_model=List[DocumentResponse])
async def get_vendor_documents(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all discovered legal & policy documents for a specific vendor."""
    vendor = await vendor_service.get_vendor_by_id(db=db, vendor_id=vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{vendor_id}' not found."
        )
    return vendor.documents


@router.post("/{vendor_id}/crawl", response_model=List[DocumentResponse])
async def recrawl_vendor_documents(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers an on-demand re-crawl of vendor legal policy pages and applies SHA-256 delta versioning.
    """
    vendor = await vendor_service.get_vendor_by_id(db=db, vendor_id=vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{vendor_id}' not found."
        )

    try:
        crawler = VendorCrawlerService()
        crawl_data = await crawler.crawl_vendor(vendor.website_url)
        documents = await vendor_service.sync_vendor_crawled_documents(db, vendor.id, crawl_data["documents"])
        return documents
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Re-crawl failed for vendor '{vendor.name}': {str(exc)}"
        )
