# AGENTS.md — Expense Splitter

## 1. Project Overview

Build an end-to-end web application called **Expense Splitter** using AI-assisted development.

The application helps groups of people manage shared expenses, calculate individual balances, and determine who owes money to whom.

This is an academic project designed to practice building a complete application with a frontend, backend, and database.

## 2. Homework Requirements

This project follows these mandatory requirements:

- **Backend:** Python with `uv` for dependency and project management.
- **Frontend:** Node.js ecosystem.
- **Database:** A persistent database for application data.
- **Architecture:** A frontend communicating with a backend API connected to the database.
- **Development approach:** Use AI-assisted development to implement, test, and improve the application incrementally.

Do not replace Python with another backend language or Node.js with another frontend runtime.

## 3. Product Scope

Implement an MVP that allows users to:

1. Create and manage expense-sharing groups.
2. Add participants to a group.
3. Record expenses and identify who paid.
4. Select which participants share each expense.
5. Split expenses equally among selected participants.
6. Calculate each participant's net balance.
7. Generate settlement suggestions.
8. Record completed settlements.
9. View expense and settlement history.

Use **XOF (West African CFA franc)** as the default currency.

The application must not process real payments.

## 4. Technical Guidelines

### Backend

- Use Python.
- Use `uv` to manage dependencies and execute project commands.
- Use FastAPI to expose a REST API.
- Use Pydantic for request validation and response schemas.
- Separate API routes, business logic, and database access.
- Use SQLAlchemy or another suitable ORM if justified.
- Keep financial calculations independent of HTTP routes and database implementation.

### Frontend

- Use Node.js and npm for frontend development.
- Use React with TypeScript and Vite unless existing project constraints require otherwise.
- Build a responsive, accessible interface.
- Communicate with the backend through its REST API.
- Keep API communication separate from presentation components.
- Display loading states, validation errors, empty states, and success feedback.

### Database

- Use PostgreSQL for persistent storage unless the homework environment or existing repository specifies another database.
- Model groups, participants, expenses, expense shares, and settlements with appropriate relationships.
- Enforce data integrity through database constraints where appropriate.
- Use migrations for schema changes.
- Do not rely on in-memory storage or hardcoded sample data as the permanent data layer.

## 5. Architecture

Maintain a clear separation of responsibilities:

- **Frontend:** User interface and user interactions.
- **Backend API:** HTTP endpoints, validation, and orchestration.
- **Business logic:** Expense allocation, balance calculations, and settlement generation.
- **Data access:** Database queries and persistence.
- **Database:** Durable storage and relational integrity.

The backend is the authoritative source for all financial calculations.

Never duplicate financial business rules independently in the frontend.

## 6. Core Business Rules

### Expenses

- Every expense belongs to one group.
- Every expense has one payer.
- The payer must belong to the group.
- An expense must be shared by at least one participant.
- Every participant sharing an expense must belong to the same group.
- Expense amounts must be positive.
- The MVP supports equal expense splitting only.

### Balances

For each participant:

`Net balance = Total paid - Total allocated shares + Settlements received - Settlements paid`

Interpretation:

- Positive balance: The participant is owed money.
- Negative balance: The participant owes money.
- Zero balance: The participant is settled.

The sum of all participant balances in a group must equal zero, subject to the application's defined rounding rules.

### Settlements

- A settlement transfers money from one participant to another.
- Both participants must belong to the same group.
- The amount must be positive.
- A settlement must not exceed the applicable outstanding debt or claim.
- Settlements must not be counted as expenses.
- Settlement history must be preserved.

### Monetary Precision

- Never use binary floating-point arithmetic for financial calculations.
- Use decimal-safe arithmetic or integer minor units.
- Define a deterministic rounding policy for equal splits.
- Ensure that allocated shares sum exactly to the original expense amount.

## 7. Implementation Workflow

Follow this sequence when implementing the application:

1. Inspect the existing repository and read its documentation.
2. Identify the current implementation, dependencies, and project constraints.
3. Create or refine the implementation plan before making substantial changes.
4. Implement one small, coherent feature at a time.
5. Run relevant tests after each feature.
6. Fix regressions before moving to the next feature.
7. Keep documentation and setup instructions synchronized with the implementation.
8. Report what was implemented, what was tested, and any remaining limitations.

Do not generate the entire application in one unreviewed change.

Before adding a new dependency or architectural component, verify that it is necessary.

## 8. Recommended Development Order

### Phase 1: Project Setup

- Inspect the repository.
- Initialize the Python backend with `uv`.
- Initialize the Node.js frontend.
- Configure environment variables.
- Configure the database connection.
- Document how to start each service.

### Phase 2: Data Model

Implement:

- Group
- Participant
- Expense
- ExpenseShare
- Settlement

Create database migrations and verify the relationships.

### Phase 3: Business Logic

Implement and test:

- Equal expense allocation.
- Balance calculations.
- Settlement suggestions.
- Rounding and edge cases.

Write unit tests before integrating these calculations into the API.

### Phase 4: REST API

Implement endpoints for:

- Group management.
- Participant management.
- Expense management.
- Balance retrieval.
- Settlement suggestions.
- Settlement recording and history.

Validate inputs and return appropriate HTTP status codes and consistent errors.

### Phase 5: Frontend

Implement:

- Groups dashboard.
- Group details.
- Participant management.
- Expense forms and expense history.
- Balance dashboard.
- Settlement suggestions and history.

Connect the interface to the real API.

### Phase 6: Integration and Delivery

- Run backend and frontend tests.
- Verify database persistence.
- Test complete user workflows.
- Resolve integration defects.
- Write a README with installation and execution instructions.
- Verify that a new developer can run the project by following the README.

## 9. Testing Requirements

Use pytest for backend testing.

At minimum, test:

- Expense splitting among multiple participants.
- Expenses with fractional shares and rounding remainders.
- A payer who also shares the expense.
- Participants who do not share a particular expense.
- Multiple expenses and changing balances.
- Settlement generation with multiple debtors and creditors.
- Invalid expense amounts and participant references.
- Expense updates and deletions.
- Settlement recording and balance recalculation.
- API validation and database persistence.

Add frontend tests for critical user interactions and validation where practical.

Do not claim a test passed unless it was actually executed and passed.

## 10. Security and Data Integrity

- Never commit secrets or credentials.
- Use environment variables for configuration.
- Validate all client input on the backend.
- Use database transactions for operations that modify related financial records.
- Prevent access to records outside the relevant group when authorization is implemented.
- Do not add authentication or complex permissions unless required by the specification or necessary for the deployment context.

## 11. Code Quality

- Prefer simple, readable, maintainable code.
- Use meaningful names and clear function responsibilities.
- Avoid unnecessary abstractions and premature optimization.
- Avoid duplicated business logic.
- Add comments for non-obvious decisions, not for self-explanatory code.
- Keep dependencies minimal.
- Never silently swallow exceptions.
- Do not hide errors with hardcoded fallback data.
- Update tests when behavior changes.

## 12. Scope Control

The MVP does not include:

- Real payment processing.
- Bank integration.
- Receipt OCR.
- Automatic expense imports.
- Multi-currency conversion.
- Advanced analytics.
- Native mobile applications.
- Notifications.
- Unequal or percentage-based splitting.

Do not implement these features unless explicitly requested.

## 13. Definition of Done

A feature is complete when:

- Its requirements and acceptance criteria are satisfied.
- Relevant automated tests pass.
- Input validation and error handling are implemented.
- The database remains consistent.
- The frontend and backend work together where applicable.
- No unrelated functionality is broken.
- Relevant documentation is updated.

The project is complete when a user can create a group, add participants, record shared expenses, view accurate balances, generate settlement suggestions, record settlements, and retrieve the data after restarting the application.

## 14. Agent Instructions

Act as a careful AI software engineering agent.

- Treat the project specification as the source of truth for product behavior.
- Treat this file as the source of truth for development practices and technical constraints.
- If the two documents conflict, preserve the homework requirements and ask for clarification when necessary.
- Inspect before editing.
- Make small, verifiable changes.
- Run tests and report actual results.
- Explain important technical decisions briefly.
- Do not introduce features outside the MVP without approval.
- Do not mark incomplete or untested functionality as finished.

**Primary objective:** Build a working, maintainable, and tested full-stack Expense Splitter using Python with `uv`, a Node.js frontend, and a persistent database.