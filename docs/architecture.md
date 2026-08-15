# VendorGuard AI Architecture Documentation

## Overview
VendorGuard AI monitors third-party vendors by systematically discovering public policies (Privacy, Terms, Trust Center), tracking semantic changes over time, assessing security/privacy/compliance/legal risk using LLMs, and alerting security teams when risk elevates.

## Core Component Diagram
```
+--------------------------------------------------------------------+
|                         React SPA (Vite)                           |
|        Enterprise Cybersecurity UI / Dashboard / Risk Analytics    |
+---------------------------------+----------------------------------+
                                  |
                                  | REST / JSON
                                  v
+---------------------------------+----------------------------------+
|                     FastAPI Backend Gateway                        |
|   (Auth, CORS, OpenAPI, Exception Handler, Structured Logging)     |
+--------+------------------------+-----------------------+----------+
         |                        |                       |
         v                        v                       v
+--------+-------+       +--------+-------+      +--------+-------+
|  Services &    |       | Async Scraper  |      |   LangChain    |
| Repositories   |       | & Scheduler    |      |  AI Risk Engine|
+--------+-------+       +--------+-------+      +--------+-------+
         |                        |                       |
         +------------------------+-----------------------+
                                  |
                                  v
+---------------------------------+----------------------------------+
|               PostgreSQL / SQLite Database                         |
|     (Vendors, Versions, Diffs, Risk Snapshots, Audit Logs)         |
+--------------------------------------------------------------------+
```

## Modular Layering
1. **API Layer (`app/api/v1`)**: Handles HTTP requests, input validation via Pydantic schemas, and response formatting.
2. **Service Layer (`app/services`)**: Encapsulates core domain business logic (Crawling, AI Analysis, Version Diffs, Risk Trends).
3. **Repository Layer (`app/repositories`)**: Encapsulates database queries using SQLAlchemy 2.0 Async Session.
4. **Model Layer (`app/models`)**: Declarative SQLAlchemy ORM models matching database tables.
5. **Worker Layer (`app/workers`)**: Scheduled background tasks (APScheduler) for periodic vendor checks.
