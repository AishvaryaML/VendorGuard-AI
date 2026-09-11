import re
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.vendor import VendorCreate, VendorResponse, VendorUpdate
from app.schemas.document import DocumentResponse
from app.schemas.risk import RiskAssessmentResponse
from app.schemas.report_schema import VendorSecurityReport
from app.schemas.policy_diff import PolicyDiffResponse, PolicyVersionSummary
from app.services.crawler import VendorCrawlerService, normalize_url
from app.services import vendor_service, policy_diff_service
from app.services.risk_engine import AIRiskEngine, get_latest_vendor_risk_assessment
from app.services.report_service import (
    build_vendor_security_report,
    generate_markdown_report,
    generate_pdf_report,
)

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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register vendor profile: {str(exc)}"
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


@router.get("/{vendor_id}/documents/{document_id}/versions", response_model=List[PolicyVersionSummary])
async def get_document_versions(
    vendor_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all historical policy versions for a specific document."""
    try:
        versions = await policy_diff_service.get_document_versions(
            db=db,
            vendor_id=vendor_id,
            document_id=document_id
        )
        return versions
    except ValueError as ve:
        err_msg = str(ve)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document versions: {str(exc)}"
        )


@router.get("/{vendor_id}/documents/{document_id}/diff", response_model=PolicyDiffResponse)
async def get_policy_diff(
    vendor_id: str,
    document_id: str,
    v1: str = Query(..., description="ID of baseline/older policy version"),
    v2: str = Query(..., description="ID of comparison/newer policy version"),
    db: AsyncSession = Depends(get_db)
):
    """
    Computes/retrieves structured deterministic diff and AI semantic impact analysis
    between two policy versions for a vendor document.
    """
    try:
        diff_response = await policy_diff_service.get_or_compute_policy_diff(
            db=db,
            vendor_id=vendor_id,
            document_id=document_id,
            old_version_id=v1,
            new_version_id=v2
        )
        return diff_response
    except ValueError as ve:
        err_msg = str(ve)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute policy diff: {str(exc)}"
        )


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


@router.post("/{vendor_id}/analyze", response_model=RiskAssessmentResponse, status_code=status.HTTP_200_OK)
async def analyze_vendor_risk(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers an AI risk assessment for the specified vendor.
    Retrieves stored PolicyVersion content, runs structured evidence-backed LLM risk extraction,
    validates evidence quotes, computes category scores & overall weighted risk score,
    determines risk tier, and persists RiskAssessment + CategoryScore records.
    """
    vendor = await vendor_service.get_vendor_by_id(db=db, vendor_id=vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{vendor_id}' not found."
        )

    try:
        engine = AIRiskEngine()
        assessment = await engine.analyze_vendor(db=db, vendor_id=vendor_id)
        return assessment
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(re)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk analysis failed unexpectedly: {str(exc)}"
        )


@router.get("/{vendor_id}/risk-assessment", response_model=RiskAssessmentResponse)
async def get_vendor_risk_assessment(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the latest persisted risk assessment for a specific vendor.
    """
    vendor = await vendor_service.get_vendor_by_id(db=db, vendor_id=vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{vendor_id}' not found."
        )

    assessment = await get_latest_vendor_risk_assessment(db=db, vendor_id=vendor_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No risk assessment found for vendor with ID '{vendor_id}'."
        )
    return assessment


@router.get("/{vendor_id}/report", response_model=VendorSecurityReport)
async def get_vendor_report(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generates and returns the complete structured executive security assessment report
    for a specified vendor.
    """
    report = await build_vendor_security_report(db=db, vendor_id=vendor_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{vendor_id}' not found."
        )
    return report


@router.get("/{vendor_id}/report/markdown")
async def download_vendor_report_markdown(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generates and downloads a complete GitHub-Flavored Markdown executive security assessment report.
    """
    report = await build_vendor_security_report(db=db, vendor_id=vendor_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{vendor_id}' not found."
        )
    md_content = generate_markdown_report(report)
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", report.vendor.name.lower()).strip("_")
    filename = f"vendorguard_{slug}_security_report.md"
    return Response(
        content=md_content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/{vendor_id}/report/pdf")
async def download_vendor_report_pdf(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generates and downloads a publication-grade PDF executive security assessment report.
    """
    report = await build_vendor_security_report(db=db, vendor_id=vendor_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{vendor_id}' not found."
        )
    pdf_bytes = generate_pdf_report(report)
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", report.vendor.name.lower()).strip("_")
    filename = f"vendorguard_{slug}_security_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

