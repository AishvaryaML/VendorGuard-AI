# VendorGuard AI — Frontend Prototype

AI-Powered Third-Party Vendor Risk Intelligence Platform — frontend-only prototype.
Consumes an existing FastAPI backend (`POST /analyze`) that discovers and downloads
a vendor's privacy policy.

## Tech Stack

- React 18 + Vite
- Tailwind CSS
- Axios
- React Icons

## Prerequisites

- Node.js 18+
- The FastAPI backend running locally at `http://127.0.0.1:8000` with a working
  `POST /analyze` endpoint (see request/response shape below).

## Setup

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`.

## Build for production

```bash
npm run build
npm run preview
```

## Backend contract

**Request**

```
POST http://127.0.0.1:8000/analyze
Content-Type: application/json

{ "url": "https://openai.com" }
```

**Response**

```json
{
  "message": "Privacy Policy downloaded successfully",
  "privacy_policy_url": "https://openai.com/security-and-privacy/",
  "characters_downloaded": 5800,
  "preview": "Security and privacy at OpenAI..."
}
```

If the backend URL changes, update `API_BASE_URL` in `src/services/api.js`.

## Project structure

```
frontend/
├── public/
│   └── shield.svg
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── Navbar.jsx
│   │   ├── Hero.jsx
│   │   ├── VendorForm.jsx
│   │   ├── LoadingSpinner.jsx
│   │   ├── ResultCard.jsx
│   │   └── Footer.jsx
│   ├── pages/
│   │   └── Home.jsx
│   ├── services/
│   │   └── api.js
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── index.html
├── tailwind.config.js
├── postcss.config.js
├── vite.config.js
└── package.json
```

## Scope notes

This prototype intentionally only displays what the backend actually returns
(privacy policy URL, character count, and a text preview). Risk scores,
compliance scores, dashboards, graphs, and vendor history are **not**
implemented — they're listed under "Next Phase" on the page as planned work.
