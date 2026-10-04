# Project Backlog

1. [x] **Choose the demo role interaction.** Use a shared Organizer/Member mode switch; Member mode requires selecting a sample member. This is a demo UI distinction, not authentication or access control.
2. [x] **Add chore and member data.** Create `Member` and one-time `Chore` models, due/completion fields, derived status labels, and migrations.
3. [x] **Seed sample members.** Add an idempotent management command for the household's sample members.
4. [x] **Build the member chore flow.** Show the chore list and due dates; let a member select their name and mark chores complete.
5. [x] **Build organizer actions and reminders.** Let the organizer create and assign chores, and reassign or reschedule overdue chores. Show due-tomorrow, due-today, and overdue labels in the list.
6. [x] **Test and validate.** Cover the acceptance criteria, apply migrations, run Django checks and tests, and manually verify create, complete, and overdue flows.
