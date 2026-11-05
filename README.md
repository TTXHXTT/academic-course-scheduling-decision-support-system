# Academic Course Scheduling Decision-Support System (ACS)
**CSE 6550: Software Engineering in the AI Era — California State University, San Bernardino (CSUSB)**  
**Project Team:** Group 5  
**Team Members:** Savannah Hebert, Bao Ngo, Brandon Varela, Shraddha Paithankar, Xiangyu Qu  
**Authoritative Baselines:**
- `CSE6550_SRS_v2.0_Requirements_Baseline_Template.md` (SRS v2.0 Requirements Baseline)
- `ACS_Group5_SPMP_Completed.md` (SPMP v1.0 Project Management Plan)

---

## 1. Executive Summary & Purpose

The **Academic Course Scheduling Decision-Support System (ACS)** is an explainable decision-support software prototype designed to assist **CSUSB department chairs, academic schedulers, and program coordinators** in deciding which courses and sections to offer each semester.

Rather than acting as an autonomous timetable engine or faculty assigner, ACS provides **evidence-based analytical decision support**:
1. **Historical Data Management (FR-01, DR-01, DR-02):** Ingests, validates, and stores historical academic course and section offerings without silent data loss.
2. **Data Exploration & Trends (FR-02, FR-03):** Queries and filters historical records by course, term, and modality, presenting multi-term enrollment, capacity utilization, and student demand trends across individual courses or groups of courses.
3. **Course Demand Analysis (FR-04, NFR-05):** Employs a self-contained, modular analytics engine (`app/analytics/`) computing weighted utilization, full-capacity rates, and linear regression demand trends.
4. **Explainable Recommendations (FR-05, FR-06):** Generates actionable, deterministic course-offering recommendations (section additions, consolidations, demand monitoring) backed by transparent formula citations, trigger evidence, and data limitation disclosures.
5. **What-If Scenario Support (FR-07, FR-08, DR-03):** Enables safe, hypothetical parameter adjustments (adding sections, adjusting section capacity, simulating demand growth) with baseline delta comparisons without modifying historical data.

---

## 2. Requirements Traceability Matrix (SRS v2.0 Baseline)

| Requirement ID | Type | Description | System Implementation | Verification (SRS Sec 11) |
|---|---|---|---|---|
| **FR-01** | Functional | Dataset import by authorized user | CSV ingestion via `ImportService` (`/api/datasets/upload`), role-gated to Schedulers and Admins. | Test (`test_import.py`, `test_api.py`) |
| **FR-02** | Functional | Query & filter records by course, term, modality | Section query engine (`/api/records`) with pagination, search, term, and modality filters. | Test (`test_api.py`) |
| **FR-03** | Functional | Enrollment, utilization, and demand trends across terms for course(s) | Multi-term course and group trends API (`/api/records/trends`) and interactive Chart.js visualizations. | Test (`test_api.py`, `test_analytics_engine.py`) |
| **FR-04** | Functional | Course demand analysis result production | Demand analysis engine (`DemandEngine.analyze()`) calculating weighted utilization, full-capacity rate, and regression slopes. | Analysis / Test (`test_analytics_engine.py`, `test_api.py`) |
| **FR-05** | Functional | Formulate course-offering recommendations | Deterministic rules engine (`RecommendationRules`) generating section additions, consolidations, and monitoring alerts. | Test (`test_analytics_engine.py`, `test_api.py`) |
| **FR-06** | Functional | Supporting data & explainability for recommendations | Recommendation drawer and `/api/recommendations/{id}` exposing rule descriptions, evidence payloads, and formula citations. | Inspection / Test (`test_analytics_engine.py`, `test_api.py`) |
| **FR-07** | Functional | Create what-if scenario modifying offering parameters | Scenario simulation builder (`/api/scenarios/`) supporting section additions, capacity adjustments, and demand surges. | Test (`test_api.py`) |
| **FR-08** | Functional | Display what-if baseline comparison & delta | Comparison view displaying baseline vs simulated sections, utilization, and delta % with simulation safeguards. | Test (`test_api.py`) |
| **DR-01** | Data | Store all required academic fields | SQLAlchemy `CourseRecord` model capturing course_id, section_id, term, year, semester, days, times, modality, campus, enrollment, capacity, attempted enrollment, unmet demand, major, class level. | Test (`test_import.py`) |
| **DR-02** | Data | Identify missing, invalid, or inconsistent records | `ImportService` validation engine flagging blank keys, negative values, and enrollment > capacity without silent row loss. | Test (`test_import.py`) |
| **DR-03** | Data | Reference input datasets and scenario values | Immutable foreign keys linking analyses, evidence, and what-if runs to source datasets and baseline parameters. | Test (`test_api.py`) |
| **NFR-01** | Quality | Security & authenticated access | Bcrypt password hashing, signed JWT tokens, cookie/bearer auth, and strict RBAC enforcement. | Test (`test_api.py`) |
| **NFR-02** | Quality | Usability & accessibility | Dual textual explanations and Chart.js graphical charts across dashboard, explorer, analysis, and scenario views. | Demonstration / Inspection |
| **NFR-03** | Quality | Performance | Sub-second response times (<500ms) for data querying and indexing, fast in-memory pure analytics processing. | Test / Analysis (`test_api.py`) |
| **NFR-04** | Quality | Reliability & Data Quality | Explicit tracking of data limitations in `CourseMetrics.limitations` and UI banner notifying users of potential impacts. | Test (`test_analytics_engine.py`, `test_import.py`) |
| **NFR-05** | Quality | Maintainability & Modularity | Self-contained `DemandEngine` module with zero web/DB dependencies, reusable for any academic department. | Test (`test_analytics_engine.py`) |
| **COM-01** | Policy | Requirements quality standard | Consistent requirements IDs, testable shall statements, documented sources, and verification methods. | Inspection |
| **COM-02** | Policy | AI assistance and provenance record | Full documentation of AI assistance, human verification, and responsibility in project dossiers. | Inspection |

---

## 3. System Boundary & Explicit Scope Exclusions (SRS Section 1.3 / LIM-01 to LIM-05)

To maintain compliance with the project scope baseline:
- **Decision-Support Principle (LIM-02):** ACS generates recommendations and simulations strictly to inform human decision-makers. Academic leaders retain final scheduling authority.
- **No Automated Faculty Assignment (LIM-05):** ACS does not assign instructors or evaluate faculty contracts / collective bargaining agreements.
- **No Room Optimization (LIM-05):** ACS does not optimize classroom locations, physical room constraints, or campus room availability.
- **No Full University-Wide Timetable Engine (LIM-01):** Prototype focuses on departmental course offerings and capacity decision support.
- **No Production SIS Integration (LIM-04):** Operates on imported historical data files (CSV format) without live write-back to production campus student information systems.

---

## 4. Technology Architecture

```
acs/
├── app/
│   ├── analytics/         # Pure Python analytics (Metrics, DemandEngine, RecommendationRules) [NFR-05]
│   ├── api/               # FastAPI REST routers (auth, datasets, records, analysis, recs, scenarios, audit)
│   ├── core/              # Config (env vars), Database session maker, Security (bcrypt/JWT)
│   ├── models/            # SQLAlchemy ORM models (User, Dataset, CourseRecord, AnalysisRun, Scenario, etc.)
│   ├── schemas/           # Pydantic validation schemas
│   ├── services/          # Business logic layer (import, analysis, recommendation, scenario, audit)
│   ├── static/            # CSS stylesheets and vanilla JavaScript API client
│   ├── templates/         # Jinja2 HTML templates for all application modules
│   └── main.py            # FastAPI entry point & HTML routes
├── data/
│   └── synthetic/         # CSUSB demonstration datasets (courses.csv, students.csv, validation fixtures)
├── docs/                  # Architecture Decision Records (ADRs) and design documentation
├── tests/                 # Pytest test suite (91 automated unit, integration, and verification tests)
├── seed.py                # Database initialization and demonstration seeding script
├── requirements.txt       # Python dependencies
├── pytest.ini             # Pytest configuration
├── docker-compose.yml     # Containerized deployment definition
├── Dockerfile             # Container build recipe
└── .env.example           # Documented environment configuration template (SQLite & Neon PostgreSQL)
```

---

## 5. Getting Started & Running the Application

### Prerequisites
- Python 3.10+
- System Python or virtual environment

### Quick Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Database (Optional)**:
   - By default, ACS runs locally using SQLite (`sqlite:///./acs_dev.db`).
   - For cloud / Neon-hosted PostgreSQL (SPMP Section 3), set `DATABASE_URL` in `.env`:
     ```env
     DATABASE_URL=postgresql://<user>:<password>@<ep-proj-name>.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```

3. **Initialize & Seed the Database**:
   ```bash
   python seed.py
   ```
   *This seeds the demonstration users, loads the verified CSUSB historical dataset, executes the baseline demand analysis, and creates explainable recommendations.*

4. **Launch the Server**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

5. **Access the Application**:
   Open your browser to: **`http://localhost:8000`** (or `http://127.0.0.1:8000`).

---

## 6. Demonstration Accounts (Stakeholder Classes per SRS 2.4 & SPMP 4.3)

| Role | Email | Password | Allowed Capabilities |
|---|---|---|---|
| **Department Chair** | `chair@csusb.edu` | `Chair@123` | View trends, review recommendations, record administrative decisions, inspect audit logs. |
| **Academic Scheduler** | `scheduler@csusb.edu` | `Scheduler@123` | Upload historical CSV datasets, review validation errors, explore records, run what-if scenarios. |
| **Program Coordinator** | `coordinator@csusb.edu` | `Coord@123` | Explore course demand patterns, inspect recommendations, run what-if scenarios. |
| **System Administrator** | `admin@csusb.edu` | `Admin@CSUSB123` | Full administrative access across data ingestion, user management, analysis runs, and audit logs. |

---

## 7. Automated Test Suite (SRS Section 11)

The test suite contains **79 automated unit, integration, and API tests** verifying all requirements:
- `tests/test_analytics_engine.py`: Pure analytics engine unit tests (weighted utilization, full capacity rates, linear regression demand trend, unmet demand).
- `tests/test_import.py`: Data ingestion, field mapping, and validation tests (DR-01, DR-02, NFR-04).
- `tests/test_api.py`: FastAPI routes, RBAC permissions, audit logging, and HTML template rendering.
- `tests/test_student_schedule.py`: Optional student schedule exploration tests.

To run the complete automated test suite:
```bash
pytest
```
*Current status: **79 passed, 0 failed**.*
