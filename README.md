# VendorGuard AI
> **AI-Powered Continuous Third-Party Vendor Risk Intelligence Platform**

VendorGuard AI is a modern cybersecurity SaaS platform designed to automate third-party vendor risk assessment, document discovery (Privacy Policies, Terms of Service, Security / Trust Centers), semantic policy change detection, explainable AI risk scoring with evidence citations, and scheduled continuous monitoring.

---

## 🛠️ Architecture & Tech Stack

### Frontend
- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS + Shadcn UI design primitives
- **Icons & Motion**: Lucide React + Framer Motion
- **Data Visualizations**: Recharts
- **State & Data Fetching**: React Router v6 + TanStack Query v5 + Axios

### Backend
- **Framework**: Python 3.11+ / 3.13 + FastAPI
- **Data Validation & Settings**: Pydantic v2
- **Database & ORM**: SQLAlchemy 2.0 (Async) + PostgreSQL (with SQLite async fallback)
- **Background Tasks**: APScheduler / Async Worker queue

---

## 🚀 Quick Start (Development Setup)

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python -m app.main
```
The FastAPI backend server will run at `http://localhost:8000`. API Swagger documentation will be available at `http://localhost:8000/docs`.

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The React SPA dashboard will run at `http://localhost:5173`.

---

## 📂 Project Directory Structure

```
VENDORGUARD_AI/
├── backend/                  # FastAPI Python backend service
│   ├── app/
│   │   ├── api/              # API v1 route handlers
│   │   ├── core/             # Configuration, database setup, CORS, logging
│   │   ├── models/           # SQLAlchemy DB models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic layer
│   │   ├── repositories/     # Data access layer
│   │   ├── workers/          # Continuous monitoring scheduler
│   │   └── main.py           # Application entrypoint
│   ├── tests/                # Pytest unit and integration tests
│   └── requirements.txt
├── frontend/                 # Vite React TypeScript single page application
│   ├── src/
│   │   ├── components/       # Layout, Navbar, Sidebar, Reusable UI primitives
│   │   ├── features/         # Page components (Dashboard, Vendors, Monitoring, Risk, etc.)
│   │   ├── hooks/            # Custom React hooks
│   │   ├── services/         # API service wrappers (Axios)
│   │   ├── types/            # TypeScript interfaces
│   │   └── App.tsx           # Route setup & layout wrapper
│   ├── package.json
│   └── vite.config.ts
├── docs/                     # Architecture & setup documentation
├── .env.example              # Environment variables template
└── README.md
```

---

## 📄 License
Academic Final-Year Project — Proprietary & Confidential.
