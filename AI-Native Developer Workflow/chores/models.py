from django.db import models
from django.utils import timezone


class Member(models.Model):
	name = models.CharField(max_length=80, unique=True)

	class Meta:
		ordering = ["name"]

	def __str__(self):
		return self.name


class Chore(models.Model):
	title = models.CharField(max_length=160)
	assignee = models.ForeignKey(
		Member,
		on_delete=models.PROTECT,
		related_name="chores",
	)
	due_date = models.DateField()
	completed_at = models.DateTimeField(blank=True, null=True)

	class Meta:
		ordering = ["due_date", "id"]

	def __str__(self):
		return self.title

	@property
	def status(self):
		if self.completed_at:
			return "complete"

		days_until_due = (self.due_date - timezone.localdate()).days
		if days_until_due < 0:
			return "overdue"
		if days_until_due == 0:
			return "due-today"
		if days_until_due == 1:
			return "due-tomorrow"
		return "upcoming"

	@property
	def status_label(self):
		return {
			"complete": "Complete",
			"overdue": "Overdue",
			"due-today": "Due today",
			"due-tomorrow": "Due tomorrow",
			"upcoming": "Scheduled",
		}[self.status]

	@property
	def is_overdue(self):
		return self.status == "overdue"
