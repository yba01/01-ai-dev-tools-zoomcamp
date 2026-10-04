# Django Implementation Plan

1. **Model household data in `chores`.** Add a `Member` model for the fixed sample household and a `Chore` model with a title, assignee, due date, and completion timestamp. Derive open, complete, due-soon, due-today, and overdue states from those fields and the local date; do not store reminder states separately.
2. **Provide sample members.** Add a small management command to create the initial members idempotently. Keep accounts, invitations, and household switching out of scope.
3. **Build the chore workflow.** Add Django views, URLs, and templates for the chore list, creating chores, selecting a member, marking a chore complete, and reassigning or rescheduling an overdue chore. Use a shared Organizer/Member mode switch; Member mode includes a sample-member selector. This is a demo interface distinction, not authentication or access control.
4. **Show in-app reminders.** Display due-tomorrow and due-today labels in the chore list, and keep incomplete past-due chores visible with an overdue label for the organizer. Do not add a notification inbox, email, or push delivery.
5. **Test the acceptance criteria.** Add focused tests for date-based labels, completing chores, creating and assigning chores, and updating overdue chores. Verify the list reflects each state.
6. **Validate the app.** Apply migrations, run Django's system check and the test suite, then manually walk through create, complete, and overdue flows.

**Resolved role interaction:** Use the shared Organizer/Member mode switch described above. Do not add accounts or authorization.
