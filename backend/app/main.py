from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .services.reporting.report_generator import generate_report
from .database import engine, Base, SessionLocal
from .models import Vendor
from .schemas import VendorRequest
from .services.web_scraper import fetch_website, find_privacy_policy
from .services.ai_analyzer import analyze_policy
from .services.crawler.discovery import VendorDiscoveryService
from .services.scoring.risk_scorer import calculate_risk

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {"message": "VendorGuard AI Backend Running"}


@app.post("/analyze")
def analyze_vendor(vendor: VendorRequest, db: Session = Depends(get_db)):

    # Step 1: Discover important vendor pages
    discovery = VendorDiscoveryService()
    result = discovery.discover(vendor.url)

    print(result)

    # Step 2: Save vendor if not already present
    existing_vendor = (
        db.query(Vendor)
        .filter(Vendor.website == vendor.url)
        .first()
    )

    if not existing_vendor:
        new_vendor = Vendor(
            name=vendor.url,
            website=vendor.url
        )
        db.add(new_vendor)
        db.commit()
        db.refresh(new_vendor)

    # Step 3: Find Privacy Policy
    privacy_url = result.get("privacy")

    if not privacy_url:
        return {
            "message": "Privacy Policy not found",
            "discovery": result
        }

    # Step 4: Download Privacy Policy
    text = fetch_website(privacy_url)

    # Step 5: AI Analysis
    analysis = analyze_policy(text)

    # Step 6: Calculate Risk Score
    risk = calculate_risk(analysis)

    # Step 7: Return Complete Report
    report = generate_report(
    vendor=vendor.url,
    privacy_url=privacy_url,
    analysis=analysis,
    risk=risk,
    characters_downloaded=len(text),
    discovery=result
    )

    return report