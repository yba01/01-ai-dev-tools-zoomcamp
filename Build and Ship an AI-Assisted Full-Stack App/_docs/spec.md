# Expense Splitter — Software Requirements Specification

**Project type:** Academic software development project  
**Version:** 1.0  
**Status:** Initial specification  
**Product:** Web application

## 1. Project Overview

### 1.1 Problem Statement

When people share expenses during trips, student activities, house-sharing, or group events, tracking payments and calculating each person's contribution can become difficult.

People may pay different amounts, forget who paid for what, or struggle to determine how much each participant owes the others.

Expense Splitter aims to simplify this process by recording shared expenses, calculating each participant's balance, and identifying the payments needed to settle outstanding debts.

### 1.2 Project Objectives

The application must allow users to:

- Create a group for a shared activity.
- Add participants to the group.
- Record expenses paid by group members.
- Divide expenses equally among selected participants.
- Calculate how much each participant has paid, owes, and is owed.
- Generate a simplified list of payments that settles the group's outstanding balances.

### 1.3 Target Users

- Students sharing costs for academic activities.
- Friends organizing trips or events.
- Roommates sharing household expenses.
- Small groups managing common costs.

### 1.4 Product Scope

The MVP will be a web application focused on group expense sharing. It will not process real financial transactions. All payments and settlements will be recorded manually.

## 2. Functional Requirements

### FR-01: Group Management

Users must be able to create and manage expense-sharing groups.

Each group must have:

- A group name.
- An optional description.
- A creation date.
- A currency.
- A list of participants.
- A list of expenses.

**Acceptance criteria:**
- A user can create a group with a valid name.
- A group cannot be created without a name.
- A group can be opened to view its participants, expenses, and balances.
- A group can be edited or deleted, subject to appropriate confirmation.

### FR-02: Participant Management

Users must be able to add people to a group.

Each participant must have:
- A unique identifier.
- A display name.
- A group association.

**Acceptance criteria:**
- A participant can be added using a valid name.
- Duplicate participant names within the same group are rejected or explicitly distinguished.
- A participant cannot be assigned an expense in a group to which they do not belong.
- Removing a participant must not silently destroy financial records.

### FR-03: Expense Management

Users must be able to record shared expenses.

Each expense must contain:
- A description.
- An amount greater than zero.
- The participant who paid.
- The date of the expense.
- The participants sharing the expense.
- The split method.

**MVP split method:** Equal division.

**Acceptance criteria:**
- An expense must have a valid description, amount, payer, and at least one participant sharing the cost.
- The payer must belong to the group.
- The selected participants must belong to the same group.
- The application must reject zero or negative amounts.
- Users can view, edit, and delete expenses.
- Changes to an expense must trigger recalculation of balances.

### FR-04: Expense Calculation

The application must calculate each participant's share of every expense.

For an equally divided expense:

\[
\text{Share}=\frac{\text{Expense amount}}{\text{Number of participants sharing}}
\]

For each participant:

\[
\text{Balance}=\text{Total paid}-\text{Total share}
\]

Interpretation:

- **Positive balance:** The participant should receive money.
- **Negative balance:** The participant owes money.
- **Zero balance:** The participant has settled their share.

The payer is not automatically responsible for the entire expense. Their own share is included in the calculation.

**Acceptance criteria:**
- Every expense is divided among the selected participants.
- The sum of all shares equals the expense amount, including any rounding adjustment.
- Balances are recalculated whenever an expense changes.
- The sum of all participant balances equals zero, before and after recorded settlements.

### FR-05: Group Balance Dashboard

The application must provide a summary of the group's financial situation.

The dashboard must display:

- Total recorded expenses.
- Number of participants.
- Number of expenses.
- Amount paid by each participant.
- Each participant's net balance.
- Outstanding amounts to be settled.

**Acceptance criteria:**
- The dashboard reflects the latest expense records.
- Participants with positive balances are identified as creditors.
- Participants with negative balances are identified as debtors.
- Participants with zero balances are shown as settled.

### FR-06: Settlement Suggestions

The application must calculate a simplified set of transfers that settles all outstanding balances.

The algorithm must match debtors with creditors until all balances are zero.

**Example:**

Three friends share expenses:

| Participant | Net balance |
|---|---:|
| Amina | +10,000 XOF |
| Ibrahima | -6,000 XOF |
| Fatou | -4,000 XOF |

Suggested transfers:

1. Ibrahima pays Amina 6,000 XOF.
2. Fatou pays Amina 4,000 XOF.

After these transfers, all three participants have a zero balance.

**Acceptance criteria:**
- Every suggested transfer goes from a debtor to a creditor.
- No transfer exceeds the debtor's outstanding debt or the creditor's outstanding claim.
- The total amount transferred equals the total outstanding debt.
- Applying all suggested transfers settles the group's balances.
- The algorithm should minimize the number of transfers where practical, without requiring a mathematically optimal solution for the MVP.

### FR-07: Settlement Recording

Users must be able to record that a suggested payment has been made.

Each settlement must contain:
- The participant paying.
- The participant receiving.
- The amount.
- The date.
- A reference to the group.

**Acceptance criteria:**
- Settlements must have a positive amount.
- Both participants must belong to the same group.
- A settlement cannot exceed the outstanding debt or claim of the relevant participants.
- Recorded settlements must update the outstanding balances.
- Users must be able to view settlement history.

### FR-08: Data Persistence

Application data must remain available after refreshing or restarting the application.

**Acceptance criteria:**
- Groups, participants, expenses, and settlements are stored persistently.
- Related records maintain valid relationships.
- Invalid records cannot be saved.
- Deleting a group must not leave orphaned records.

## 3. Business Rules

1. Every expense belongs to exactly one group.
2. Each expense has exactly one payer.
3. Only group participants can pay or share expenses.
4. Expenses are divided equally among the selected participants in the MVP.
5. Monetary values must use decimal-safe arithmetic or integer minor units, not binary floating-point calculations.
6. Rounding differences must be allocated deterministically so that all shares add up to the original expense.
7. Settlements affect outstanding balances but must not be counted as new expenses.
8. The net balance of the group must equal zero when calculated from expenses and recorded settlements.
9. All amounts within a group use the group's currency.
10. Financial history must remain consistent when an expense is edited or deleted.

## 4. Core Data Model

The following entities represent the minimum data structure.

### Group

| Field | Description |
|---|---|
| id | Unique group identifier |
| name | Group name |
| description | Optional description |
| currency | Group currency, such as XOF |
| created_at | Creation timestamp |

### Participant

| Field | Description |
|---|---|
| id | Unique participant identifier |
| group_id | Associated group |
| name | Display name |

### Expense

| Field | Description |
|---|---|
| id | Unique expense identifier |
| group_id | Associated group |
| payer_id | Participant who paid |
| description | Expense description |
| amount | Total amount |
| date | Expense date |
| created_at | Record creation timestamp |

### ExpenseShare

This entity identifies who shares each expense.

| Field | Description |
|---|---|
| id | Unique share identifier |
| expense_id | Associated expense |
| participant_id | Participant sharing the expense |
| share_amount | Participant's allocated share |

### Settlement

| Field | Description |
|---|---|
| id | Unique settlement identifier |
| group_id | Associated group |
| payer_id | Participant making the payment |
| receiver_id | Participant receiving the payment |
| amount | Amount transferred |
| date | Settlement date |

**Relationship summary:**

- One group has many participants.
- One group has many expenses.
- One expense has one payer and multiple expense shares.
- One participant can pay many expenses and share many expenses.
- One group has many settlements.

## 5. User Interface Requirements

The MVP should include the following screens.

### Screen 1: Groups Dashboard
- List existing groups.
- Create a new group.
- Open or delete a group.

### Screen 2: Group Details
- Group information.
- Participant list.
- Total expenses.
- Current balances.
- Actions to add participants and expenses.

### Screen 3: Add/Edit Expense
- Description field.
- Amount field.
- Date field.
- Payer selection.
- Participant selection.
- Save and cancel actions.

### Screen 4: Balances and Settlements
- Participant balances.
- Suggested transfers.
- Record-settlement action.
- Settlement history.

The interface must be responsive, readable, and usable on both desktop and mobile devices.

## 6. Non-Functional Requirements

### NFR-01: Usability
A user should be able to create a group, add participants, and record an expense without technical knowledge.

### NFR-02: Correctness
Financial calculations must be accurate, deterministic, and covered by automated tests.

### NFR-03: Reliability
Invalid data must be rejected with understandable error messages.

### NFR-04: Maintainability
The application must separate business logic, data access, and user interface responsibilities.

### NFR-05: Security
If authentication is included, users must only access groups and data they are authorized to view or modify.

### NFR-06: Testing
The application must include unit tests for calculations and settlement logic, plus integration tests for important workflows.

## 7. Technical Architecture

The implementation stack may be selected based on course requirements and learning objectives. A reasonable default for this project is:

- **Frontend:** React
- **Backend:** FastAPI with Python
- **Database:** PostgreSQL
- **API:** REST
- **Testing:** Pytest for backend logic and API tests; frontend tests where appropriate
- **Version control:** Git and GitHub
- **Documentation:** README, specification, and API documentation

The application should use a layered architecture:

1. **Presentation layer:** Screens, forms, and balance summaries.
2. **API layer:** Request validation and HTTP endpoints.
3. **Business logic layer:** Expense calculations, balance computation, and settlement suggestions.
4. **Data access layer:** Database operations.
5. **Database layer:** Persistent relational storage.

The financial calculation logic must not be duplicated across the frontend and backend. The backend should be the authoritative source of balances and settlement suggestions.

## 8. API Requirements

The backend should expose REST endpoints similar to the following:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/groups` | Create a group |
| GET | `/groups` | List groups |
| GET | `/groups/{group_id}` | Get group details |
| PATCH | `/groups/{group_id}` | Update a group |
| DELETE | `/groups/{group_id}` | Delete a group |
| POST | `/groups/{group_id}/participants` | Add a participant |
| GET | `/groups/{group_id}/participants` | List participants |
| POST | `/groups/{group_id}/expenses` | Add an expense |
| GET | `/groups/{group_id}/expenses` | List expenses |
| PATCH | `/expenses/{expense_id}` | Update an expense |
| DELETE | `/expenses/{expense_id}` | Delete an expense |
| GET | `/groups/{group_id}/balances` | Calculate balances |
| GET | `/groups/{group_id}/settlement-suggestions` | Suggest transfers |
| POST | `/groups/{group_id}/settlements` | Record a settlement |
| GET | `/groups/{group_id}/settlements` | List settlements |

All endpoints must validate input, return appropriate HTTP status codes, and provide consistent error responses.

## 9. Testing Strategy

The following scenarios are mandatory.

**Unit tests**
- Equal division among two or more participants.
- Expense rounding and remainder allocation.
- A participant paying an expense they also share.
- Multiple expenses paid by different participants.
- Balance calculation with debtors and creditors.
- Settlement suggestion generation.
- Full settlement resulting in zero balances.
- Invalid amounts and invalid participant references.

**Integration tests**
- Create a group and add participants.
- Record an expense and verify balances.
- Edit or delete an expense and verify recalculation.
- Record a settlement and verify outstanding balances.
- Reject invalid API requests.

**End-to-end scenario**

1. Create a group with three participants.
2. Add two expenses paid by different participants.
3. Verify each participant's balance.
4. Generate settlement suggestions.
5. Record the suggested payments.
6. Confirm that all balances are zero.

## 10. MVP Acceptance Checklist

The MVP is complete when:

- [ ] A user can create, view, edit, and delete groups.
- [ ] Participants can be added to groups.
- [ ] Expenses can be created, viewed, edited, and deleted.
- [ ] Expenses can be shared equally among selected participants.
- [ ] Balances are calculated correctly.
- [ ] Settlement suggestions are generated correctly.
- [ ] Settlements can be recorded and reviewed.
- [ ] Data persists in the database.
- [ ] Input validation and error handling are implemented.
- [ ] Automated tests cover the core business rules.
- [ ] The project can be installed and run using documented instructions.

## 11. Out of Scope for the MVP

The following features are explicitly excluded from the initial version:

- Real payment processing.
- Bank account integration.
- Automatic expense import.
- OCR receipt scanning.
- Unequal or percentage-based expense splitting.
- Multi-currency conversion.
- Notifications and reminders.
- Advanced analytics and spending forecasts.
- Mobile applications.
- Complex role-based permissions.

These features may be considered in later versions if justified by user needs.

## 12. Suggested Development Phases

**Phase 1 — Foundation**
- Set up the repository and project structure.
- Configure the database.
- Implement the core data models.

**Phase 2 — Expense management**
- Implement groups and participants.
- Implement expense creation, editing, and deletion.
- Add input validation.

**Phase 3 — Financial logic**
- Implement share calculations.
- Implement participant balances.
- Implement settlement suggestions.
- Add comprehensive unit tests.

**Phase 4 — API and interface**
- Connect the frontend to the backend.
- Build the group dashboard, expense forms, and settlement screens.

**Phase 5 — Validation and delivery**
- Run integration and end-to-end tests.
- Fix defects.
- Document installation and usage.
- Prepare a demonstration of the application.

## 13. Definition of Done

A feature is considered complete only when:

- Its acceptance criteria are satisfied.
- Its business logic is tested.
- Invalid inputs are handled.
- The code follows the project's architecture.
- The feature is integrated with the database and API where applicable.
- The documentation is updated when necessary.
- The feature has been committed to version control.

**Final objective:** Deliver a functional, testable, and well-documented expense-sharing web application that demonstrates database design, REST API development, frontend integration, business logic, and software testing.