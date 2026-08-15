# VendorGuard AI Setup & Operating Guide

## Prerequisites
- Node.js v18+ (Tested on v24.x)
- Python 3.11+ (Tested on Python 3.13)
- PostgreSQL 15+ (Optional: SQLite fallback is active by default in `.env` for zero-setup local development)

## Installation & Running

### Step 1: Clone & Environment Setup
Ensure `.env` exists in the project root:
```bash
cp .env.example .env
```

### Step 2: Backend Setup
```bash
cd backend
python -m venv venv
# Activate virtual environment:
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

pip install -r requirements.txt
python -m app.main
```
Check health endpoint at: `http://localhost:8000/health`

### Step 3: Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open browser at: `http://localhost:5173`
