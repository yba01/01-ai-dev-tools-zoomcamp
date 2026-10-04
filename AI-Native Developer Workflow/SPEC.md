# Shared Household Chores: MVP Specification

## Goal

Build a small tool for one household to assign one-time chores, track completion, and make upcoming or overdue tasks visible.

## Users and household setup

- The MVP supports one household with sample members.
- There is one organizer role. The organizer creates chores, assigns them, and can reassign or reschedule overdue chores.
- A shared Organizer/Member mode switch controls which actions are shown. In Member mode, the user selects a sample member's name.
- This role switch is a demo interface only, not authentication or access control; there are no individual accounts or invitations.
- Members can mark chores complete.

## Chore workflow

1. The organizer creates a chore with a title, an assignee, and a due date.
2. The chore appears in the household chore list with its assignee and due date.
3. A member selects their name and marks a chore complete.
4. If the due date passes before completion, the chore remains open and is marked overdue. The organizer can reassign it or change its due date.

## Reminders

- Show reminder labels on the chore list one day before a chore is due and on its due date.
- Show an overdue label after the due date until the chore is completed or rescheduled.
- Surface overdue chores to the organizer in the chore list so they can take action.
- Reminders are in-app only; there is no separate notification inbox, email, or push notification.

## Out of scope

- Recurring chores
- Multiple households or household switching
- Sign-in, accounts, and invitations
- Email or push notifications
- Automatic reassignment or rescheduling

## Acceptance criteria

- The organizer can create a one-time chore, assign it to a sample member, and set its due date.
- A member can select their name and mark a chore complete.
- The chore list shows the assignee, due date, completion state, and applicable due-soon, due-today, or overdue label.
- An incomplete chore past its due date stays open and is visible to the organizer as overdue.
- The organizer can reassign or reschedule an overdue chore.
