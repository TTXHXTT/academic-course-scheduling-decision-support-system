# Academic Course Scheduling Decision-Support System (ACS)
**CSE 6550: Software Engineering in the AI Era — California State University, San Bernardino (CSUSB)**  
**Authoritative Baseline:** `CSE6550_SRS_v0.1_Requirements_Baseline_Template.pdf`

---

## 1. Executive Summary & Purpose

The **Academic Course Scheduling Decision-Support System (ACS)** is a web-based decision-support prototype engineered to assist department chairs, academic schedulers, and program coordinators at CSUSB in making evidence-based course-offering and capacity decisions.

Rather than acting as an autonomous university timetable engine or faculty assigner, ACS provides **analytical decision support**:
- Discovers historical enrollment and capacity trends across academic terms.
- Detects bottlenecks, courses frequently operating at or above capacity, and underutilized sections.
- Formulates actionable, deterministic course-offering recommendations (e.g., section additions, consolidations, or demand monitoring) backed by transparent formula citations and documented data limitations.
- Enables safe, hypothetical **What-If Scenarios** to simulate the impact of adding sections, adjusting capacities, or demand surges without altering historical academic records.

---

## 2. Requirements Traceability Matrix

| Requirement ID | Module | Implementation |
|---|---|---|
| **FR-01, FR-02** | Module B: Data Import | CSV ingestion with strict column validation, error logging without silent data loss, and warning detection for enrollment > capacity. |
| **FR-03, FR-04** | Module C: Explorer | Section and course query engine with term, modality, and utilization filtering. Detailed course history drawer. |
| **FR-05, FR-06** | Module D: Analytics | Pure analytics engine (`app/analytics/`) calculating weighted utilization, linear regression demand trends, and full capacity rates. |
| **FR-07, FR-08** | Module E: Recommendations | Deterministic rule engine (`app/analytics/rules.py`) with plain-language explanations, evidence payloads, confidence levels, and chair approval tracking. |
| **FR-09, FR-10** | Module F: Scenarios | Simulation service (`app/services/scenario_service.py`) executing hypothetical modifications with prominent disclaimers and delta comparisons. |
| **NFR-01** | Security & Auth | Bcrypt password hashing, signed JWT tokens, role-based access control (Chair, Scheduler, Coordinator, Admin). |
| **NFR-02, DR-03** | Traceability | Immutable analysis history recording method version (`1.0.0`), dataset ID, and exact parameter thresholds. |
| **NFR-03** | Audit & Compliance | Audit logging service capturing logins, uploads, runs, scenario tests, and recommendation approvals. |
| **COM-01** | Assumptions | Configurable thresholds documented as prototype assumptions rather than university-wide mandates. |

---

## 3. Technology Architecture

```
acs/
├── backend/
│   ├── app/
│   │   ├── analytics/         # Pure Python analytics (Metrics, DemandEngine, RecommendationRules)
│   │   ├── api/               # FastAPI routers (auth, datasets, records, analysis, recs, scenarios, audit)
│   │   ├── core/              # Config (env vars), Database session maker, Security (bcrypt/JWT)
│   │   ├── models/            # SQLAlchemy ORM models (User, Dataset, CourseRecord, AnalysisRun, etc.)
│   │   ├── schemas/           # Pydantic validation schemas
│   │   ├── services/          # Business logic layer (import, analysis, recommendation, scenario, audit)
│   │   ├── static/            # CSS stylesheets and vanilla JavaScript API client
│   │   ├── templates/         # Jinja2 HTML templates for all 8 application modules
│   │   └── main.py            # FastAPI entry point & HTML routes
│   ├── tests/                 # Automated Pytest suite (67 unit and integration tests)
│   ├── seed.py                # Database initialization and demonstration seeding script
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile             # Container definition
├── data/
│   └── synthetic/             # CSUSB demonstration datasets (3,799 sections and test fixtures)
├── docker-compose.yml         # Containerized PostgreSQL and application deployment
├── .env.example               # Documented environment configuration template
└── README.md                  # This documentation
```

---

## 4. Getting Started & Running the Application

### Prerequisites
- Python 3.10+
- Virtual environment or system Python (`D:\PythonEnt\python.exe` or standard `python`)

### Quick Setup

1. **Install Dependencies** (if not already installed):
   ```bash
   cd acs/backend
   pip install -r requirements.txt
   ```

2. **Initialize & Seed the Database**:
   ```bash
   cd acs/backend
   python seed.py
   ```
   *This seeds the demonstration users and imports the CSUSB multi-term synthetic dataset (3,799 section records), runs the baseline demand analysis, and generates recommendations.*

3. **Launch the Server**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

4. **Access the Application**:
   Open your browser to: **`http://localhost:8000`** (or `http://127.0.0.1:8000`)

---

## 5. Demonstration Accounts

The system provides 4 pre-configured role-based demonstration accounts (accessible via 1-click login on the `/login` page):

| Role | Email | Password | Allowed Capabilities |
|---|---|---|---|
| **Department Chair** | `chair@csusb.edu` | `Chair@123` | View trends, review recommendations, record administrative decisions, inspect audit logs. |
| **Academic Scheduler** | `scheduler@csusb.edu` | `Scheduler@123` | Upload historical CSV datasets, review validation errors, explore records, run what-if scenarios. |
| **Program Coordinator** | `coordinator@csusb.edu` | `Coord@123` | Explore course demand patterns, inspect recommendations, run program what-if scenarios. |
| **System Administrator** | `admin@csusb.edu` | `Admin@CSUSB123` | Full access across data ingestion, user management, analysis runs, and system audit trails. |

---

## 6. Running the Automated Test Suite

The test suite covers:
- **Pure Analytics Engine**: Section utilization, weighted utilization, full-capacity rate, demand trend slope, unmet demand handling, deterministic consistency.
- **Data Ingestion & Validation**: Required fields, negative values, missing value preservation, warning flags, edge cases (empty files, header-only, duplicates).
- **Authentication & RBAC**: JWT lifecycle, role permission enforcement, protected endpoints.
- **API Endpoints**: Datasets, analysis runs, recommendation lifecycle, scenario simulations.
- **HTML UI Pages**: Template rendering and route availability.

Run the tests with:
```bash
cd acs/backend
pytest
```
*Current test status: **67 passed, 0 failed**.*

---

## 7. Scope Boundaries (SRS Section 1.3)

To maintain compliance with the project scope baseline:
- **Explicitly Excluded**: Autonomous faculty assignment, room assignment optimization, faculty union contract interpretation, live production SIS integration.
- **Decision Support Principle**: All recommendations are advisory. Administrators retain final responsibility for schedule publication.
