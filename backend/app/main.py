from .database import engine, Base
from . import models

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

@app.get("/")
def home():
    return {"message": "VendorGuard AI Backend Running"}


@app.post("/analyze")
def analyze_vendor(vendor: VendorRequest):

    privacy_url = find_privacy_policy(vendor.url)

    if not privacy_url:
        return {
            "message": "Privacy Policy not found"
        }

    text = fetch_website(privacy_url)
    analysis = analyze_policy(text)

    return {
    "message": "AI Analysis Completed",
    "privacy_policy_url": privacy_url,
    "characters_downloaded": len(text),
    "analysis": analysis
}
    