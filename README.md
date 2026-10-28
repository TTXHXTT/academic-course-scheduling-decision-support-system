## Academic Course Scheduling Decision-Support System (ACS)
## Members: Savannah Hebert, Bao Ngo, Brandon Varela, Shraddha Paithankar, Xiangyu Qu, Erik Marvin

## 1. SOURCE-OF-TRUTH AND SCOPE CONTROL

Priority order:

1. Explicit SRS requirements and scope boundaries.
2. SRS user stories and acceptance criteria.
3. SRS data requirements, interface definitions, assumptions, limitations, and open questions.
4. Implementation decisions needed to create a working prototype.
5. Optional future enhancements explicitly separated from the baseline.

Maintain a requirements traceability record throughout development.

Every implemented baseline feature must map to one or more requirement IDs or documented supporting requirements.

If an implementation idea conflicts with the SRS, follow the SRS.

Do not silently introduce unapproved requirements. Document assumptions and distinguish them from confirmed requirements.

### Critical project identity

ACS is an academic course-offering and course-demand decision-support system.

It helps department chairs, academic schedulers, and program coordinators understand historical academic data, identify student demand patterns, evaluate course-offering recommendations, and compare proposed changes with a baseline analysis.

The system is not intended to be a complete automated university scheduling engine in this release.

### Explicitly out of scope for the baseline

Do not make any of the following mandatory baseline features:

- Automatic faculty assignment.
- Automatic generation of a complete weekly timetable.
- Room optimization or classroom assignment optimization.
- Faculty leave and substitute-teacher management.
- Complete faculty workload management.
- Full university-wide scheduling optimization.
- Production integration with CSUSB information systems.
- Automated interpretation of faculty contracts or collective bargaining agreements.
- Automated enforcement of accreditation requirements.
- Deployment as an official university system.

These boundaries are specified in Section 1.3 and the release-planning section of the SRS.

Do not allow optional enhancements to delay completion of the required baseline.

---

## 2. PRODUCT PURPOSE AND EXPECTED OUTCOME

The application must help university academic administrators make evidence-based course-offering decisions.

The core problem is that course-offering decisions depend on historical enrollment, course capacity, unmet student demand, previous offerings, term differences, modality, and other available academic information.

Users need a clear way to understand:

- Which courses demonstrate increasing demand.
- Which courses repeatedly reach capacity.
- Which courses may need additional sections.
- Which courses demonstrate low capacity utilization.
- Whether existing capacity may be insufficient.
- How demand varies across semesters or terms.
- How course modality and offering frequency may affect decisions.
- What supporting data justifies each recommendation.
- How a proposed change affects the analysis compared with the baseline.

The system must provide decision support, not autonomous administrative decisions.

Users retain responsibility for evaluating recommendations and deciding which courses should be offered.

---

## 3. REQUIRED TECHNOLOGY AND ARCHITECTURE

Use the following implementation stack unless the coding environment imposes a documented limitation.

### Frontend

- React.
- TypeScript.
- Vite.
- A consistent, accessible component library or a well-structured custom component system.
- A charting library such as Recharts.
- Responsive layouts using modern CSS.
- A typed API client.

### Backend

- Python.
- FastAPI.
- Pydantic for request and response validation.
- SQLAlchemy or an equivalent well-maintained ORM.
- Alembic for database migrations.
- Pandas for tabular data processing where appropriate.
- A separate Python analytics module for demand analysis and recommendation generation.

### Database

- SQLite for straightforward local development and demonstration.
- PostgreSQL for Docker-based deployment.
- Database configuration through environment variables.
- Database migrations and reproducible seed scripts.
- No hard-coded production credentials.

### Deployment and developer tools

- Dockerfiles for the application services.
- Docker Compose for local deployment.
- A documented `.env.example`.
- Automated backend tests using pytest.
- Frontend tests using an appropriate TypeScript-compatible test framework.
- API documentation through FastAPI's OpenAPI interface.

### Architecture principles

Separate the system into the following logical layers:

1. Frontend presentation and navigation.
2. Backend API and request validation.
3. Application services and access control.
4. Academic data ingestion and validation.
5. Historical data analysis.
6. Recommendation generation and explanation.
7. What-if scenario execution and comparison.
8. Database persistence and audit records.

Keep analytics logic independent from the web framework wherever practical.

Do not place all business logic in one API file or one frontend component.

The analytics engine must be independently testable without starting the web application or connecting to a live university system.

SQLite and PostgreSQL must use compatible schemas and behavior.

Do not claim that SQLite and PostgreSQL are both supported until the application's database initialization, migrations, persistence, and tests have been verified for both.

---

## 4. USERS, AUTHENTICATION, AND PERMISSIONS

Implement authentication appropriate for the prototype.

The SRS identifies three principal user classes:

1. Department chairs.
2. Academic schedulers.
3. Program coordinators.

Provide role-appropriate navigation and actions.

### Department chair

Must be able to:

- View historical enrollment and course-demand trends.
- Explore capacity utilization and unmet demand.
- Review course-offering recommendations.
- Inspect supporting evidence and recommendation explanations.
- Review what-if scenario outcomes.

### Academic scheduler

Must be able to:

- Import historical academic data.
- Review import validation results.
- Filter and query historical records.
- Review demand analyses and recommendations.
- Inspect evidence supporting recommendations.
- Run and compare what-if scenarios.

### Program coordinator

Must be able to:

- Explore course-offering and enrollment trends.
- Review recommendations relevant to program planning.
- Evaluate proposed course-offering changes.
- Run supported what-if scenarios and compare results.

### Authentication requirements

- Require authentication for protected application functions.
- Enforce permissions on the backend, not just by hiding frontend buttons.
- Hash passwords using an appropriate password-hashing library.
- Use secure session or token handling.
- Validate authentication and authorization on protected endpoints.
- Do not include plaintext passwords in source code.
- Do not create an unauthenticated administrative backdoor.
- Provide a safe development-only mechanism for creating demonstration accounts.
- Document the demonstration account setup process.

Do not assume that every user role has unrestricted access to every administrative operation.

Where the SRS does not define a precise permission matrix, use a conservative prototype policy and document it as an implementation assumption.

---

## 5. REQUIRED APPLICATION MODULES

Implement the following modules as connected, functional parts of the same application.

### Module A: Dashboard

Create a dashboard showing the current dataset and its analysis status.

Include, when supported by the imported data:

- Number of courses.
- Number of sections.
- Number of academic terms.
- Total enrollment.
- Aggregate capacity utilization.
- Number of courses repeatedly at capacity.
- Courses showing increasing demand.
- Courses with low utilization.
- Courses with potentially unmet demand.
- Number of recommendations generated.
- Data-quality warnings.
- Most recent analysis run.

Every displayed metric must be calculated from persisted or currently selected data. Do not use hard-coded dashboard values.

Use clear visualizations and plain-language explanations.

Display an informative empty state when no dataset has been imported.

### Module B: Historical academic data management

Implement a data import workflow for supported historical academic datasets.

Support CSV import initially. Additional formats may be implemented if they do not delay the baseline.

The data model must accommodate the academic fields identified in SRS DR-01 and Section 1.2, including:

- Course identifier.
- Section identifier, when available.
- Semester or academic term.
- Days and times.
- Modality.
- Campus or location, when applicable.
- Enrollment.
- Course capacity.
- Attempted or unmet enrollment.
- Student demand.
- Major.
- Student or class level.

Preserve source information and identifiers when available.

Provide:

- A dataset selection or upload page.
- A description of the expected input schema.
- A preview of imported rows.
- Column mapping when necessary.
- Data-type and required-field validation.
- A validation summary.
- Row-level errors and warnings.
- Import success and failure feedback.
- A record of the imported dataset.
- The ability to inspect previously imported datasets.

Never silently discard invalid rows.

When a record is invalid, explain the problem and whether it was rejected, excluded from analysis, or retained with a warning.

Do not treat missing information as zero unless the field's documented semantics justify that interpretation.

If no real CSUSB dataset is supplied, use clearly labeled synthetic demonstration data.

Do not claim synthetic data is actual university data.

### Module C: Data validation and quality

Implement the requirements in DR-02 and NFR-04.

Detect relevant examples of:

- Missing required fields.
- Invalid numeric values.
- Negative enrollment or capacity values where invalid.
- Invalid dates or term values.
- Malformed identifiers.
- Inconsistent course or section references.
- Duplicate records according to documented duplicate-detection rules.
- Enrollment greater than capacity.
- Missing historical periods.
- Inconsistent representations of modality.
- Impossible or ambiguous values that cannot safely be interpreted.

Not every unusual record is necessarily invalid. Distinguish errors from warnings.

For every import, show:

- Total records received.
- Valid records.
- Records with errors.
- Records with warnings.
- Fields affected.
- Error or warning explanation.
- Whether affected records are included in analysis.

Use stable validation codes and clear messages.

Preserve enough information to trace analysis results back to the imported dataset.

### Module D: Historical data explorer

Implement FR-02 and FR-03.

Allow authorized users to search, filter, and inspect historical records by:

- Course.
- Academic term.
- Modality.
- Major, when available.
- Student or class level, when available.
- Other available fields that are useful for exploration.

Display useful trends, including:

- Enrollment over time.
- Capacity utilization over time.
- Course demand changes.
- Courses repeatedly reaching capacity.
- Low-enrollment courses.
- Differences between academic terms.
- Differences by modality.
- Attempted enrollment and unmet demand, when available.

Support both visual and textual representations.

Clearly label filters, units, time ranges, and data limitations.

Avoid presenting unavailable metrics as zero.

### Module E: Course-demand analysis engine

Implement FR-04.

Create a separate, deterministic analytics engine that produces a demand-analysis result for each course in the selected historical dataset.

Use the fields actually available in the data.

Possible calculations include:

- Enrollment by term.
- Capacity utilization.
- Historical enrollment growth.
- Frequency of full sections.
- Average and peak enrollment.
- Available unmet-demand indicators.
- Changes in offering frequency.
- Differences across modalities.
- Evidence of insufficient historical capacity.

Document each formula and the assumptions it requires.

Examples:

Capacity utilization:

`enrollment / capacity × 100`

Only calculate this when capacity is valid and greater than zero.

For aggregate utilization, use a clearly documented weighted formula, such as total enrollment divided by total capacity, when the included records have compatible meanings.

Do not simply average percentages if that would misrepresent the aggregate.

Demand trend:

Use a documented method based on comparable historical periods. Handle missing periods, new courses, and irregular offering schedules explicitly.

Full-capacity frequency:

Calculate the proportion of valid historical observations meeting a documented full-capacity condition.

Do not infer unmet demand from enrollment alone when no attempted-enrollment or unmet-demand field exists.

Do not claim that correlations establish causation.

When the dataset is too small, incomplete, or inconsistent to support a calculation, return a limitation or insufficient-evidence result instead of inventing a confident conclusion.

Statistical methods, business rules, or machine-learning techniques may be used when appropriate. A transparent statistical or rule-based approach is acceptable for the prototype.

If machine learning is used, explain the model, features, validation method, and limitations.

Do not introduce machine learning merely to make the application appear more advanced.

### Module F: Course-offering recommendations

Implement FR-05 and FR-06.

Generate explainable recommendations based on the results of the course-demand analysis.

Possible recommendation categories include:

- Consider adding a section.
- Investigate increasing demand.
- Investigate repeatedly full courses.
- Review low-utilization courses.
- Review potential capacity shortages.
- Investigate a change in modality.
- Investigate a change in offering frequency.
- Review courses with insufficient historical data.

These are examples of recommendations, not automatic decisions.

For each recommendation, display:

1. Course identifier and course name, if available.
2. Recommendation category.
3. Priority or urgency, if the implemented rules support it.
4. Supporting historical observations.
5. Relevant enrollment and capacity figures.
6. Demand trend or other relevant calculation.
7. The rule or analytical method that produced the recommendation.
8. The reason the evidence supports the recommendation.
9. Data limitations and uncertainty.
10. Suggested human follow-up.
11. The input dataset and analysis version.

Distinguish measured facts from inferred recommendations.

Do not invent numerical thresholds and present them as approved CSUSB policies.

If thresholds are necessary for the prototype, make them configurable, document them as prototype assumptions, and show them in the analysis methodology.

Users must be able to inspect why a recommendation was generated.

A recommendation without sufficient supporting evidence must be labeled accordingly.

### Module G: What-if scenario builder

Implement FR-07 and FR-08.

This module is mandatory for the baseline.

Provide a baseline analysis and a scenario editor.

At minimum, support one complete, functional what-if workflow that changes a course-offering parameter.

Preferably support several simple options:

- Add a hypothetical section.
- Change a course's proposed section capacity.
- Limit the number of sections or courses offered.
- Change a proposed course modality.
- Simulate a demand increase.

Only implement an option when its effect can be calculated and explained from the available data.

Workflow:

1. Select a historical dataset.
2. Generate the baseline analysis.
3. Select a supported scenario type.
4. Enter the hypothetical change.
5. Validate the scenario inputs.
6. Execute the scenario using the same documented analytical rules.
7. Compare scenario results against the baseline.
8. Display the changed values, unchanged values, and relevant warnings.
9. Show the assumptions and supporting evidence.
10. Save the scenario and its results for later review.

For example, a user may simulate adding a section for a course that repeatedly reaches capacity and inspect the effect on proposed capacity and utilization.

The application must distinguish simulated results from actual historical observations.

Do not modify the original historical dataset when a scenario is executed.

Do not claim to have optimized a complete university timetable. The baseline scenario evaluates course-offering changes, not faculty assignments or classroom conflicts.

### Module H: Analysis history and traceability

Implement the data traceability intent of DR-03.

Every analysis, recommendation set, and what-if result must retain a reference to:

- The source dataset.
- The analysis run or version.
- The analytical method or rule version.
- Applicable scenario parameters.
- Relevant supporting observations.
- The time the operation was performed.
- The authenticated user who initiated the operation, where applicable.

Allow users to navigate from a recommendation to the evidence supporting it.

Allow users to inspect a previous scenario and understand how it differed from the baseline used at that time.

Avoid recalculating historical results silently when the algorithm or dataset changes.

### Module I: Audit logging

Implement an audit trail for significant actions, including:

- Authentication events where appropriate.
- Dataset imports.
- Import validation.
- Analysis runs.
- Recommendation generation.
- Scenario creation and execution.
- Relevant data modifications.
- Administrative changes.

Store the actor, action, timestamp, and relevant object identifiers.

Do not store plaintext passwords, authentication secrets, or unnecessary sensitive information in audit logs.

Provide an authorized view for inspecting audit events.

Audit logging supports traceability and accountability; do not treat it as proof that all possible security threats have been eliminated.

---

## 6. DATABASE DESIGN

Design a normalized relational schema appropriate for the baseline.

At minimum, consider entities for:

- Users.
- Roles or permissions.
- Imported datasets.
- Dataset schema definitions.
- Historical course records.
- Course and section identifiers.
- Import jobs.
- Validation issues.
- Analysis runs.
- Course-demand analysis results.
- Recommendations.
- Recommendation evidence.
- What-if scenarios.
- Scenario parameters.
- Scenario results.
- Audit events.

Use primary keys, foreign keys, indexes, appropriate numeric types, timestamps, and database constraints.

Avoid unnecessary duplication of historical records.

Keep raw import data or an equivalent reproducible representation so that analysis results can be traced to their inputs.

Document how the system handles dataset revisions and deletion.

Do not create tables for faculty scheduling, room allocation, leave requests, or substitute assignments as mandatory baseline modules. Those belong to optional future extensions unless the team formally changes the SRS.

---

## 7. USER INTERFACE AND NAVIGATION

Build a professional academic administration interface.

The design should be suitable for department chairs, academic schedulers, and program coordinators with different levels of technical expertise.

Use a consistent layout, navigation, typography, spacing, form design, and feedback patterns.

Suggested navigation:

1. Dashboard
2. Data Imports
3. Historical Data Explorer
4. Demand Analysis
5. Recommendations
6. What-If Scenarios
7. Analysis History
8. Audit Log, when authorized
9. Account and Sign Out

Use clear page titles, breadcrumbs where useful, filters, tables, charts, explanatory text, and accessible forms.

### Interface requirements

- Responsive desktop and laptop layouts.
- Usable layouts on smaller screens.
- Keyboard-accessible controls.
- Visible focus indicators.
- Proper form labels.
- Sufficient color contrast.
- Charts accompanied by textual explanations or accessible data tables.
- Loading indicators.
- Empty states.
- Success and error messages.
- Confirmation before destructive operations.
- Clear validation feedback.
- Consistent terminology matching the SRS.
- No decorative metrics that do not correspond to real data.

Use visual design to help users distinguish historical facts, analytical findings, recommendations, hypothetical changes, and data-quality warnings.

Do not make the interface depend exclusively on color to communicate meaning.

---

## 8. SECURITY, PRIVACY, AND DATA PROTECTION

Implement reasonable prototype security controls consistent with NFR-01.

Requirements include:

- Authentication for protected functions.
- Server-side authorization.
- Password hashing.
- Input validation.
- Protection against SQL injection through parameterized queries or safe ORM operations.
- Secure handling of session or token credentials.
- Restricted CORS configuration.
- Safe file upload validation.
- Upload size and file-type limits.
- Safe error messages that do not expose secrets or stack traces to end users.
- Environment-based configuration.
- No credentials committed to source control.
- Secure communication in the intended network deployment.
- Least-privilege database and application permissions where practical.

Use synthetic or anonymized data for demonstrations.

Do not include actual student records, personal identifiers, faculty personal information, or confidential university data in seed files.

Do not send academic datasets to third-party AI services.

Document that a local development configuration is not automatically a production-ready security configuration.

---

## 9. PERFORMANCE AND RELIABILITY

Address NFR-03 and NFR-04.

The application should remain responsive during ordinary data exploration and should provide feedback during longer analysis operations.

Avoid unnecessary full-table processing, repeated calculations, and inefficient database queries.

Use pagination or bounded result sets for large tables where appropriate.

Optimize calculations based on evidence rather than making unsupported performance claims.

The SRS does not specify numerical response-time targets. Do not invent a target and claim it was required by the SRS.

Instead:

- Measure representative operations.
- Record test dataset sizes.
- Record observed response times.
- Identify any slow operations.
- Document prototype limitations.
- Make performance thresholds configurable if useful.

For invalid or incomplete data, provide actionable warnings and preserve the ability to understand how data quality affects the analysis.

---

## 10. SEED DATA AND DEMONSTRATION SCENARIO

Provide a reproducible synthetic dataset suitable for demonstrating the entire baseline workflow.

Include multiple courses and historical academic terms with plausible variation in:

- Enrollment.
- Capacity.
- Course demand.
- Modality.
- Course offerings.
- Full-capacity observations.
- Low-utilization observations.
- Attempted or unmet enrollment, when included.
- Missing and inconsistent records for validation demonstrations.

Mark all synthetic data clearly.

Create at least one valid demonstration dataset that produces useful analysis results and another small validation fixture containing intentionally problematic records.

The seed process must be repeatable and must not create duplicate users or duplicate records each time it runs.

Provide a documented way to reset the development database.

Provide a demonstration workflow showing:

1. Sign in.
2. Import or select a synthetic dataset.
3. Review validation results.
4. Explore historical trends.
5. Run demand analysis.
6. Review recommendations.
7. Inspect recommendation evidence.
8. Create a what-if scenario.
9. Compare scenario results with the baseline.
10. Review the saved analysis history.

A newly initialized application must not depend on an unavailable external university system.

---

## 11. REQUIRED TESTING

Create automated tests for business logic, API behavior, data integrity, security-sensitive behavior, and the principal end-to-end workflow.

### A. Pure analytics-engine tests

The demand-analysis engine must be testable independently of FastAPI and the frontend.

Include tests for:

- Correct capacity utilization.
- Weighted aggregate utilization where applicable.
- Increasing, decreasing, and stable demand.
- Courses repeatedly at capacity.
- Low-utilization courses.
- Missing historical periods.
- Zero or invalid capacity.
- Missing enrollment values.
- Invalid numeric values.
- Insufficient historical evidence.
- Unavailable unmet-demand information.
- Consistent recommendation generation for identical inputs.
- Correct scenario comparison.
- Preservation of the original baseline.
- Reproducibility of results.

Test known inputs against manually calculated expected results.

Do not use only snapshot tests or tests that repeat the implementation's own assumptions.

### B. Data-import tests

Verify:

- Valid CSV imports.
- Missing columns.
- Invalid data types.
- Empty files.
- Duplicate rows.
- Invalid encodings where relevant.
- Unexpected column names.
- Negative or impossible values.
- Partially valid datasets.
- Correct error and warning reporting.
- No silent loss of rejected records.

### C. API and database tests

Verify:

- Authentication.
- Role-based access.
- Unauthorized requests.
- Invalid request bodies.
- Import persistence.
- Analysis persistence.
- Recommendation evidence retrieval.
- Scenario persistence.
- Audit event creation.
- Database constraints.
- SQLite initialization and migrations.
- PostgreSQL compatibility where a PostgreSQL test environment is available.

### D. Frontend tests

Verify:

- Navigation.
- Login and logout.
- Import form validation.
- Data table filtering.
- Chart and textual result rendering.
- Recommendation details.
- Scenario form behavior.
- Baseline-versus-scenario comparison.
- Empty, loading, and error states.

### E. End-to-end acceptance tests

Test the core workflow from authentication through dataset import, analysis, recommendation review, scenario execution, and comparison.

A test passes only when its expected behavior is verified.

Do not fabricate passing results, test reports, coverage percentages, or successful deployment claims.

---

## 12. REQUIREMENTS TRACEABILITY

Create a requirements-to-implementation matrix.

Use the following baseline identifiers from the SRS:

### Functional requirements

- FR-01: Import a supported historical academic dataset.
- FR-02: Query and filter historical records by course, term, or modality.
- FR-03: Display historical enrollment, capacity utilization, and student-demand trends.
- FR-04: Produce course-demand analysis results.
- FR-05: Generate course-offering recommendations.
- FR-06: Display supporting data and recommendation explanations.
- FR-07: Create at least one supported what-if scenario.
- FR-08: Display changes relative to the baseline analysis.

### Data requirements

- DR-01: Accept and store the specified historical academic fields.
- DR-02: Identify missing, invalid, and inconsistent imported records or fields before analysis.
- DR-03: Preserve references to source datasets and applicable scenario values for analysis evidence.

### Quality requirements

- NFR-01: Restrict access to authorized users and protect communication.
- NFR-02: Present trends, recommendations, and supporting information in clear textual and visual forms.
- NFR-03: Provide responsive access to historical data and trends, allowing additional processing time for analysis.
- NFR-04: Identify data-quality issues and indicate their potential impact on results.

### Policy requirements

- COM-01: Follow the course's requirements-quality guidance, including stable identifiers, testable statements, sources, and planned verification.
- COM-02: Document significant generative AI assistance, human review, validation, and responsibility.

Preserve these identifiers in code comments, implementation documentation, or a dedicated traceability file where appropriate.

Create a `docs/requirements-traceability.md` file containing:

- Requirement ID.
- Original requirement summary.
- Implemented module or file.
- API endpoint or user interface, when applicable.
- Verification method.
- Test identifier.
- Status: Implemented, Partially Implemented, Not Implemented, or Not Verified.
- Explanation of any gap.

Do not mark a requirement as fully implemented merely because a related page or button exists.

A requirement is implemented only when the underlying behavior exists and can be demonstrated or tested.

The SRS contains planned and incomplete verification activities. Keep actual verification results separate from planned tests.

---

## 13. ACCEPTANCE CRITERIA

The baseline prototype is complete only when all applicable criteria below are satisfied.

AC-01: The application starts using documented commands.

AC-02: The database can be initialized from a clean state.

AC-03: An authorized user can authenticate successfully.

AC-04: The application can import a supported historical academic CSV dataset.

AC-05: The application reports missing, invalid, and inconsistent data with actionable feedback.

AC-06: The user can query and filter historical data by course, term, and modality.

AC-07: The application produces historical enrollment, capacity-utilization, and demand-trend views when the required data is available.

AC-08: The analytics engine produces a demand-analysis result for each course in the selected dataset.

AC-09: The application produces course-offering recommendations from the analysis.

AC-10: A user can inspect the supporting data, analytical rule, explanation, and limitations for a recommendation.

AC-11: The user can create and execute at least one supported what-if scenario.

AC-12: The user can compare the scenario results with the original baseline analysis.

AC-13: Scenario results identify the applicable source dataset and scenario parameters.

AC-14: Running a scenario does not overwrite the original historical data or baseline results.

AC-15: Important application operations are traceable through persisted records and appropriate audit events.

AC-16: Automated tests verify the analytics engine, data validation, core API behavior, and scenario comparison.

AC-17: The README provides complete setup, execution, testing, and troubleshooting instructions.

AC-18: The requirements traceability matrix accurately identifies implementation and verification status.

AC-19: The application presents information in clear textual and visual forms and includes appropriate accessibility practices.

AC-20: No mandatory baseline functionality depends on production CSUSB integrations or unapproved scheduling-optimization features.

---

## 14. OPTIONAL FUTURE EXTENSIONS

The following ideas may be useful in a later release, but they are not approved baseline requirements in SRS v0.1.

Do not implement these before the mandatory baseline is functional, tested, and traceable.

### Optional extension A: Faculty registry

- Faculty profiles.
- Education and degree history.
- Teaching qualifications.
- Specializations.
- Weekly workload records.
- Daily workload records.
- Availability and preferred time slots.

### Optional extension B: Complete timetable scheduling

- Working days and time slots.
- Break slots.
- Room types, buildings, and capacities.
- Section scheduling.
- Faculty assignment.
- Room-conflict prevention.
- Faculty-conflict prevention.
- Section-conflict prevention.
- Draft, published, and archived timetable versions.
- Weekly timetable filters.

### Optional extension C: Faculty leave and substitute recommendations

- Faculty leave declarations.
- Detection of affected classes.
- Identification of qualified alternate faculty.
- Availability checks.
- Ranked substitute recommendations.
- Human approval workflow.
- Workload and eligibility checks.

### Optional extension D: Conversational AI assistant

A future conversational interface could help users understand existing analysis results, provided its responses remain grounded in stored evidence.

It must not fabricate academic data, present unsupported predictions as facts, or replace human approval.

### Extension governance

Before implementing any extension:

1. Finish and test the baseline.
2. Identify the affected SRS requirements and scope boundaries.
3. Document the proposed change.
4. Assess its effect on architecture, data, testing, schedule, and risk.
5. Obtain project-team approval.
6. Update the SRS and traceability records.
7. Implement and test the extension separately.

Do not silently merge these features into the original scope.

---

## 15. REQUIRED PROJECT FILES

Produce a complete, organized repository.

A suggested structure is:

acs/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── features/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── types/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── analytics/
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   └── requirements.txt
├── data/
│   ├── synthetic/
│   └── examples/
├── docs/
│   ├── architecture.md
│   ├── database-design.md
│   ├── analytics-methodology.md
│   ├── requirements-traceability.md
│   ├── security.md
│   └── demo-guide.md
├── scripts/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md

You may adjust this structure when a better architecture is justified, but preserve the separation of frontend, API, database, analytics, testing, and documentation.

Include all required configuration files and dependencies.

Do not leave core modules as empty files, pseudocode, TODO comments, or placeholder API responses.

If a feature cannot be completed, document the exact gap and its effect on acceptance criteria.

---

## 16. DEVELOPMENT EXECUTION PLAN

Work through the following stages in order.

### Stage 1: SRS analysis

- Read the entire uploaded SRS.
- Identify approved baseline requirements.
- Identify scope exclusions and unresolved questions.
- Create a requirements checklist.
- Document any necessary implementation assumptions.

### Stage 2: Architecture and database

- Define the system architecture.
- Design the relational schema.
- Define the API contracts.
- Create database migrations.
- Create the requirements traceability matrix.

### Stage 3: Backend implementation

- Implement authentication and authorization.
- Implement dataset import.
- Implement data validation.
- Implement historical data queries.
- Implement analytics.
- Implement recommendation generation.
- Implement scenario execution and comparison.
- Implement evidence traceability and audit logging.

### Stage 4: Frontend implementation

- Build the application shell and navigation.
- Implement the dashboard.
- Build the import and validation workflow.
- Build historical-data exploration.
- Build analysis and recommendation pages.
- Build recommendation evidence views.
- Build the what-if scenario editor.
- Build scenario comparisons and analysis history.
- Add role-appropriate access and responsive behavior.

### Stage 5: Seed data and demonstration

- Create synthetic demonstration datasets.
- Create reproducible seed scripts.
- Configure development accounts safely.
- Verify that the demonstration workflow works from a clean database.

### Stage 6: Testing and debugging

- Run the analytics-engine tests.
- Run data-import and validation tests.
- Run API and authorization tests.
- Run frontend tests.
- Run end-to-end acceptance tests.
- Fix defects and rerun affected tests.
- Verify SQLite support and PostgreSQL compatibility.

### Stage 7: Final verification

- Start the application from a clean environment.
- Execute the complete demonstration workflow.
- Inspect errors and logs.
- Verify the traceability matrix against the actual code.
- Verify setup instructions.
- Document any remaining limitations.

Do not skip testing merely to finish generating code faster.

---

## 17. WORKING RULES FOR THE CODING AGENT

1. Start by inspecting the existing repository and uploaded SRS.
2. If the repository already contains code, inspect it before changing files.
3. Preserve useful existing work unless it conflicts with the SRS.
4. Implement real functionality rather than visual-only mockups.
5. Keep the analytics engine deterministic and independently testable.
6. Use the same analytical definitions in the API, user interface, and tests.
7. Do not fabricate historical records or real university integrations.
8. Do not invent approval from CSUSB stakeholders.
9. Do not confuse hypothetical scenario results with historical facts.
10. Do not label unverified requirements as complete.
11. Do not hard-code metrics that should be calculated from the database.
12. Do not suppress exceptions without logging and handling them appropriately.
13. Do not leave essential buttons disconnected from their intended actions.
14. Do not introduce optional faculty scheduling features until the core baseline is complete.
15. When a decision is not specified in the SRS, select a reasonable prototype implementation, record the assumption, and continue unless the ambiguity prevents safe or correct implementation.
16. Ask for clarification only when a necessary decision cannot reasonably be made without project-owner input.
17. Keep documentation synchronized with the implementation.
18. If a command fails, inspect the error, fix the underlying problem, and rerun it.
19. Never claim a test, migration, build, or deployment succeeded without actually verifying it.
20. Maintain the SRS as the controlling specification throughout development.

---

## 18. FINAL DELIVERABLES

At completion, provide:

1. The complete source code.
2. A working React frontend.
3. A working FastAPI backend.
4. Database models and migrations.
5. A SQLite local-development configuration.
6. A PostgreSQL Docker configuration.
7. Synthetic demonstration datasets.
8. Reproducible seed scripts.
9. Automated backend tests.
10. Frontend tests.
11. Analytics-engine tests.
12. End-to-end acceptance tests.
13. A requirements traceability matrix.
14. Architecture and database documentation.
15. Analytics methodology documentation.
16. Security and privacy notes.
17. A complete README with installation and execution commands.
18. Demonstration account setup instructions.
19. A demonstration workflow for the project presentation.
20. A final verification report identifying passed tests, failed tests, unverified items, and known limitations.

If your environment permits creating files, produce them directly in the repository rather than merely describing their contents.

If your environment permits command execution, run the installation, migrations, build, and tests.

If your environment permits a browser, launch the application and verify the major user workflows.

If you cannot execute a particular operation, clearly state what was not executed and provide the precise command needed to complete it.

---

## 19. FINAL RESPONSE FORMAT

When implementation is complete, report:

### A. Implementation summary
Describe the modules and workflows actually completed.

### B. How to run the application
Provide exact commands for local development and Docker deployment.

### C. Demonstration accounts
Explain how demonstration accounts are created and how credentials are configured safely.

### D. Verification results
List actual build, test, migration, and end-to-end results.

### E. Requirements coverage
Summarize FR-01 through FR-08, DR-01 through DR-03, NFR-01 through NFR-04, and COM-01 through COM-02 using truthful status values.

### F. Known limitations
Identify incomplete features, unverified behavior, assumptions, and unresolved SRS questions.

### G. Demonstration instructions
Provide a short sequence for presenting the complete decision-support workflow.

### H. Future enhancements
List faculty management, automated timetable scheduling, room optimization, leave management, substitute recommendations, and conversational AI as separate potential extensions.

Begin now by inspecting the SRS and repository. Then implement the baseline in stages until the application is runnable and its core behavior is verified.

**The final objective is a working, explainable, evidence-driven academic course-offering decision-support prototype that faithfully implements the uploaded SRS—not a different scheduling system.**
