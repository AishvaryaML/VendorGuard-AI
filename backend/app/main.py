from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import engine, Base, SessionLocal
from . import models
from .schemas import VendorRequest
from .services.web_scraper import fetch_website, find_privacy_policy
from .services.ai_analyzer import analyze_policy

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

    existing_vendor = (
        db.query(models.Vendor)
        .filter(models.Vendor.website == vendor.url)
        .first()
    )

    if not existing_vendor:
        new_vendor = models.Vendor(
            name=vendor.url,
            website=vendor.url
        )
        db.add(new_vendor)
        db.commit()
        db.refresh(new_vendor)

    privacy_url = find_privacy_policy(vendor.url)

    if not privacy_url:
        return {
            "message": "Privacy Policy not found"
        }

    text = fetch_website(privacy_url)

    analysis = analyze_policy(text)

    return {
        "message": "AI Analysis Completed",
        "vendor": vendor.url,
        "privacy_policy_url": privacy_url,
        "characters_downloaded": len(text),
        "analysis": analysis
    }