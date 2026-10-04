from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Chore, Member


class ChoreModelTests(TestCase):
	def setUp(self):
		self.member = Member.objects.create(name="Alex")

	def test_status_is_derived_from_due_date_and_completion(self):
		today = date(2026, 10, 4)
		with patch("chores.models.timezone.localdate", return_value=today):
			chore = Chore(title="Today", assignee=self.member, due_date=today)
			self.assertEqual(chore.status, "due-today")
			self.assertEqual(chore.status_label, "Due today")
			self.assertFalse(chore.is_overdue)

			chore.due_date = today + timedelta(days=1)
			self.assertEqual(chore.status, "due-tomorrow")
			self.assertEqual(chore.status_label, "Due tomorrow")

			chore.due_date = today + timedelta(days=2)
			self.assertEqual(chore.status, "upcoming")
			self.assertEqual(chore.status_label, "Scheduled")

			chore.due_date = today - timedelta(days=1)
			self.assertTrue(chore.is_overdue)
			self.assertEqual(chore.status_label, "Overdue")

			chore.completed_at = timezone.now()
			self.assertEqual(chore.status, "complete")
			self.assertEqual(chore.status_label, "Complete")
			self.assertFalse(chore.is_overdue)


class SampleMemberCommandTests(TestCase):
	def test_seed_command_is_idempotent(self):
		Member.objects.create(name="Taylor")
		call_command("seed_members", stdout=StringIO())
		self.assertSetEqual(
			set(Member.objects.values_list("name", flat=True)),
			{"Alex", "Jordan", "Sam", "Taylor"},
		)

		call_command("seed_members", stdout=StringIO())
		self.assertEqual(Member.objects.count(), 4)


class ChoreWorkflowTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.alex = Member.objects.create(name="Alex")
		cls.jordan = Member.objects.create(name="Jordan")

	def create_chore(self, title="Wash dishes", due_date=None, assignee=None):
		return Chore.objects.create(
			title=title,
			assignee=assignee or self.alex,
			due_date=due_date or date.today() + timedelta(days=2),
		)

	def set_member_mode(self, member=None):
		return self.client.post(
			reverse("chores:switch_mode"),
			{"mode": "member", "member_id": (member or self.alex).pk},
		)

	def test_home_shows_date_labels_and_overdue_count(self):
		today = date(2026, 10, 4)
		self.create_chore("Today task", due_date=today)
		self.create_chore("Tomorrow task", due_date=today + timedelta(days=1))
		self.create_chore("Late task", due_date=today - timedelta(days=1))
		completed = self.create_chore("Finished task", due_date=today - timedelta(days=2))
		completed.completed_at = timezone.now()
		completed.save(update_fields=["completed_at"])

		with patch("chores.models.timezone.localdate", return_value=today):
			response = self.client.get(reverse("chores:home"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Due today")
		self.assertContains(response, "Due tomorrow")
		self.assertContains(response, "Overdue")
		self.assertContains(
			response, '<span class="assignee-dot" aria-hidden="true">A</span>'
		)
		self.assertContains(
			response, '<span class="assignee-name">Alex</span>'
		)
		self.assertEqual(response.context["overdue_count"], 1)
		self.assertEqual(response.context["open_count"], 3)
		self.assertEqual(response.context["complete_count"], 1)

	def test_empty_home_shows_organizer_create_action(self):
		response = self.client.get(reverse("chores:home"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "No chores yet")
		self.assertContains(response, "Add the first chore")

	def assert_shared_navigation(self, response):
		content = response.content.decode()
		member_selector = content.split('id="member-mode-select"', 1)[1].split(
			"</select>", 1
		)[0]
		self.assertIn(f'value="{self.alex.pk}"', member_selector)
		self.assertIn("Alex", member_selector)
		self.assertIn("Jordan", member_selector)
		self.assertNotIn("{{", member_selector)
		self.assertNotIn("option.name", member_selector)
		self.assertIn('role="group" aria-label="Demo mode"', content)
		self.assertIn('aria-pressed="true"', content)

	def test_create_page_renders_shared_navigation_context(self):
		response = self.client.get(reverse("chores:create_chore"))

		self.assertEqual(response.status_code, 200)
		self.assert_shared_navigation(response)

	def test_overdue_review_page_renders_shared_navigation_context(self):
		today = date(2026, 10, 4)
		chore = self.create_chore(due_date=today - timedelta(days=1))

		with patch("chores.models.timezone.localdate", return_value=today):
			response = self.client.get(
				reverse("chores:review_overdue_chore", args=[chore.pk])
			)

		self.assertEqual(response.status_code, 200)
		self.assert_shared_navigation(response)

	def test_organizer_can_create_a_chore(self):
		response = self.client.post(
			reverse("chores:create_chore"),
			{
				"title": "Take out recycling",
				"assignee": self.jordan.pk,
				"due_date": "2026-10-10",
			},
		)

		self.assertRedirects(response, reverse("chores:home"))
		chore = Chore.objects.get(title="Take out recycling")
		self.assertEqual(chore.assignee, self.jordan)
		self.assertEqual(chore.due_date, date(2026, 10, 10))

	def test_invalid_chore_form_does_not_create_a_chore(self):
		response = self.client.post(
			reverse("chores:create_chore"),
			{"title": "", "assignee": self.jordan.pk, "due_date": "2026-10-10"},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "This field is required.")
		self.assertEqual(Chore.objects.count(), 0)

	def test_member_can_mark_a_chore_complete(self):
		chore = self.create_chore()
		self.set_member_mode()

		response = self.client.post(
			reverse("chores:complete_chore", args=[chore.pk])
		)

		self.assertRedirects(response, reverse("chores:home"))
		chore.refresh_from_db()
		self.assertIsNotNone(chore.completed_at)

	def test_organizer_cannot_complete_without_member_mode(self):
		chore = self.create_chore()

		response = self.client.post(
			reverse("chores:complete_chore", args=[chore.pk])
		)

		self.assertRedirects(response, reverse("chores:home"))
		chore.refresh_from_db()
		self.assertIsNone(chore.completed_at)

	def test_repeated_completion_does_not_change_completion_time(self):
		chore = self.create_chore()
		self.set_member_mode()
		url = reverse("chores:complete_chore", args=[chore.pk])

		self.client.post(url)
		chore.refresh_from_db()
		completed_at = chore.completed_at
		response = self.client.post(url)

		self.assertRedirects(response, reverse("chores:home"))
		chore.refresh_from_db()
		self.assertEqual(chore.completed_at, completed_at)

	def test_member_view_shows_completion_action_without_organizer_actions(self):
		self.create_chore("Open task")
		self.set_member_mode()

		response = self.client.get(reverse("chores:home"))

		self.assertContains(response, "Member view")
		self.assertContains(response, "Alex")
		self.assertContains(response, "Mark complete")
		self.assertNotContains(response, "Add chore")

	def test_member_mode_cannot_create_chores(self):
		self.set_member_mode()

		response = self.client.get(reverse("chores:create_chore"))

		self.assertRedirects(response, reverse("chores:home"))
		self.assertEqual(Chore.objects.count(), 0)

	def test_member_cannot_review_an_overdue_chore(self):
		today = date(2026, 10, 4)
		chore = self.create_chore(due_date=today - timedelta(days=1))
		self.set_member_mode()

		with patch("chores.models.timezone.localdate", return_value=today):
			response = self.client.get(
				reverse("chores:review_overdue_chore", args=[chore.pk])
			)

		self.assertRedirects(response, reverse("chores:home"))

	def test_invalid_overdue_update_does_not_change_chore(self):
		today = date(2026, 10, 4)
		chore = self.create_chore(due_date=today - timedelta(days=1))

		with patch("chores.models.timezone.localdate", return_value=today):
			response = self.client.post(
				reverse("chores:review_overdue_chore", args=[chore.pk]),
				{"assignee": "", "due_date": ""},
			)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "This field is required.")
		chore.refresh_from_db()
		self.assertEqual(chore.assignee, self.alex)
		self.assertEqual(chore.due_date, today - timedelta(days=1))

	def test_organizer_can_reassign_and_reschedule_overdue_chore(self):
		today = date(2026, 10, 4)
		chore = self.create_chore(due_date=today - timedelta(days=1))
		data = {"assignee": self.jordan.pk, "due_date": "2026-10-08"}

		with patch("chores.models.timezone.localdate", return_value=today):
			response = self.client.post(
				reverse("chores:review_overdue_chore", args=[chore.pk]), data
			)

		self.assertRedirects(response, reverse("chores:home"))
		chore.refresh_from_db()
		self.assertEqual(chore.assignee, self.jordan)
		self.assertEqual(chore.due_date, date(2026, 10, 8))

	def test_switching_to_organizer_clears_selected_member(self):
		self.set_member_mode(self.jordan)

		response = self.client.post(
			reverse("chores:switch_mode"), {"mode": "organizer"}
		)

		self.assertRedirects(response, reverse("chores:home"))
		self.assertEqual(self.client.session["demo_mode"], "organizer")
		self.assertNotIn("selected_member_id", self.client.session)

	def test_invalid_member_selection_does_not_enter_member_mode(self):
		response = self.client.post(
			reverse("chores:switch_mode"),
			{"mode": "member", "member_id": "99999"},
		)

		self.assertRedirects(response, reverse("chores:home"))
		self.assertNotEqual(self.client.session.get("demo_mode"), "member")

	def test_mode_switch_rejects_get_requests(self):
		response = self.client.get(reverse("chores:switch_mode"))

		self.assertEqual(response.status_code, 405)

	def test_non_overdue_chore_cannot_be_edited_in_overdue_review(self):
		today = date(2026, 10, 4)
		chore = self.create_chore(due_date=today + timedelta(days=1))

		with patch("chores.models.timezone.localdate", return_value=today):
			response = self.client.get(
				reverse("chores:review_overdue_chore", args=[chore.pk])
			)

		self.assertRedirects(response, reverse("chores:home"))
